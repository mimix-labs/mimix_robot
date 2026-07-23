# Mimix ROS 2 workspace

Esta es la capa de coordinación de Mimix. No sustituye a Mimix Web ni al
servicio de percepción: conecta sus eventos con comportamientos seguros del
robot.

## Diseño inicial

```text
Mimix Web <-> web_bridge <-> /mimix/web/context y /mimix/web/command
                                     ^
Fuente de percepción -> perception_adapter -> /mimix/perception/event
                                     |
                              behavior_node
                               |             |
                         web_bridge      safety_node -> usb_serial_bridge
```

La percepción es genérica. Un evento puede venir de MediaPipe Hands, Pose,
Face Landmarker, Object Detector u otra fuente, identificando `source` y
`modality`; ROS no queda atado a las manos.

El puente USB inicia siempre con `dry_run:=true` y el filtro de seguridad con
`armed:=false`. En este estado no se escribe nada al ESP32. La definición del
protocolo de firmware será una etapa posterior.

## Instalar en Jetson (Ubuntu 24.04)

Instala ROS 2 Jazzy para Ubuntu 24.04 siguiendo la documentación oficial de
ROS y añade las dependencias del workspace:

```bash
sudo apt install ros-jazzy-ros-base python3-colcon-common-extensions python3-rosdep python3-serial
sudo rosdep init
rosdep update
```

Desde este directorio:

```bash
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

## Ejecutar de forma segura

Primero inicia Mimix Web con el lanzador existente. En otra terminal:

```bash
cd ~/mimix_robot/ros_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch mimix_bringup robot.launch.py
```

Esto comunica ROS con el backend existente de Mimix Web en `:4000`, pero no
activa motores. Para inspeccionar eventos:

```bash
ros2 topic echo /mimix/robot/status
ros2 topic echo /mimix/web/context
```

Cuando el ESP32 esté conectado por USB-C a un puerto USB anfitrión de la
Jetson, se identificará primero su ruta estable con:

```bash
ls -l /dev/serial/by-id/
```

No pases esa ruta al launch ni desactives `dry_run` hasta definir y cargar el
protocolo del firmware.
