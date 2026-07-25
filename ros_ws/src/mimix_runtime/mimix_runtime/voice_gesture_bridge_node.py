"""Convierte eventos locales de voz en una animación ROS de servos."""

import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from queue import Empty, Queue
from threading import Thread

import rclpy
from rclpy.node import Node

from mimix_interfaces.msg import MotionRequest, RobotStatus
from .common import now_ms, status


class VoiceGestureBridge(Node):
    """La voz solicita duración; ROS programa los servos y finaliza en BASE."""

    MIN_DURATION_MS = 1000
    MAX_DURATION_MS = 7000
    FRAME_INTERVAL_SECONDS = 0.70
    # Ojos (1 y 2), giro de cabeza (3) y cabeceo (4 y 5). Las variaciones
    # pequeñas entre cuadros permiten que los servos lleguen suavemente.
    TALK_FRAMES = (
        ((1, 180), (2, 480), (3, 400), (4, 150), (5, 400)),
        ((1, 186), (2, 474), (3, 395), (4, 156), (5, 394)),
        ((1, 194), (2, 466), (3, 385), (4, 164), (5, 386)),
        ((1, 202), (2, 458), (3, 372), (4, 172), (5, 378)),
        ((1, 196), (2, 464), (3, 382), (4, 166), (5, 384)),
        ((1, 210), (2, 455), (3, 370), (4, 175), (5, 375)),
        ((1, 198), (2, 462), (3, 405), (4, 166), (5, 384)),
        ((1, 190), (2, 470), (3, 420), (4, 160), (5, 390)),
        ((1, 184), (2, 476), (3, 410), (4, 154), (5, 396)),
        ((1, 180), (2, 480), (3, 400), (4, 150), (5, 400)),
    )

    def __init__(self):
        super().__init__('mimix_voice_gesture_bridge')
        self.declare_parameter('host', '127.0.0.1')
        self.declare_parameter('port', 8092)
        self.host = self.get_parameter('host').value
        self.port = int(self.get_parameter('port').value)
        self.pending_durations = Queue()
        self.motion_publisher = self.create_publisher(MotionRequest, '/mimix/motion/request', 10)
        self.status_publisher = self.create_publisher(RobotStatus, '/mimix/robot/status', 10)
        self.server = None
        self.server_thread = None
        self.gesture_active = False
        self.gesture_deadline = 0.0
        self.next_frame_at = 0.0
        self.frame_index = 0
        self.request_sequence = 0

        try:
            self.server = ThreadingHTTPServer((self.host, self.port), self.make_handler())
            self.server.daemon_threads = True
            self.server_thread = Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            self.status_publisher.publish(status(
                'voice_gesture_bridge', 'listening', f'http://{self.host}:{self.port}/talk',
            ))
        except OSError as error:
            self.get_logger().error(f'No se pudo iniciar el puente de gestos: {error}')
            self.status_publisher.publish(status('voice_gesture_bridge', 'error', str(error)))

        self.create_timer(0.05, self.update_gesture)

    def make_handler(self):
        bridge = self

        class GestureRequestHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path.split('?', 1)[0] != '/talk':
                    self.send_error(404)
                    return
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    if length <= 0 or length > 4096:
                        raise ValueError('Cuerpo inválido.')
                    payload = json.loads(self.rfile.read(length).decode('utf-8'))
                    duration = int(payload.get('duration_ms'))
                    duration = min(max(duration, bridge.MIN_DURATION_MS), bridge.MAX_DURATION_MS)
                except (TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as error:
                    body = json.dumps({'accepted': False, 'message': str(error)}).encode('utf-8')
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return

                bridge.pending_durations.put(duration)
                body = json.dumps({'accepted': True, 'duration_ms': duration}).encode('utf-8')
                self.send_response(202)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, _format, *_args):
                return

        return GestureRequestHandler

    def publish_request(self, action, payload=None):
        self.request_sequence += 1
        request = MotionRequest()
        request.id = f'voice-talk-{now_ms()}-{self.request_sequence}'
        request.action = action
        request.max_duration_ms = 100
        request.payload_json = json.dumps(payload or {})
        self.motion_publisher.publish(request)

    def publish_frame(self):
        for servo_number, pulse in self.TALK_FRAMES[self.frame_index]:
            self.publish_request(f'servo_{servo_number}', {'pulse': pulse})
        self.frame_index = (self.frame_index + 1) % len(self.TALK_FRAMES)

    def start_or_extend_gesture(self, duration_ms):
        now = time.monotonic()
        deadline = now + duration_ms / 1000.0
        if not self.gesture_active:
            self.gesture_active = True
            self.frame_index = 0
            self.next_frame_at = now
        self.gesture_deadline = max(self.gesture_deadline, deadline)
        self.status_publisher.publish(status(
            'voice_gesture_bridge', 'gesture_requested', f'{duration_ms} ms',
        ))

    def update_gesture(self):
        while True:
            try:
                self.start_or_extend_gesture(self.pending_durations.get_nowait())
            except Empty:
                break

        if not self.gesture_active:
            return

        now = time.monotonic()
        if now >= self.gesture_deadline:
            self.publish_request('base_pose')
            self.gesture_active = False
            self.status_publisher.publish(status('voice_gesture_bridge', 'gesture_complete_base'))
            return

        if now >= self.next_frame_at:
            self.publish_frame()
            self.next_frame_at = now + self.FRAME_INTERVAL_SECONDS

    def destroy_node(self):
        if self.gesture_active:
            self.publish_request('base_pose')
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = VoiceGestureBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
