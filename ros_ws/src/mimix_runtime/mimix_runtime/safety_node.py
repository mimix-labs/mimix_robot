"""Freno lógico entre comportamiento y hardware."""

import rclpy
from rclpy.node import Node
from std_srvs.srv import SetBool

from mimix_interfaces.msg import MotionRequest, RobotStatus
from .common import status


class SafetyNode(Node):
    def __init__(self):
        super().__init__('mimix_safety')
        self.declare_parameter('armed', False)
        self.armed = bool(self.get_parameter('armed').value)
        self.approved_publisher = self.create_publisher(MotionRequest, '/mimix/motion/approved', 10)
        self.status_publisher = self.create_publisher(RobotStatus, '/mimix/robot/status', 10)
        self.create_subscription(MotionRequest, '/mimix/motion/request', self.on_request, 10)
        self.create_service(SetBool, '/mimix/safety/arm', self.on_arm)
        self.publish_state('El robot inicia desarmado.' if not self.armed else 'Armado por parámetro de launch.')

    def publish_state(self, detail=''):
        state = 'armed' if self.armed else 'disarmed'
        self.status_publisher.publish(status('safety', state, detail))

    def on_arm(self, request, response):
        self.armed = bool(request.data)
        response.success = True
        response.message = 'Movimiento habilitado.' if self.armed else 'Movimiento bloqueado.'
        self.publish_state(response.message)
        return response

    def on_request(self, request):
        if not self.armed:
            self.status_publisher.publish(status('safety', 'blocked', f'{request.action}: robot desarmado'))
            return
        approved = MotionRequest()
        approved.id = request.id
        approved.action = request.action
        approved.max_duration_ms = min(max(request.max_duration_ms, 100), 5000)
        approved.payload_json = request.payload_json
        self.approved_publisher.publish(approved)
        self.status_publisher.publish(status('safety', 'approved', request.action))


def main(args=None):
    rclpy.init(args=args)
    node = SafetyNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
