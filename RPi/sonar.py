"""HC-SR04 style ultrasonic distance sensor."""
import time

import RPi.GPIO as GPIO


class SonarSensor:
    def __init__(self, trigger_pin, echo_pin):
        self.TRIG = trigger_pin
        self.ECHO = echo_pin
        GPIO.setup(self.TRIG, GPIO.OUT)
        GPIO.setup(self.ECHO, GPIO.IN)
        GPIO.output(self.TRIG, False)
        time.sleep(0.1)

    def measure_distance(self):
        """Return distance in cm, or -1 if the reading is invalid."""
        try:
            GPIO.output(self.TRIG, True)
            time.sleep(0.00001)
            GPIO.output(self.TRIG, False)

            pulse_start_time = time.time()
            timeout = pulse_start_time + 0.1
            while GPIO.input(self.ECHO) == 0 and pulse_start_time < timeout:
                pulse_start_time = time.time()

            pulse_end_time = time.time()
            timeout = pulse_end_time + 0.1
            while GPIO.input(self.ECHO) == 1 and pulse_end_time < timeout:
                pulse_end_time = time.time()

            pulse_duration = pulse_end_time - pulse_start_time
            distance = pulse_duration * 17150
            return distance if 2 <= distance <= 400 else -1
        except Exception:
            return -1
