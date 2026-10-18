#!/usr/bin/env python3
"""Entry point: starts the robot control loop and the command server."""
import threading

from robot.config import COMMAND_SERVER_HOST, COMMAND_SERVER_PORT
from robot.controller import RobotController
from robot.server import create_app


def main():
    robot = None
    try:
        robot = RobotController()

        thread = threading.Thread(target=robot.main_loop, daemon=True)
        thread.start()

        app = create_app(robot)
        print(f"🚀 Starting command server on port {COMMAND_SERVER_PORT}...")
        app.run(host=COMMAND_SERVER_HOST, port=COMMAND_SERVER_PORT)
    except Exception as e:
        print(f"MAIN ERROR: {e}")
    finally:
        if robot:
            robot.cleanup()


if __name__ == '__main__':
    main()
