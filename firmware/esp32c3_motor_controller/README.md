# ESP32-C3 motor controller

Firmware para el ESP32-C3 SuperMini que controlará el driver TB6612FNG y los dos motores DC del robot.

## Abrir en Arduino IDE

1. Abrir `esp32c3_motor_controller.ino` desde esta carpeta.
2. Instalar el paquete de placas ESP32 de Espressif si aún no está instalado.
3. Elegir la placa ESP32-C3 que corresponda al SuperMini y el puerto USB correcto.
4. Por seguridad, conservar `MOTOR_OUTPUTS_ENABLED` en `false` hasta validar el cableado.

## Contrato inicial con la Jetson

El futuro servicio `services/arduino_bridge` se conectará por USB serial a 115200 baudios.

| Jetson -> ESP32 | Respuesta | Propósito |
| --- | --- | --- |
| `PING` | `PONG mimix-esp32c3` | Verificar enlace. |
| `HEARTBEAT` | `ACK HEARTBEAT` | Mantener habilitado el controlador. |
| `STOP` | `ACK STOP` | Detener inmediatamente los motores. |

El firmware no acepta todavía comandos de movimiento. Antes de agregarlos hay que definir los GPIO reales, alimentación de motores, tierra común, sentido de cada motor, velocidad máxima y comportamiento ante fallo.

## Seguridad eléctrica mínima

- Alimentar los motores desde una fuente independiente y apropiada para ellos.
- Unir la tierra de la fuente de motores, TB6612FNG, ESP32 y Jetson.
- Mantener el pin `STBY` del TB6612FNG en estado seguro durante el arranque.
- Probar con las ruedas elevadas antes de poner el robot en el suelo.
