# ESP32-C3 + puente H + PCA9685

El ESP32-C3 recibe ordenes desde la Jetson por USB-C a 115200 baudios. Controla
la traccion mediante un puente H de cuatro entradas y los cinco servos mediante
un PCA9685. Al arrancar, los motores quedan detenidos y los servos pasan a su
posicion base calibrada.

## Conexiones

| ESP32-C3 SuperMini | Destino | Funcion |
| --- | --- | --- |
| GPIO 3 | IN1 | Direccion motor A (izquierdo). |
| GPIO 5 | IN2 | Direccion motor A (izquierdo). |
| GPIO 6 | IN3 | Direccion motor B (derecho). |
| GPIO 7 | IN4 | Direccion motor B (derecho). |
| GPIO 8 | SDA del PCA9685 | Bus I2C. |
| GPIO 9 | SCL del PCA9685 | Bus I2C. |
| GND | GND | Tierra comun. |

El PCA9685 usa la direccion I2C `0x40`, frecuencia de 50 Hz y los canales 0 a
4. Esta etapa no controla velocidad: el puente H debe tener sus lineas de
habilitacion activas, por ejemplo mediante los jumpers `ENA` y `ENB` si el
modulo los incluye.

## Calibracion de servos

Los valores son pulsos PWM calibrados fisicamente, no grados.

| Servo | Canal PCA9685 | Rango seguro | Base |
| --- | --- | --- | --- |
| 1 | 0 | 180-320 | 180 |
| 2 | 1 | 400-480 | 480 |
| 3 | 2 | 180-600 | 375 |
| 4 | 3 | 150-300 | 150 |
| 5 | 4 | 150-400 | 400 |

## Protocolo `MIMIX_ROBOT_V3`

| Orden | Respuesta | Efecto |
| --- | --- | --- |
| `PING` | `PONG MIMIX_ROBOT_V3` | Comprueba USB serial. |
| `STOP` | `OK STOP` | Detiene ambos motores. |
| `MOVE FORWARD 500` | `OK MOVE FORWARD` | Mueve en la direccion indicada. |
| `BASE` | `OK BASE` | Lleva los cinco servos a la posicion base. |
| `SERVO 3 375` | `OK SERVO 3 375` | Mueve un servo dentro de su rango calibrado. |

Las direcciones validas son `FORWARD`, `BACKWARD`, `LEFT` y `RIGHT`. La duracion
esta limitada a 3000 ms y al vencer se ejecuta una parada automatica. Una orden
invalida de traccion tambien detiene el robot. `STOP` no altera los servos.

## Carga y prueba

1. En el gestor de bibliotecas de Arduino IDE instala **Adafruit PWM Servo
   Driver Library** (instala tambien `Adafruit BusIO` cuando lo solicite).
2. Selecciona la placa ESP32-C3 correcta en Arduino IDE y carga el `.ino`.
3. Si Arduino IDE lo ofrece, activa **USB CDC On Boot**.
4. El monitor serial a 115200 debe mostrar `READY MIMIX_ROBOT_V3`; los motores
   deben quedar detenidos.
5. Cierra el monitor serial antes de iniciar la prueba ROS, porque ambos no
   pueden abrir el mismo puerto USB a la vez.

Las pruebas ROS de traccion y servos estan en
[`ros_ws/README.md`](../../ros_ws/README.md). Prueba primero los servos uno por
uno y siempre con espacio libre para su recorrido.
