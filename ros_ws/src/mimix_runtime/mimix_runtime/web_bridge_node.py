"""Puente pequeño entre ROS 2 y los endpoints ya existentes de Mimix Web."""

import json
from urllib.error import URLError
from urllib.request import Request, urlopen

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from mimix_interfaces.msg import RobotStatus
from .common import status


class WebBridge(Node):
    def __init__(self):
        super().__init__('mimix_web_bridge')
        self.declare_parameter('web_url', 'http://127.0.0.1:4000')
        self.declare_parameter('bridge_token', '')
        self.declare_parameter('poll_seconds', 1.0)
        self.web_url = self.get_parameter('web_url').value.rstrip('/')
        self.bridge_token = self.get_parameter('bridge_token').value
        poll_seconds = float(self.get_parameter('poll_seconds').value)

        self.context_publisher = self.create_publisher(String, '/mimix/web/context', 10)
        self.status_publisher = self.create_publisher(RobotStatus, '/mimix/robot/status', 10)
        self.create_subscription(String, '/mimix/web/command', self.on_command, 10)
        self.create_timer(max(poll_seconds, 0.2), self.publish_context)
        self.status_publisher.publish(status('web_bridge', 'starting', self.web_url))

    def request_json(self, path, method='GET', payload=None):
        headers = {'Accept': 'application/json'}
        if self.bridge_token:
            headers['Authorization'] = f'Bearer {self.bridge_token}'
        data = None
        if payload is not None:
            headers['Content-Type'] = 'application/json'
            data = json.dumps(payload).encode('utf-8')
        request = Request(f'{self.web_url}{path}', data=data, headers=headers, method=method)
        with urlopen(request, timeout=2) as response:
            return json.loads(response.read().decode('utf-8'))

    def publish_context(self):
        try:
            context = self.request_json('/api/robot/context')
            message = String()
            message.data = json.dumps(context, ensure_ascii=False)
            self.context_publisher.publish(message)
            self.status_publisher.publish(status('web_bridge', 'connected'))
        except (URLError, OSError, ValueError) as error:
            self.status_publisher.publish(status('web_bridge', 'waiting', str(error)))

    def on_command(self, message):
        try:
            command = json.loads(message.data)
            action = command.get('action')
            destination = command.get('destination')
            if action != 'navigate_to' or destination not in {'world', 'mathematics', 'science'}:
                raise ValueError('Solo se admite navigate_to a world, mathematics o science.')
            self.request_json('/api/robot/commands', 'POST', command)
            self.status_publisher.publish(status('web_bridge', 'command_sent', destination))
        except (URLError, OSError, ValueError, json.JSONDecodeError) as error:
            self.get_logger().warning(f'Comando web rechazado: {error}')
            self.status_publisher.publish(status('web_bridge', 'command_error', str(error)))


def main(args=None):
    rclpy.init(args=args)
    node = WebBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
