"""DC motor drive train (movement and rotation)."""
from AMSpi import AMSpi

from .config import SHIFT_REGISTER_PINS, L293D_PINS, ROTATION_SPEED


class DriveTrain:
    def __init__(self):
        self.amspi = AMSpi()
        self.amspi.set_74HC595_pins(*SHIFT_REGISTER_PINS)
        self.amspi.set_L293D_pins(*L293D_PINS)
        self.motor_active = True

    @property
    def _all_motors(self):
        a = self.amspi
        return [a.DC_Motor_1, a.DC_Motor_2, a.DC_Motor_3, a.DC_Motor_4]

    def move(self, speed):
        """Drive forward (speed > 0) or backward (speed < 0); 0 stops."""
        if not self.motor_active:
            return
        if speed == 0:
            self.amspi.stop_dc_motors(self._all_motors)
            return

        motor_speed = abs(speed)
        forward = speed > 0
        a = self.amspi
        a.run_dc_motors([a.DC_Motor_1, a.DC_Motor_3, a.DC_Motor_4],
                        speed=motor_speed, clockwise=forward)
        # Motor 2 is mounted reversed
        a.run_dc_motors([a.DC_Motor_2], speed=motor_speed, clockwise=not forward)

    def rotate_left(self, speed=ROTATION_SPEED):
        """Rotate counterclockwise: right side backward, left side forward."""
        if not self.motor_active:
            return
        a = self.amspi
        a.run_dc_motors([a.DC_Motor_1], speed=speed, clockwise=False)
        a.run_dc_motors([a.DC_Motor_2], speed=speed, clockwise=True)   # reversed motor
        a.run_dc_motors([a.DC_Motor_3, a.DC_Motor_4], speed=speed, clockwise=True)

    def rotate_right(self, speed=ROTATION_SPEED):
        """Rotate clockwise: right side forward, left side backward."""
        if not self.motor_active:
            return
        a = self.amspi
        a.run_dc_motors([a.DC_Motor_1], speed=speed, clockwise=True)
        a.run_dc_motors([a.DC_Motor_2], speed=speed, clockwise=False)  # reversed motor
        a.run_dc_motors([a.DC_Motor_3, a.DC_Motor_4], speed=speed, clockwise=False)

    def stop(self):
        self.amspi.stop_dc_motors(self._all_motors)
