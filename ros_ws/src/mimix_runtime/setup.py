from glob import glob
from setuptools import find_packages, setup

package_name = 'mimix_runtime'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Mimix Labs',
    maintainer_email='edwarfin24@gmail.com',
    description='Nodos ROS 2 mínimos para Mimix.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'web_bridge = mimix_runtime.web_bridge_node:main',
            'perception_adapter = mimix_runtime.perception_adapter_node:main',
            'behavior = mimix_runtime.behavior_node:main',
            'safety = mimix_runtime.safety_node:main',
            'usb_serial_bridge = mimix_runtime.usb_serial_bridge_node:main',
        ],
    },
)
