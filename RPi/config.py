"""Central configuration: pins, network settings, and tuning parameters."""

# --- GPIO pins (BCM numbering) ---
FRONT_SENSOR_TRIG = 14
FRONT_SENSOR_ECHO = 15
SERVO_PINS = [2, 3, 4, 17]  # claw, shoulder, elbow, base

# AMSpi motor driver pins
SHIFT_REGISTER_PINS = (21, 20, 16)  # 74HC595
L293D_PINS = (5, 6, 13, 19)

# --- Networking ---
MAIN_SERVER_URL = "http://192.168.137.236:8000/robot_status"
COMMAND_SERVER_HOST = "0.0.0.0"
COMMAND_SERVER_PORT = 5001
VALID_TARGETS = ["paper ball", "cup", "eraser"]

# --- Movement & grabbing ---
GRAB_RANGE_MIN = 5.0        # cm - minimum distance for grab
GRAB_RANGE_MAX = 11.0       # cm - maximum distance for grab
OBSTACLE_THRESHOLD = 15.0   # cm - stop if non-target obstacle is this close
MOVE_SPEED = 20             # motor speed %
ROTATION_SPEED = 28         # motor speed % for rotation
ALIGN_LEFT_SPEED = ROTATION_SPEED // 2.15   # slower rotation for precise alignment
ALIGN_RIGHT_SPEED = ROTATION_SPEED // 2
ADJUST_DURATION = 0.4       # seconds to move when adjusting distance
ROTATION_TIME = 0.4         # seconds per search rotation step
ROTATION_PAUSE = 2          # seconds to pause after each search step
MAX_ROTATION_STEPS = 16     # steps before giving up on a search
MAX_GRAB_RETRIES = 3
RESET_BACKUP_FACTOR = 0.85  # fraction of distance driven that is reversed on reset
GRAB_SETTLE_TIME = 1        # seconds to wait before checking grab success

# --- Initial assessment / alignment confirmation ---
INITIAL_ASSESSMENT_DURATION = 3   # seconds
ALIGNMENT_WAIT_DURATION = 1       # seconds of consistent "aligned" before locking

# --- Arm geometry (cm) ---
L1 = 7.5
L2 = 7.0
H_BASE = 4.7
