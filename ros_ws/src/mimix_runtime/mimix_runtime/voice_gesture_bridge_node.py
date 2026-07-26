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
    MAX_DURATION_MS = 10000
    # El firmware actual solo admite encendido/dirección para las ruedas: no
    # tiene PWM para regular velocidad. Por eso el vaivén usa la pulsación
    # mínima permitida. Durante la respuesta repite el vaivén cada 2.5 s.
    WHEEL_PULSE_MS = 100
    WHEEL_START_DELAY_S = 0.25
    WHEEL_RETURN_DELAY_S = 0.50
    WHEEL_CYCLE_INTERVAL_S = 2.50
    WHEEL_DEADLINE_MARGIN_S = 0.20
    # La base es la mirada directa al estudiante. S1/S2 tienen amplitud
    # suficiente para resultar visibles; S3 gira a los lados. S4/S5 solo
    # acompañan con un cabeceo leve para no llevar la mirada hacia abajo.
    # Las poses intermedias hacen que cada desplazamiento sea escalonado.
    TALK_FRAMES = (
        (((1, 180), (2, 480), (3, 400), (4, 150), (5, 400)), 0.8),
        (((1, 220), (2, 455), (3, 365), (4, 170), (5, 382)), 0.55),
        (((1, 260), (2, 430), (3, 330), (4, 195), (5, 355)), 1.35),
        (((1, 220), (2, 455), (3, 365), (4, 170), (5, 382)), 0.55),
        (((1, 180), (2, 480), (3, 400), (4, 150), (5, 400)), 0.9),
        (((1, 225), (2, 450), (3, 435), (4, 172), (5, 380)), 0.55),
        (((1, 270), (2, 420), (3, 470), (4, 200), (5, 350)), 1.35),
        (((1, 225), (2, 450), (3, 435), (4, 172), (5, 380)), 0.55),
        (((1, 180), (2, 480), (3, 400), (4, 150), (5, 400)), 0.9),
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
        self.scheduled_wheel_actions = []
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
            def write_json(self, code, payload):
                body = json.dumps(payload).encode('utf-8')
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path.split('?', 1)[0] != '/health':
                    self.send_error(404)
                    return
                self.write_json(200, {
                    'ok': True,
                    'gesture_active': bridge.gesture_active,
                })

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
                    self.write_json(400, {'accepted': False, 'message': str(error)})
                    return

                bridge.pending_durations.put(duration)
                self.write_json(202, {'accepted': True, 'duration_ms': duration})

            def log_message(self, _format, *_args):
                return

        return GestureRequestHandler

    def publish_request(self, action, payload=None, max_duration_ms=100):
        self.request_sequence += 1
        request = MotionRequest()
        request.id = f'voice-talk-{now_ms()}-{self.request_sequence}'
        request.action = action
        request.max_duration_ms = max_duration_ms
        request.payload_json = json.dumps(payload or {})
        self.motion_publisher.publish(request)

    def publish_frame(self):
        frame, pause_seconds = self.TALK_FRAMES[self.frame_index]
        for servo_number, pulse in frame:
            self.publish_request(f'servo_{servo_number}', {'pulse': pulse})
        self.frame_index = (self.frame_index + 1) % len(self.TALK_FRAMES)
        return pause_seconds

    def start_or_extend_gesture(self, duration_ms):
        now = time.monotonic()
        deadline = now + duration_ms / 1000.0
        if not self.gesture_active:
            self.gesture_active = True
            self.frame_index = 0
            self.next_frame_at = now
            self.scheduled_wheel_actions = self.wheel_actions_for_duration(
                now, duration_ms
            )
        self.gesture_deadline = max(self.gesture_deadline, deadline)
        self.status_publisher.publish(status(
            'voice_gesture_bridge', 'gesture_requested', f'{duration_ms} ms',
        ))

    def wheel_actions_for_duration(self, started_at, duration_ms):
        """Programa pares adelante/atrás que siempre finalizan antes del gesto."""
        deadline = started_at + duration_ms / 1000.0 - self.WHEEL_DEADLINE_MARGIN_S
        forward_at = started_at + self.WHEEL_START_DELAY_S
        actions = []
        while forward_at + self.WHEEL_RETURN_DELAY_S <= deadline:
            actions.extend((
                (forward_at, 'forward'),
                (forward_at + self.WHEEL_RETURN_DELAY_S, 'backward'),
            ))
            forward_at += self.WHEEL_CYCLE_INTERVAL_S
        return actions

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
            # La parada no mueve servos y evita que una anomalía del puente H
            # deje las ruedas activas al terminar el gesto.
            self.publish_request('stop')
            self.publish_request('base_pose')
            self.gesture_active = False
            self.scheduled_wheel_actions = []
            self.status_publisher.publish(status('voice_gesture_bridge', 'gesture_complete_base'))
            return

        while (
            self.scheduled_wheel_actions
            and now >= self.scheduled_wheel_actions[0][0]
        ):
            _scheduled_at, action = self.scheduled_wheel_actions.pop(0)
            self.publish_request(action, max_duration_ms=self.WHEEL_PULSE_MS)
            self.status_publisher.publish(status(
                'voice_gesture_bridge', 'wheel_pulse', f'{action} {self.WHEEL_PULSE_MS} ms',
            ))

        if now >= self.next_frame_at:
            self.next_frame_at = now + self.publish_frame()

    def destroy_node(self):
        if self.gesture_active:
            self.publish_request('stop')
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
