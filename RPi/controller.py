"""Robot state machine: Idle -> Seeking -> Adjusting -> Grabbing -> Resetting."""
import time

import RPi.GPIO as GPIO

from . import config as cfg
from .arm import RobotArm
from .drive import DriveTrain
from .sonar import SonarSensor
from .status import send_status


class RobotController:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)

        self.state = "Idle"  # Idle, Seeking, Adjusting, Grabbing, Resetting
        self.front_sensor = SonarSensor(cfg.FRONT_SENSOR_TRIG, cfg.FRONT_SENSOR_ECHO)
        self.drive = DriveTrain()
        self.arm = RobotArm()
        self.target_object = None

        # Movement command from backend: rotate, move_left, move_right, aligned
        self.is_target_detected = False
        self.movement_command = "rotate"
        self.offset_x = 0

        # Initial assessment
        self.initial_assessment_active = False
        self.initial_assessment_start_time = None
        self.target_found_during_assessment = False

        # Alignment lock
        self.alignment_locked = False
        self.alignment_wait_start = None

        self.reset_duration = 0
        self.grab_retries = 0
        self.holding_object = False
        self.rotation_count = 0

        self.arm.reset()
        print("✅ Robot Controller Initialized.")

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------
    def _reset_assessment(self):
        self.initial_assessment_active = False
        self.initial_assessment_start_time = None
        self.target_found_during_assessment = False

    def _unlock_alignment(self):
        self.alignment_locked = False
        self.alignment_wait_start = None

    # ------------------------------------------------------------------
    # Commands from the Flask server
    # ------------------------------------------------------------------
    def start_seeking(self, object_name):
        self.target_object = object_name
        self.is_target_detected = False
        self.movement_command = "rotate"
        self.reset_duration = 0
        self.grab_retries = 0
        self.rotation_count = 0
        self._unlock_alignment()
        self.initial_assessment_active = True
        self.initial_assessment_start_time = None
        self.target_found_during_assessment = False
        self.state = "Seeking"
        print(f"COMMAND: Start seeking '{object_name}' - starting with 1s assessment")

    def stop(self):
        self.state = "Idle"
        self.target_object = None
        self.movement_command = "rotate"
        self._unlock_alignment()
        self._reset_assessment()
        self.drive.stop()
        print("COMMAND: Stop and return to Idle - alignment unlocked and assessment reset")

    def handle_vision_update(self, detected, command, offset_x):
        """Apply a movement command produced by the vision server."""
        self.is_target_detected = detected
        self.offset_x = offset_x

        # Reactivate the assessment so a briefly-lost target doesn't cause a sudden rotation
        if command in ('aligned', 'move_left', 'move_right'):
            if not self.initial_assessment_active:
                print(f"🔍 Reactivating initial assessment due to {command} command")
                self.initial_assessment_active = True
                self.initial_assessment_start_time = None
                self.target_found_during_assessment = False

        self.movement_command = command

    # ------------------------------------------------------------------
    # Seeking / alignment
    # ------------------------------------------------------------------
    def _process_assessment(self, now):
        """Run the initial assessment. Returns True if the caller should return early."""
        if not self.initial_assessment_active:
            return False

        if self.initial_assessment_start_time is None:
            self.initial_assessment_start_time = now
            print("🔍 Starting initial assessment...")
            self.drive.stop()
            return True

        remaining = cfg.INITIAL_ASSESSMENT_DURATION - (now - self.initial_assessment_start_time)
        if remaining > 0:
            if self.is_target_detected and self.movement_command == "aligned":
                self.target_found_during_assessment = True
                print(f"✅ Target found straight ahead during assessment! {remaining:.1f}s remaining")
            else:
                print(f"🔍 Assessment in progress... {remaining:.1f}s remaining")
            self.drive.stop()
            return True

        self.initial_assessment_active = False
        print("✅ Initial assessment complete!")
        if self.target_found_during_assessment:
            print("🎯 Target was found straight ahead - proceeding to distance adjustment")
            self.state = "Adjusting"
            self.rotation_count = 0
            return True

        print("🔄 Target not found straight ahead - starting rotation search")
        return False

    def _search_rotate(self):
        print(f"🔄 Rotating to search for target... Step {self.rotation_count}/{cfg.MAX_ROTATION_STEPS}")
        self.drive.rotate_left(cfg.ROTATION_SPEED)
        time.sleep(cfg.ROTATION_TIME)
        self.drive.stop()
        time.sleep(cfg.ROTATION_PAUSE)
        self.rotation_count += 1

        if self.rotation_count >= cfg.MAX_ROTATION_STEPS:
            print("❌ Target not found after 360-degree search")
            self.state = "Resetting"

    def _align_step(self, direction):
        """Continuously rotate toward the target ('left' or 'right')."""
        if self.alignment_locked:
            print(f"🔒 Alignment locked - ignoring move_{'right' if direction == 'left' else 'left'} command")
            return
        self.alignment_wait_start = None

        if direction == "left":
            print("↩️ Continuously rotating left to align target...")
            self.drive.rotate_left(cfg.ALIGN_LEFT_SPEED)
        else:
            print("↪️ Continuously rotating right to align target...")
            self.drive.rotate_right(cfg.ALIGN_RIGHT_SPEED)
        self.rotation_count = 0

    def _handle_aligned(self, now):
        if self.alignment_wait_start is None:
            self.alignment_wait_start = now
            self.drive.stop()
            print("⏱️ Target aligned - stopping motors and waiting to confirm...")
        elif now - self.alignment_wait_start >= cfg.ALIGNMENT_WAIT_DURATION:
            if not self.alignment_locked:
                self.alignment_locked = True
                print("🔒 Alignment CONFIRMED and LOCKED")
                if self.state == "Seeking":
                    self.state = "Adjusting"
                    self.rotation_count = 0
                    print("✅ Moving to distance adjustment phase.")
        else:
            self.drive.stop()
            remaining = cfg.ALIGNMENT_WAIT_DURATION - (now - self.alignment_wait_start)
            print(f"⏱️ Waiting {remaining:.1f}s more to confirm alignment...")

    def execute_movement_command(self):
        """Execute movement based on the latest backend command."""
        now = time.time()
        if self._process_assessment(now):
            return

        cmd = self.movement_command
        if cmd == "rotate":
            self._search_rotate()
        elif cmd == "move_right":    # target is to the left -> rotate left
            self._align_step("left")
        elif cmd == "move_left":     # target is to the right -> rotate right
            self._align_step("right")
        elif cmd == "aligned":
            self._handle_aligned(now)
        elif not self.alignment_locked:
            self.drive.stop()

    # ------------------------------------------------------------------
    # State handlers
    # ------------------------------------------------------------------
    def _handle_seeking(self):
        if not self.is_target_detected and not self.initial_assessment_active:
            if self.movement_command == "rotate":
                self.execute_movement_command()
        else:
            self.execute_movement_command()

    def _handle_adjusting(self, distance):
        if not self.is_target_detected and distance > cfg.OBSTACLE_THRESHOLD:
            self.state = "Seeking"
            self._unlock_alignment()
            self.rotation_count = 0
            self._reset_assessment()
            print("🔓 Target lost - alignment unlocked, returning to seeking")
            return

        self.execute_movement_command()
        if not self.alignment_locked:
            return

        if distance > cfg.GRAB_RANGE_MAX:
            print(f"📏 Too far ({distance:.1f}cm), moving forward...")
            self.drive.move(cfg.MOVE_SPEED)
            time.sleep(cfg.ADJUST_DURATION)
            self.drive.stop()
            self.reset_duration += cfg.ADJUST_DURATION
        elif distance < cfg.GRAB_RANGE_MIN:
            print(f"📏 Too close ({distance:.1f}cm), moving backward...")
            self.drive.move(-cfg.MOVE_SPEED)
            time.sleep(cfg.ADJUST_DURATION)
            self.drive.stop()
            self.reset_duration -= cfg.ADJUST_DURATION
        else:
            print(f"🎯 Perfect distance ({distance:.1f}cm) and aligned!")
            self.drive.stop()
            self.state = "Grabbing"

    def _handle_resetting(self):
        print("⚠️ Resetting position...")
        self.drive.move(-cfg.MOVE_SPEED)
        time.sleep(self.reset_duration * cfg.RESET_BACKUP_FACTOR)
        self.drive.stop()
        self.reset_duration = 0
        self.rotation_count = 0
        self._unlock_alignment()
        self._reset_assessment()
        print("🔓 Alignment unlocked and assessment reset during reset")
        if self.holding_object:
            self.drop_object()
        self.target_object = None
        self.movement_command = "rotate"
        self.state = "Idle"

    # ------------------------------------------------------------------
    # Grabbing
    # ------------------------------------------------------------------
    def execute_grab_sequence(self, initial_distance):
        self.grab_retries += 1
        print(f"🤖 Starting grab attempt #{self.grab_retries}...")
        self.arm.grab(initial_distance)
        time.sleep(cfg.GRAB_SETTLE_TIME)

        final_distance = self.front_sensor.measure_distance()
        if final_distance == -1 or final_distance > initial_distance + 5:
            print("✅ Grab Successful!")
            self.holding_object = True
            self.grab_retries = 0
            self.state = "Resetting"
            return

        print("❌ Grab Failed. Retrying...")
        self.arm.reset()
        if self.grab_retries >= cfg.MAX_GRAB_RETRIES:
            print(f"❌ Failed to grab after {cfg.MAX_GRAB_RETRIES} attempts. Resetting.")
            self._unlock_alignment()
            self._reset_assessment()
            print("🔓 Alignment unlocked and assessment reset due to grab failure")
            self.state = "Resetting"
        else:
            self.drive.move(-cfg.MOVE_SPEED)
            time.sleep(cfg.ADJUST_DURATION)
            self.drive.stop()
            self.reset_duration -= cfg.ADJUST_DURATION
            self._reset_assessment()
            print("🔓  attempting to grab again")
            self.state = "Adjusting"

    def drop_object(self):
        self.arm.drop()
        self.holding_object = False

    # ------------------------------------------------------------------
    # Main loop & lifecycle
    # ------------------------------------------------------------------
    def main_loop(self):
        while True:
            distance = self.front_sensor.measure_distance()
            if distance == -1:
                time.sleep(0.1)
                continue

            if self.state == "Idle":
                self.drive.stop()
            elif self.state == "Seeking":
                self._handle_seeking()
            elif self.state == "Adjusting":
                self._handle_adjusting(distance)
            elif self.state == "Grabbing":
                print(f"🤖 Grabbing at distance: {distance}cm")
                self.execute_grab_sequence(distance)
            elif self.state == "Resetting":
                self._handle_resetting()

            send_status(self.state, distance,
                        self.alignment_locked, self.initial_assessment_active)
            time.sleep(0.1)

    def cleanup(self):
        self.drive.stop()
        self.arm.cleanup()
        GPIO.cleanup()
        print("GPIO cleanup complete.")
