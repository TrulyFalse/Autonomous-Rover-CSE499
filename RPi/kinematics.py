"""Inverse kinematics for the two-link arm."""
import math

from .config import L1, L2, H_BASE


def calculate_angles(x_target, z_target_ground=0):
    """Return (shoulder_servo_angle, elbow_servo_angle) in degrees.

    Raises ValueError if the target is out of reach.
    """
    z_target = z_target_ground - H_BASE
    d = math.sqrt(x_target ** 2 + z_target ** 2)
    if d > (L1 + L2 - 2.5):
        raise ValueError("Target out of reach")

    cos_theta2 = (d ** 2 - L1 ** 2 - L2 ** 2) / (2 * L1 * L2)
    cos_theta2 = max(min(cos_theta2, 1), -1)
    theta2_rad = math.acos(cos_theta2)
    theta2_deg = math.degrees(theta2_rad)

    k1 = L1 + L2 * math.cos(theta2_rad)
    k2 = L2 * math.sin(theta2_rad)
    theta1_rad = math.atan2(z_target, x_target) - math.atan2(k2, k1)
    theta1_deg = math.degrees(theta1_rad)

    servo_shoulder_angle = max(0, min(180 + theta1_deg, 120))
    servo_elbow_angle = min(theta2_deg, 135)
    return servo_shoulder_angle, servo_elbow_angle
