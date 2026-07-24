# ESP32-C3 + puente H

Firmware de tracción de Mimix. El ESP32-C3 recibe órdenes desde la Jetson por
USB-C a 115200 baudios y controla únicamente las cuatro entradas de dirección
del puente H. Al arrancar, deja los cuatro pines en bajo y no mueve el robot.

## Conexiones

| ESP32-C3 SuperMini | Puente H | Función |
| --- | --- | --- |
| GPIO 4 | IN1 | Dirección motor A. |
| GPIO 5 | IN2 | Dirección motor A. |
| GPIO 6 | IN3 | Dirección motor B. |
| GPIO 7 | IN4 | Dirección motor B. |
| GND | GND | Tierra común. |

GPIO 8 y GPIO 9 quedan reservados para I2C. Esta primera etapa no controla
velocidad: el puente H debe tener sus líneas de habilitación activas, por
ejemplo mediante los jumpers `ENA` y `ENB` si el módulo los incluye.

## Protocolo `MIMIX_MOTOR_V2`

| Orden | Respuesta | Efecto |
| --- | --- | --- |
| `PING` | `PONG` | Comprueba USB serial. |
| `STOP` | `OK STOP` | Detiene ambos motores. |
| `MOVE FORWARD 500` | `OK MOVE FORWARD` | Mueve en la dirección indicada. |

Las direcciones válidas son `FORWARD`, `BACKWARD`, `LEFT` y `RIGHT`. La
duración está limitada a 3000 ms y al vencer se ejecuta una parada automática.
Una orden inválida también detiene el robot.

## Carga y prueba

1. Selecciona la placa ESP32-C3 correcta en Arduino IDE y carga el `.ino`.
2. Si Arduino IDE lo ofrece, activa **USB CDC On Boot**.
3. El monitor serial a 115200 debe mostrar `READY MIMIX_MOTOR_V2`; el robot no
   debe moverse.
4. Cierra el monitor serial antes de iniciar la prueba ROS, porque ambos no
   pueden abrir el mismo puerto USB a la vez.

La primera prueba física desde ROS está en
[`ros_ws/README.md`](../../ros_ws/README.md). Hazla siempre con ruedas elevadas.
