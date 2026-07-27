# Progreso de Mimix Robot

Actualizado: 27 de julio de 2026.

## Estado actual

La Jetson puede iniciar Mimix Web, vision nativa y ROS fisico con un solo
comando. La sesion de voz de ElevenLabs se abre por separado para no consumir
minutos cuando el robot no esta en uso. La ESP32-C3 recibe ordenes validadas
por USB y el firmware no necesita recargarse para ajustar gestos.

## Entregas realizadas

- **Arranque en Jetson:** `deploy/jetson/start_mimix.sh --physical` inicia el
  backend y cliente Web, vision nativa, Chromium y ROS fisico. Detecta la
  ESP32-C3 por `/dev/serial/by-id` cuando no se definio el puerto.
- **Vision:** el supervisor de vision intenta las camaras disponibles y no
  bloquea el arranque de Web o ROS si una camara tarda en estar lista. Mimix
  Web recibe los frames nativos de la Jetson.
- **ROS y seguridad:** el puente USB acepta solo acciones semanticas, valida
  los limites de S1 a S5 y traduce a `SERVO`, `MOVE`, `STOP` y `BASE` para el
  firmware. El robot debe estar armado antes de moverse.
- **Dialogos de Wall-E:** los dialogos deterministas viven en
  `services/speech_service/dialogues.json`. El servicio local registra las
  herramientas de ElevenLabs y convierte sus respuestas en una solicitud de
  gesto ROS.
- **Gesto conversacional:**
  `voice_gesture_bridge_node.py` programa los cinco servos en cada cuadro,
  vuelve a la pose base al final y realiza pulsos cortos de ruedas adelante y
  atras durante respuestas largas.
- **Calibracion vigente:** S1 `180-320`, S2 `400-480`, S3 `180-600`, S4
  `150-300`, S5 `150-400`; la pose base es `180, 480, 400, 150, 400`.
- **Voz bajo demanda:** `deploy/jetson/start_voice.sh` exige que el puente ROS
  este sano y luego abre la conversacion. Si no hay clave API de ElevenLabs,
  la voz publica sigue funcionando; la sincronizacion remota queda omitida.

## Operacion de demostracion

```bash
cd ~/mimix_robot
bash deploy/jetson/start_mimix.sh --physical
```

En el momento de conversar:

```bash
cd ~/mimix_robot
bash deploy/jetson/start_voice.sh
```

Para detener la voz se usa `Ctrl+C` en la terminal de voz. Web, vision y ROS
pueden continuar activos.

## Pendientes y verificaciones fisicas

- S1 y S2 estan incluidos en todos los cuadros del gesto: ROS emite las
  acciones `servo_1` y `servo_2`, y el firmware las asigna a los canales 0 y
  1 del PCA9685. Si no responden a una orden ROS directa, revisar canal,
  cableado, alimentacion y tierra comun antes de modificar la animacion.
- En ElevenLabs debe desactivarse el evento **Interruption** para que el ruido
  o el audio del propio robot no corte una respuesta. El tiempo de espera y
  las reglas de silencio se configuran tambien en el agente remoto.
- Para sincronizar automaticamente el prompt y la configuracion remota desde
  la Jetson se necesita `ELEVENLABS_API_KEY` en `.env`; esa clave nunca se
  versiona.

## Archivos de referencia

- `ros_ws/src/mimix_runtime/mimix_runtime/voice_gesture_bridge_node.py`:
  secuencia de habla, servos y ruedas.
- `ros_ws/src/mimix_runtime/mimix_runtime/usb_serial_bridge_node.py`:
  validacion y protocolo USB.
- `firmware/esp32c3_motor_controller/esp32c3_motor_controller.ino`:
  firmware de ESP32-C3, PCA9685 y puente H.
- `services/speech_service/dialogues.json`: fuente de verdad de dialogos.
- `services/speech_service/README.md` y `ros_ws/README.md`: configuracion y
  pruebas manuales.
