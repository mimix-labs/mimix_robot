# Despliegue en Jetson

## Arranque de demostración física

Con `mimix_web` y `mimix_robot` instalados como directorios hermanos, el
iniciador detecta automáticamente una única ESP32-C3 Espressif conectada. Si
hay varias C3 o se quiere fijar un puerto, configurarlo en
`~/mimix_robot/.env`:

```bash
MIMIX_SERIAL_PORT=/dev/serial/by-id/REEMPLAZAR_POR_EL_ESP32
```

El primer comando prepara Web, visión, Chromium, ROS y gestos físicos, sin
abrir una sesión de ElevenLabs:

```bash
cd ~/mimix_robot
bash deploy/jetson/start_mimix.sh --physical
```

`--physical` reconstruye ROS, inicia el puente de gestos, conecta el ESP32 con
`dry_run=false` y arma la seguridad. Si falta el puerto serial o el puerto
local `8092` ya está ocupado, el lanzador se detiene sin mover el robot y
explica cómo corregirlo. No carga firmware.

Cuando vaya a empezar la conversación, abrir la voz en otra terminal:

```bash
cd ~/mimix_robot
bash deploy/jetson/start_voice.sh
```

Este segundo comando es el único que abre una sesión de ElevenLabs y consume
la cuota del agente. Al terminar, detenerlo con `Ctrl+C`; Web, cámara y ROS
siguen activos.

La visión se inicia en segundo plano, pero no bloquea ROS ni la Web.
Si la cámara no publica frames, Chromium abre `http://127.0.0.1:5173/` en modo
normal y el problema queda registrado en `logs/jetson/vision.log`.

`--ros` inicia ROS en simulación segura y desarmada. `--voice` inicia voz junto
con el stack, pero para una demostración física se recomienda `start_voice.sh`.
Usa `--no-browser` al ejecutarlo por SSH o para diagnóstico remoto, y
`--skip-ros-build` en reinicios posteriores cuando el workspace no cambió. Los
registros quedan en `~/mimix_robot/logs/jetson/`; `Ctrl+C` detiene todos los
procesos que inició el lanzador.

El navegador de la Jetson abre con `?vision=robot`. Un navegador normal usa
su propia cámara cuando el backend no informa frames nativos; puede forzarse
con `?vision=browser` durante pruebas.

La exposición a Internet no forma parte de este lanzador: Vite queda visible
en la red local de la Jetson. El despliegue público de Mimix Web debe hacerse
por separado con un dominio, HTTPS y un servidor de producción.

---

Este directorio todavía no contiene una imagen de producción. Antes de crearla se debe registrar:

1. Modelo exacto de Jetson Nano, versión de JetPack y arquitectura.
2. Adaptador Wi-Fi y soporte comprobado para modo cliente y punto de acceso.
3. Dispositivos seriales del Arduino y regla estable de `udev`.
4. Cámara, audio, alimentación y comportamiento ante corte de energía.
5. Distribución ROS 2 compatible, si se decide usarla.

La futura configuración de contenedores tendrá que mapear dispositivos requeridos, por ejemplo el puerto serial. Nunca se usará `privileged: true` como sustituto de permisos definidos.
