from flask import Flask, render_template, Response, request, jsonify
import cv2
import threading
import time
from ultralytics import YOLO
import requests
import logging
# logging.getLogger('werkzeug').disabled = True
app = Flask(__name__)

# --- command to stream video from rpi ---
# libcamera-vid --nopreview -t 0 --width 640 --height 480 --framerate 15 --bitrate 2000000 --inline --flush --listen -o tcp://0.0.0.0:8888

# better quality version
# libcamera-vid --nopreview -t 0 --width 960 --height 540 --framerate 15 --bitrate 3000000 --inline --flush --listen -o tcp://0.0.0.0:8888

# faster but potential packet loss
# libcamera-vid --nopreview -t 0 --width 960 --height 540 --framerate 15 --bitrate 3000000 --inline --flush -o udp://<client_ip>:8888


# --- Global Variables & Configuration ---
video_active = False
current_frame = None
lock = threading.Lock()
model = "weights/yolov5n_best.pt"

# Configuration
PI_IP = "192.168.137.130"  # Raspberry Pi's IP address
PI_PORT = 5001
CONFIDENCE_THRESHOLD = 0.50
TARGET_OBJECTS = ['paper ball', 'eraser', 'cup']
ALIGNMENT_THRESHOLD = 80  # pixels

# State Tracking
selected_object = None
pi_robot_status = "Idle" # Tracks the robot's state (e.g., Idle, Seeking, Grabbing)
pi_initial_assessment_active = False  # Track if Pi is doing initial assessment
current_distance = 0
current_offset_x = 0
current_offset_y = 0

