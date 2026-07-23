import time

from mimix_interfaces.msg import RobotStatus


def now_ms():
    return int(time.time() * 1000)


def status(component, state, detail=''):
    message = RobotStatus()
    message.component = component
    message.state = state
    message.detail = detail
    message.timestamp_ms = now_ms()
    return message
