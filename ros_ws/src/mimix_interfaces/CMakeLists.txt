cmake_minimum_required(VERSION 3.8)
project(mimix_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/PerceptionEvent.msg"
  "msg/BehaviorIntent.msg"
  "msg/MotionRequest.msg"
  "msg/RobotStatus.msg"
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
