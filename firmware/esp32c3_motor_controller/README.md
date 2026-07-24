# ESP32-C3 + TB6612FNG

Firmware de tracción de Mimix. El ESP32-C3 se conecta por USB-C a la Jetson y
solo acepta comandos seriales delimitados por salto de línea a 115200 baudios.
Al arrancar deja los motores detenidos; no hay prueba automática.

## Conexiones definidas

| ESP32-C3 SuperMini | TB6612FNG | Función |
| --- | --- | --- |
| GPIO 3 | PWMA | Velocidad del motor A (izquierdo). |
| GPIO 4 | AIN1 | Dirección motor A. |
| GPIO 5 | AIN2 | Dirección motor A. |
| GPIO 1 | STBY | Habilita el TB6612FNG. |
| GPIO 6 | BIN1 | Dirección motor B (derecho). |
| GPIO 7 | BIN2 | Dirección motor B. |
| GPIO 10 | PWMB | Velocidad del motor B. |
| 3V3 | VCC | Alimentación lógica del TB6612FNG. |
| GND | GND | Tierra común. |
| Batería/fuente de motores | VM | Alimentación de los motores. |

Los motores se conectan a `A01/A02` y `B01/B02` del TB6612FNG. GPIO 8 y 9 se
reservan para I2C y no intervienen en este firmware.

## Protocolo `MIMIX_MOTOR_V1`

| Orden | Respuesta | Efecto |
| --- | --- | --- |
| `PING` | `PONG` | Comprueba la conexión. |
| `STOP` | `OK STOP` | Detiene inmediatamente ambos motores. |
| `MOVE FORWARD 500 80` | `OK MOVE FORWARD` | Mueve en la dirección indicada. |

Las direcciones aceptadas son `FORWARD`, `BACKWARD`, `LEFT` y `RIGHT`.
La duración debe estar entre 1 y 3000 ms; la velocidad entre 1 y 180. Al
cumplirse el tiempo, el firmware detiene los motores automáticamente y emite
`EVENT MOTION_TIMEOUT STOP`. Cualquier orden inválida también detiene motores.

## Carga y prueba

1. En Arduino IDE selecciona la placa ESP32-C3 correcta y el puerto USB.
2. Si el menú lo ofrece, activa **USB CDC On Boot**.
3. Carga `esp32c3_motor_controller.ino`.
4. Abre el monitor serial a 115200; al reiniciar debe aparecer
   `READY MIMIX_MOTOR_V1` y no debe moverse el robot.

La primera orden física debe enviarse desde ROS, no desde el monitor serial;
el procedimiento está en [`ros_ws/README.md`](../../ros_ws/README.md).

## Seguridad eléctrica

- La fuente de motores va a `VM`; nunca alimentar motores desde el pin 3V3
  del ESP32.
- Usar 3V3 en `VCC` para lógica compatible con el ESP32.
- Unir GND de ESP32, TB6612FNG y la fuente de motores.
- Probar con las ruedas elevadas antes de colocar el robot en el suelo.
