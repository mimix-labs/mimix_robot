"""Único punto ROS 2 que escribe el protocolo serial del ESP32-C3."""

import time

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
        self.baud = int(self.get_parameter('baud').value)
        self.dry_run = bool(self.get_parameter('dry_run').value)
        self.serial_connection = None
        self.status_publisher = self.create_publisher(RobotStatus, '/mimix/robot/status', 10)
        self.create_subscription(MotionRequest, '/mimix/motion/approved', self.on_motion, 10)

        if self.dry_run:
            detail = 'Salida USB desactivada (dry_run=true).'
            if self.port:
                detail += f' Puerto reservado: {self.port}'
            self.status_publisher.publish(status('usb_serial_bridge', 'dry_run', detail))
            return

        self.connect()

    def connect(self):
        self.close_serial()

        if not self.port:
            self.status_publisher.publish(status(
                'usb_serial_bridge', 'blocked', 'Falta serial_port; no se abre ningún puerto.',
            ))
            return False

        try:
            import serial

            self.serial_connection = serial.Serial(
                self.port,
                baudrate=self.baud,
                timeout=0.5,
                write_timeout=0.5,
            )
            # Abrir USB CDC puede reiniciar el ESP32-C3; el firmware arranca detenido.
            time.sleep(1.0)
            self.serial_connection.reset_input_buffer()
            self.send_line('STOP')
            self.serial_connection.readline()
            self.send_line('PING')
            response = self.serial_connection.readline().decode('utf-8', errors='replace').strip()
            self.status_publisher.publish(status(
                'usb_serial_bridge', 'connected', f'{self.port}: {response or "sin respuesta inicial"}',
            ))
            return True
        except (ImportError, OSError, ValueError) as error:
            self.get_logger().error(f'No se pudo abrir el puerto serial: {error}')
            self.close_serial()
            self.status_publisher.publish(status('usb_serial_bridge', 'error', str(error)))
            return False

    def close_serial(self):
        if not self.serial_connection:
            return
        try:
            self.serial_connection.close()
        except OSError:
            pass
        finally:
            self.serial_connection = None

    def send_line(self, command):
        if not self.serial_connection:
            raise OSError('Puerto serial no conectado.')
        self.serial_connection.write(f'{command}\n'.encode('utf-8'))
        self.serial_connection.flush()

    def motion_command(self, request):
        action = request.action.lower()
        if action == 'stop':
            return 'STOP'

        directions = {
            'forward': 'FORWARD',
            'backward': 'BACKWARD',
            'left': 'LEFT',
            'right': 'RIGHT',
        }
        if action not in directions:
            raise ValueError(f'Acción no admitida por el firmware: {request.action}')

        duration = min(max(int(request.max_duration_ms), 100), 3000)
        return f'MOVE {directions[action]} {duration}'

    def on_motion(self, request):
        if self.dry_run:
            self.get_logger().info(
                f'[DRY RUN] Acción aprobada: {request.action} ({request.max_duration_ms} ms)'
            )
            self.status_publisher.publish(status('usb_serial_bridge', 'simulated', request.action))
            return

        try:
            command = self.motion_command(request)
            if not self.serial_connection and not self.connect():
                raise OSError('Puerto serial no conectado.')
            self.send_line(command)
            response = self.serial_connection.readline().decode('utf-8', errors='replace').strip()
            self.status_publisher.publish(status(
                'usb_serial_bridge', 'command_sent', f'{command} | {response or "sin respuesta"}',
            ))
        except (OSError, ValueError) as error:
            self.get_logger().error(f'No se pudo enviar movimiento: {error}')
            # No reenviamos un movimiento tras un fallo: podría haberse recibido
            # parcialmente. Solo recuperamos el puerto y el usuario decide repetirlo.
            reconnected = self.connect()
            state = 'reconnected_reissue_command' if reconnected else 'error'
            detail = 'Puerto recuperado; vuelve a enviar la orden.' if reconnected else str(error)
            self.status_publisher.publish(status('usb_serial_bridge', state, detail))

    def destroy_node(self):
        if self.serial_connection:
            try:
                self.send_line('STOP')
            except OSError:
                pass
            finally:
                self.close_serial()
        return super().destroy_node()


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
