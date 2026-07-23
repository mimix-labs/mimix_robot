from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    web_url = LaunchConfiguration('web_url')
    bridge_token = LaunchConfiguration('bridge_token')
    serial_port = LaunchConfiguration('serial_port')
    serial_baud = LaunchConfiguration('serial_baud')
    dry_run = LaunchConfiguration('dry_run')
    armed = LaunchConfiguration('armed')

    return LaunchDescription([
        DeclareLaunchArgument('web_url', default_value='http://127.0.0.1:4000'),
        DeclareLaunchArgument('bridge_token', default_value=''),
        DeclareLaunchArgument('serial_port', default_value=''),
        DeclareLaunchArgument('serial_baud', default_value='115200'),
        DeclareLaunchArgument('dry_run', default_value='true'),
        DeclareLaunchArgument('armed', default_value='false'),
        Node(
            package='mimix_runtime',
            executable='web_bridge',
            name='web_bridge',
            parameters=[{'web_url': web_url, 'bridge_token': bridge_token}],
        ),
        Node(
            package='mimix_runtime',
            executable='perception_adapter',
            name='perception_adapter',
        ),
        Node(
            package='mimix_runtime',
            executable='behavior',
            name='behavior',
        ),
        Node(
            package='mimix_runtime',
            executable='safety',
            name='safety',
            parameters=[{'armed': armed}],
        ),
        Node(
            package='mimix_runtime',
            executable='usb_serial_bridge',
            name='usb_serial_bridge',
            parameters=[
                {'port': serial_port, 'baud': serial_baud, 'dry_run': dry_run},
            ],
        ),
    ])
