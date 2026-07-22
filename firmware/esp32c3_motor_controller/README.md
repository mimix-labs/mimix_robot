# ESP32-C3 + TB6612FNG

Sketch Arduino para probar los dos motores DC del robot. Se abre directamente con Arduino IDE mediante `esp32c3_motor_controller.ino`.

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

Los motores se conectan a `A01/A02` y `B01/B02` del TB6612FNG.

## Pines que quedan libres

| Pines | Reserva |
| --- | --- |
| GPIO 8 / GPIO 9 | I2C: SDA / SCL. |
| GPIO 20 / GPIO 21 | UART: RX / TX para una futura comunicación con la Jetson. |
| GPIO 0 / GPIO 2 | Sin usar. GPIO 2 es un pin de arranque, por eso no se conecta al driver. |

El ESP32-C3 considera GPIO 2, 8 y 9 como pines de arranque; 8 y 9 quedan además reservados para I2C. [Documentación de Espressif](https://docs.espressif.com/projects/esp-idf/en/latest/esp32c3/api-reference/peripherals/gpio.html)

## Prueba automática

Al reiniciar, el sketch espera tres segundos y realiza una sola vez:

1. Adelante durante un segundo.
2. Quieto durante un segundo.
3. Atrás durante un segundo.
4. Quieto durante un segundo.
5. Izquierda durante un segundo.
6. Quieto durante un segundo.
7. Derecha durante un segundo y queda detenido.

Si adelante o atrás se invierten, intercambiar los dos cables del motor afectado en el TB6612FNG, o invertir los valores `HIGH`/`LOW` de ese motor en el sketch.

## Seguridad eléctrica

- La fuente de motores va a `VM`; no alimentar motores desde el pin 3V3 del ESP32.
- Usar 3V3 en `VCC` para que la lógica del TB6612FNG sea compatible con las señales de 3.3 V del ESP32.
- Unir GND de ESP32, TB6612FNG y la fuente de motores.
- Probar con las ruedas elevadas antes de colocar el robot en el suelo.
