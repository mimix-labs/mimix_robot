"""Convierte JSON genérico de una fuente externa a PerceptionEvent."""

import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from mimix_interfaces.msg import PerceptionEvent, RobotStatus
from .common import now_ms, status


class PerceptionAdapter(Node):
    def __init__(self):
        super().__init__('mimix_perception_adapter')
        self.publisher = self.create_publisher(PerceptionEvent, '/mimix/perception/event', 10)
        self.status_publisher = self.create_publisher(RobotStatus, '/mimix/robot/status', 10)
        self.create_subscription(String, '/mimix/perception/raw', self.on_raw_event, 10)
        self.status_publisher.publish(status('perception_adapter', 'ready'))

    def on_raw_event(self, message):
        try:
            payload = json.loads(message.data)
            if not isinstance(payload, dict):
                raise ValueError('El evento debe ser un objeto JSON.')
            event = PerceptionEvent()
            event.source = str(payload.get('source', 'unknown'))
            event.modality = str(payload.get('modality', 'unknown'))
            event.confidence = float(payload.get('confidence', 0.0))
            event.timestamp_ms = int(payload.get('timestamp_ms', now_ms()))
            event.payload_json = json.dumps(payload.get('payload', {}), ensure_ascii=False)
            self.publisher.publish(event)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self.get_logger().warning(f'Evento de percepción inválido: {error}')
            self.status_publisher.publish(status('perception_adapter', 'invalid_event', str(error)))


def main(args=None):
    rclpy.init(args=args)
    node = PerceptionAdapter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
