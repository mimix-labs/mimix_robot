"""Único punto previsto para el USB del ESP32; inicialmente solo simulación."""

import rclpy
from rclpy.node import Node

from mimix_interfaces.msg import MotionRequest, RobotStatus
from .common import status


class UsbSerialBridge(Node):
    def __init__(self):
        super().__init__('mimix_usb_serial_bridge')
        self.declare_parameter('port', '')
        self.declare_parameter('baud', 115200)
        self.declare_parameter('dry_run', True)
        self.port = self.get_parameter('port').value
        self.dry_run = bool(self.get_parameter('dry_run').value)
        self.status_publisher = self.create_publisher(RobotStatus, '/mimix/robot/status', 10)
        self.create_subscription(MotionRequest, '/mimix/motion/approved', self.on_motion, 10)

        if self.dry_run:
            detail = 'Salida USB desactivada (dry_run=true).'
            if self.port:
                detail += f' Puerto reservado: {self.port}'
            self.status_publisher.publish(status('usb_serial_bridge', 'dry_run', detail))
        else:
            self.status_publisher.publish(status(
                'usb_serial_bridge',
                'blocked',
                'El protocolo ESP32 aún no está definido; no se abre ningún puerto.',
            ))

    def on_motion(self, request):
        if self.dry_run:
            self.get_logger().info(
                f'[DRY RUN] Acción aprobada: {request.action} ({request.max_duration_ms} ms)'
            )
            self.status_publisher.publish(status('usb_serial_bridge', 'simulated', request.action))
            return

        self.get_logger().error('Salida USB bloqueada: falta definir el protocolo de firmware.')
        self.status_publisher.publish(status('usb_serial_bridge', 'blocked', request.action))


def main(args=None):
    rclpy.init(args=args)
    node = UsbSerialBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