class UnifiedYOLOProcessor:
    def __init__(self):
        self.model_path = 'weights/yolov5n_best.pt'
        self.current_model = None
        self.latest_frame = None
        self.running = False
        self.target_detected_in_frame = False
        self.stats = {'frames_processed': 0, 'last_yolo_time': 0}
        
        # Updated detection stability tracking
        self.search_start_time = 0  # Time when object search was initiated
        self.initial_wait_duration = 1.0  # Wait 1 second after object selection
        self.last_command_sent = None
        self.command_repeat_count = 0

    def load_model(self):
        try:
            self.current_model = YOLO(self.model_path)
            print(f"✅ Successfully loaded YOLO model: {self.model_path}")
            return True
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            return False

    def frame_reader_tcp(self):
        stream_url = f'tcp://{PI_IP}:8888'
        cap = cv2.VideoCapture(stream_url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        print(f"Connecting to video stream: {stream_url}")
        while self.running:
            ret, frame = cap.read()
            if ret:
                frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
                self.latest_frame = frame
            else:
                time.sleep(0.01)
        cap.release()
        print("TCP stream connection closed.")

    def process_yolo_detection(self, frame):
        global selected_object, current_offset_x, current_offset_y, pi_initial_assessment_active
        start_time = time.time()
        
        # Don't process if no object is selected
        if not selected_object:
            return frame
            
        results = self.current_model.predict(frame, verbose=False, conf=CONFIDENCE_THRESHOLD)

        frame_h, frame_w = frame.shape[:2]
        center_x, center_y = frame_w // 2, frame_h // 2

        # Draw green center square
        box_size = 100
        cv2.rectangle(frame, (center_x + 25 - box_size, center_y + 15 - box_size), 
                    (center_x + box_size, center_y + box_size), (0, 255, 0), 2)

        # Reset detection state
        self.target_detected_in_frame = False
        current_offset_x = 0
        current_offset_y = 0
        movement_command = None
        
        current_time = time.time()
        
        # Check if we're in initial wait period after object selection
        time_since_search_start = current_time - self.search_start_time
        in_initial_wait = time_since_search_start < self.initial_wait_duration
        
        # Process detections first
        target_found = False
        for result in results:
            boxes = result.boxes
            for box in boxes:
                label = self.current_model.names[int(box.cls[0])].lower()
                
                if selected_object and label == selected_object:
                    target_found = True
                    self.target_detected_in_frame = True
                    
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = box.conf.item()

                    # Draw bounding box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                    # Compute center of bounding box
                    box_cx, box_cy = (x1 + x2) // 2, (y1 + y2) // 2
                    cv2.circle(frame, (box_cx, box_cy), 4, (0, 255, 255), -1)

                    # Calculate and show offset
                    dx = box_cx - center_x
                    dy = box_cy - center_y
                    current_offset_x = dx
                    current_offset_y = dy
                    
                    # Determine movement command based on alignment
                    if abs(dx) <= ALIGNMENT_THRESHOLD:
                        movement_command = "aligned"
                        alignment_status = "ALIGNED"
                        alignment_color = (0, 255, 0)
                    elif dx > ALIGNMENT_THRESHOLD:
                        movement_command = "move_right"
                        alignment_status = "MOVE RIGHT"
                        alignment_color = (0, 0, 255)
                    else:  # dx < -ALIGNMENT_THRESHOLD
                        movement_command = "move_left" 
                        alignment_status = "MOVE LEFT"
                        alignment_color = (0, 0, 255)
                    
                    # Show different status during initial wait
                    if in_initial_wait:
                        remaining_wait = self.initial_wait_duration - time_since_search_start
                        if movement_command == "aligned":
                            offset_text = f"ASSESSMENT: Target found straight ahead! ({remaining_wait:.1f}s)"
                            alignment_color = (0, 255, 255)  # Cyan for assessment
                        else:
                            offset_text = f"ASSESSMENT: Target detected, waiting... ({remaining_wait:.1f}s)"
                            alignment_color = (255, 255, 0)  # Yellow for assessment
                    else:
                        offset_text = f"Offset: Δx={dx}px, Δy={dy}px ({alignment_status})"
                    
                    cv2.putText(frame, offset_text, (10, 30), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, alignment_color, 2)

                    # Draw alignment indicator line
                    cv2.line(frame, (center_x, center_y), (box_cx, box_cy), alignment_color, 2)

                    # Label box
                    text = f"{label.title()} {conf:.2f} ({current_distance:.1f}cm)"
                    cv2.putText(frame, text, (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    break  # Only process the first matching target
        
        # Show initial wait status if no target found but we're still in wait period
        if not target_found and in_initial_wait:
            remaining_wait = self.initial_wait_duration - time_since_search_start
            wait_text = f"INITIAL ASSESSMENT: Checking for target straight ahead... ({remaining_wait:.1f}s)"
            cv2.putText(frame, wait_text, (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 165, 0), 2)  # Orange
        
        # Now determine the final command to send
        if in_initial_wait:
            # During initial wait period - only send commands if Pi is doing assessment
            if pi_initial_assessment_active:
                if target_found and movement_command:
                    # Send the actual alignment command during assessment
                    self.send_movement_command(self.target_detected_in_frame, movement_command, current_offset_x)
                    if movement_command != self.last_command_sent:
                        print(f"🔍 ASSESSMENT: Target detected, Command: {movement_command}")
                        self.last_command_sent = movement_command
                else:
                    # No target found during assessment - don't send rotate yet
                    print(f"🔍 ASSESSMENT: No target found straight ahead ({remaining_wait:.1f}s remaining)")
            # Don't send any commands if Pi is not in assessment mode
            
        elif not target_found:
            # After initial wait, no target detected - check if we need to reactivate assessment
            current_time = time.time()
            
            # If we recently had a target (within last 2 seconds), reactivate assessment instead of rotating
            if (self.last_command_sent in ['aligned', 'move_left', 'move_right'] and 
                current_time - self.search_start_time > self.initial_wait_duration):
                
                print("🔍 Target lost during alignment - reactivating assessment to avoid premature rotation")
                # Reset search start time to reactivate assessment period
                self.search_start_time = current_time
                self.last_command_sent = None
                # Don't send rotate command yet - let the assessment period handle it
                movement_command = None
            else:
                # Normal case - send rotate command
                movement_command = "rotate"
                if movement_command != self.last_command_sent:
                    self.command_repeat_count = 0
                    self.send_movement_command(self.target_detected_in_frame, movement_command, current_offset_x)
                    print(f"🎯 Target detected: {self.target_detected_in_frame}, Command: {movement_command}")
                    self.last_command_sent = movement_command
                
        else:
            # After initial wait, target found - send alignment commands
            if movement_command != self.last_command_sent:
                self.command_repeat_count = 0
                self.send_movement_command(self.target_detected_in_frame, movement_command, current_offset_x)
                print(f"🎯 Target detected: {self.target_detected_in_frame}, Command: {movement_command}")
            elif movement_command in ["move_left", "move_right"]:
                # For alignment commands, send continuously for smooth movement
                self.command_repeat_count += 1
                if self.command_repeat_count % 3 == 0:  # Send every 3rd frame to avoid spam
                    self.send_movement_command(self.target_detected_in_frame, movement_command, current_offset_x)
            
            self.last_command_sent = movement_command
        
        self.stats['last_yolo_time'] = time.time() - start_time
        self.stats['frames_processed'] += 1
        return frame

    def send_movement_command(self, is_detected, command, offset_x=0):
        """Sends movement commands to the Pi based on vision analysis."""
        try:
            requests.post(
                f"http://{PI_IP}:{PI_PORT}/movement_command",
                json={
                    'detected': is_detected,
                    'command': command,
                    'offset_x': offset_x
                },
                timeout=0.08 # Short timeout to avoid blocking
            )
        except requests.exceptions.RequestException:
            # This is expected to fail often if the Pi is busy; not a critical error
            pass

    def video_processing_loop(self):
        global current_frame
        while self.running and self.latest_frame is None:
            print("⏳ Waiting for the first frame from the video stream...")
            time.sleep(0.05)

        while self.running:
            if self.latest_frame is not None:
                frame_to_process = self.latest_frame.copy()
                processed_frame = self.process_yolo_detection(frame_to_process)
                ret, jpeg = cv2.imencode('.jpg', processed_frame)
                if ret:
                    with lock:
                        current_frame = jpeg.tobytes()
            time.sleep(0.02) # Control loop frequency

    def start_processing(self):
        if self.running:
            return False, "Processing is already running."
        if not self.load_model():
            return False, "Failed to load YOLO model."
        
        self.running = True
        self.stats = {'frames_processed': 0, 'last_yolo_time': 0}
        # Reset detection tracking
        self.search_start_time = 0
        self.last_command_sent = None
        self.command_repeat_count = 0
        
        threading.Thread(target=self.frame_reader_tcp, daemon=True).start()
        threading.Thread(target=self.video_processing_loop, daemon=True).start()
        
        return True, "Started video processing."

    def stop_processing(self):
        self.running = False
        self.latest_frame = None
        
        # Reset detection tracking
        self.search_start_time = 0
        self.last_command_sent = None
        self.command_repeat_count = 0
        self.target_detected_in_frame = False
        
        # Reset global variables
        global current_frame, selected_object, pi_robot_status, current_distance, current_offset_x, current_offset_y
        with lock:
            current_frame = None
        
        # Reset global state
        selected_object = None
        pi_robot_status = "Idle"
        current_distance = 0
        current_offset_x = 0
        current_offset_y = 0
        
        print("⏹️ Processing stopped and all state reset.")

processor = UnifiedYOLOProcessor()

# --- Flask Routes ---
@app.route('/control', methods=['POST'])
def control():
    global video_active, selected_object
    action = request.json['action']
    
    if action == 'start' and not video_active:
        success, message = processor.start_processing()
        if success:
            video_active = True
            return jsonify({'status': 'success', 'message': message})
        else:
            return jsonify({'status': 'error', 'message': message})
            
    elif action == 'stop':  # Remove the video_active condition check
        # Force stop regardless of current state
        processor.stop_processing()
        
        # Reset all global state variables
        video_active = False
        selected_object = None
        
        # Also command the robot to stop
        try:
            requests.post(f"http://{PI_IP}:{PI_PORT}/command", json={'object': 'stop'}, timeout=2)
        except requests.exceptions.RequestException as e:
            print(f"Could not send stop command to Pi: {e}")
        
        return jsonify({'status': 'success', 'message': 'Processing stopped.'})
    
    return jsonify({'status': 'error', 'message': 'Invalid action or state.'})

@app.route('/grab', methods=['POST'])
def grab():
    """Handle object selection and command the robot to start seeking."""
    global selected_object
    object_name = request.json.get('object', '').lower()
    isDetected = processor.target_detected_in_frame
    if object_name in TARGET_OBJECTS and not isDetected:
        selected_object = object_name
        # Set search start time for initial wait period
        processor.search_start_time = time.time()
        processor.last_command_sent = None
        processor.command_repeat_count = 0
        
        try:
            # Command the Pi to start seeking this object
            res = requests.post(
                f"http://{PI_IP}:{PI_PORT}/command",
                json={'object': object_name},
                timeout=3
            )
            if res.status_code == 200:
                return jsonify({'status': 'success', 'message': f'Robot is now seeking: {object_name.title()}'})
            else:
                return jsonify({'status': 'error', 'message': 'Robot did not acknowledge command.'})
        except requests.exceptions.RequestException as e:
            return jsonify({'status': 'error', 'message': f'Failed to send command to Pi: {e}'})
    
    else:
        return jsonify({'status': 'error', 'message': 'Invalid object selected.'})

@app.route('/robot_status', methods=['POST'])
def robot_status():
    """Receives status updates from the Raspberry Pi."""
    global pi_robot_status, current_distance, pi_initial_assessment_active
    data = request.json
    pi_robot_status = data.get('state', pi_robot_status)
    current_distance = data.get('distance', current_distance)
    pi_initial_assessment_active = data.get('initial_assessment_active', pi_initial_assessment_active)
    return jsonify({'status': 'success'})

@app.route('/stats')
def stats():
    """Provides frontend with current system statistics."""
    alignment_status = "aligned" if abs(current_offset_x) <= ALIGNMENT_THRESHOLD else "misaligned"
    if current_offset_x > ALIGNMENT_THRESHOLD:
        alignment_status = "move_right"
    elif current_offset_x < -ALIGNMENT_THRESHOLD:
        alignment_status = "move_left"
    
    # Show assessment status if Pi is in initial assessment
    if pi_initial_assessment_active:
        current_time = time.time()
        time_since_search = current_time - processor.search_start_time
        remaining_time = processor.initial_wait_duration - time_since_search
        if remaining_time > 0:
            grab_status = f"Assessing ({remaining_time:.1f}s)"
        else:
            grab_status = pi_robot_status
    else:
        grab_status = pi_robot_status
        
    return jsonify({
        'active': video_active,
        'targetValue': selected_object.title() if selected_object else 'None',
        'distanceValue': f"{current_distance:.1f}cm" if current_distance > 0 else 'N/A',
        'offsetValue': f"Δx={current_offset_x}px, Δy={current_offset_y}px",
        'alignmentValue': alignment_status,
        'framesValue': processor.stats['frames_processed'],
        'timeValue': f"{processor.stats['last_yolo_time']:.3f}s",
        'grabValue': grab_status
    })

@app.route('/config', methods=['POST'])
def config():
    """Update configuration like confidence threshold."""
    global CONFIDENCE_THRESHOLD, ALIGNMENT_THRESHOLD
    data = request.json
    if 'confidence_threshold' in data:
        CONFIDENCE_THRESHOLD = float(data['confidence_threshold'])
        return jsonify({'status': 'success'})
    if 'alignment_threshold' in data:
        ALIGNMENT_THRESHOLD = float(data['alignment_threshold'])
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Invalid config.'})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            with lock:
                if current_frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + current_frame + b'\r\n')
            time.sleep(0.03) # ~33 FPS streaming rate
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("Starting YOLO Detection Server...")
    app.run(host='0.0.0.0', port=5000)