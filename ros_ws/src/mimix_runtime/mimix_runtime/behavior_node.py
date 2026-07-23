"""Traduce intenciones simbólicas en comandos web o solicitudes de movimiento."""

import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from mimix_interfaces.msg import BehaviorIntent, MotionRequest, RobotStatus
from .common import now_ms, status


DESTINATIONS = {
    'open_world': 'world',
    'open_mathematics': 'mathematics',
    'open_science': 'science',
}
MOTION_INTENTS = {'greet', 'celebrate', 'look_at_student'}


class BehaviorNode(Node):
    def __init__(self):
        super().__init__('mimix_behavior')
        self.web_publisher = self.create_publisher(String, '/mimix/web/command', 10)
        self.motion_publisher = self.create_publisher(MotionRequest, '/mimix/motion/request', 10)
        self.status_publisher = self.create_publisher(RobotStatus, '/mimix/robot/status', 10)
        self.create_subscription(BehaviorIntent, '/mimix/behavior/intent', self.on_intent, 10)
        self.status_publisher.publish(status('behavior', 'ready'))

    def on_intent(self, intent):
        if intent.expires_at_ms and intent.expires_at_ms < now_ms():
            self.status_publisher.publish(status('behavior', 'expired_intent', intent.id))
            return

        if intent.intent in DESTINATIONS:
            command = String()
            command.data = json.dumps({
                'action': 'navigate_to',
                'destination': DESTINATIONS[intent.intent],
                'source': intent.source or 'ros2',
            })
            self.web_publisher.publish(command)
            self.status_publisher.publish(status('behavior', 'web_navigation', intent.intent))
            return

        if intent.intent in MOTION_INTENTS:
            request = MotionRequest()
            request.id = intent.id
            request.action = intent.intent
            request.max_duration_ms = 2000
            request.payload_json = intent.payload_json or '{}'
            self.motion_publisher.publish(request)
            self.status_publisher.publish(status('behavior', 'motion_requested', intent.intent))
            return

        self.status_publisher.publish(status('behavior', 'unknown_intent', intent.intent))


def main(args=None):
    rclpy.init(args=args)
    node = BehaviorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
