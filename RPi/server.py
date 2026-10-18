"""Flask server that receives commands and vision-based movement updates."""
import logging

from flask import Flask, request, jsonify

from .config import VALID_TARGETS

logging.getLogger('werkzeug').disabled = True


def create_app(robot):
    app = Flask(__name__)

    @app.route('/command', methods=['POST'])
    def command():
        data = request.get_json()
        object_name = data.get('object', '').lower()

        if object_name in VALID_TARGETS:
            robot.start_seeking(object_name)
            return jsonify({"status": "success"})
        if object_name == 'stop':
            robot.stop()
            return jsonify({"status": "success"})
        return jsonify({"status": "error", "message": "Invalid command"})

    @app.route('/movement_command', methods=['POST'])
    def movement_command():
        """Receives movement commands from the main server based on vision analysis."""
        data = request.get_json()
        robot.handle_vision_update(
            detected=data.get('detected', False),
            command=data.get('command', 'rotate'),
            offset_x=data.get('offset_x', 0),
        )
        return jsonify({"status": "success"})

    return app
