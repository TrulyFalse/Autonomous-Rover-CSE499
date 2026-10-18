"""Servo-driven robotic arm: low-level servo control and grab/drop routines."""
import time

import RPi.GPIO as GPIO

from .config import SERVO_PINS
from .kinematics import calculate_angles


class RobotArm:
    def __init__(self):
        self.pwms = {}
        self.servo_positions = {}
        for pin in SERVO_PINS:
            GPIO.setup(pin, GPIO.OUT)
            self.pwms[pin] = GPIO.PWM(pin, 50)
            self.pwms[pin].start(0)
        self.claw_pwm, self.shoulder_pwm, self.elbow_pwm, self.base_pwm = (
            self.pwms[p] for p in SERVO_PINS
        )

    # --- Low-level servo control ---
    @staticmethod
    def angle_to_duty(angle):
        return 2 + (angle / 180.0) * 10

    def smooth_move_servo(self, pwm, start_angle, target_angle, duration=1, release=False):
        steps = 30
        step_delay = duration / steps
        step_angle = (target_angle - start_angle) / steps
        angle = start_angle
        for _ in range(steps):
            pwm.ChangeDutyCycle(self.angle_to_duty(angle))
            time.sleep(step_delay)
            angle += step_angle
        pwm.ChangeDutyCycle(self.angle_to_duty(target_angle))
        time.sleep(0.3)
        if release:
            pwm.ChangeDutyCycle(0)

    def set_servo_angle(self, pwm, target_angle, duration=0.65, release=True):
        """Smoothly move a servo to the target angle."""
        pin = [k for k, v in self.pwms.items() if v == pwm][0]
        current_angle = self.servo_positions.get(pin, target_angle)
        self.smooth_move_servo(pwm, current_angle, target_angle,
                               duration=duration, release=release)
        self.servo_positions[pin] = target_angle

    # --- High-level arm routines ---
    def reset(self):
        """Put the arm in a neutral position."""
        print("Resetting arm position...")
        self.set_servo_angle(self.claw_pwm, 10, duration=1)
        self.set_servo_angle(self.elbow_pwm, 20, duration=1)
        self.set_servo_angle(self.shoulder_pwm, 40, duration=1)

    def grab(self, distance):
        """Reach out, grasp an object at `distance` cm, and lift it."""
        shoulder_angle = 45
        elbow_angle = 20
        if distance < 10.5:
            shoulder_angle, elbow_angle = calculate_angles(distance - 1, 1)
        print("shoulder:", shoulder_angle)
        print("elbow:", elbow_angle)
        shoulder_angle += 45
        elbow_angle += 15

        self.set_servo_angle(self.shoulder_pwm, shoulder_angle)          # position over object
        self.set_servo_angle(self.claw_pwm, 120)                         # open claw
        self.set_servo_angle(self.elbow_pwm, elbow_angle)                # lower elbow
        self.set_servo_angle(self.claw_pwm, 5, release=False, duration=0.25)  # close claw
        self.set_servo_angle(self.elbow_pwm, 10, release=False)          # lift elbow

    def drop(self):
        print("Dropping object...")
        self.set_servo_angle(self.elbow_pwm, 90)
        time.sleep(0.5)
        self.set_servo_angle(self.claw_pwm, 120)
        time.sleep(0.5)
        self.set_servo_angle(self.elbow_pwm, 15)
        time.sleep(0.5)
        self.set_servo_angle(self.claw_pwm, 20)
        time.sleep(0.5)
        self.set_servo_angle(self.shoulder_pwm, 45)
        time.sleep(0.5)

    def cleanup(self):
        for pwm in self.pwms.values():
            pwm.stop()
