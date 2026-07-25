"""Puente HTTP local: la voz solicita gestos sin controlar hardware directamente."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from queue import Empty, Queue
from threading import Thread

import rclpy
from rclpy.node import Node

from mimix_interfaces.msg import MotionRequest, RobotStatus
from .common import now_ms, status


class VoiceGestureBridge(Node):
    """Acepta POST local /talk y publica una solicitud ROS de gesto conversacional."""

    MIN_DURATION_MS = 1000
    MAX_DURATION_MS = 5000

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

        self.create_timer(0.05, self.publish_pending_gestures)

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

    def publish_pending_gestures(self):
        while True:
            try:
                duration = self.pending_durations.get_nowait()
            except Empty:
                return

            request = MotionRequest()
            request.id = f'voice-talk-{now_ms()}'
            request.action = 'conversation_gesture'
            request.max_duration_ms = duration
            request.payload_json = json.dumps({'duration_ms': duration})
            self.motion_publisher.publish(request)
            self.status_publisher.publish(status(
                'voice_gesture_bridge', 'gesture_requested', f'{duration} ms',
            ))

    def destroy_node(self):
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
