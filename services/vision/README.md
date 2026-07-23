# vision_service

Procesa la camara en la Jetson y entrega a Mimix Web solamente landmarks de
manos. Esto elimina el conflicto entre MediaPipe WebGL y Three.js/ANGLE dentro
de Chromium: el navegador conserva su GPU para el mundo 3D y MediaPipe se
ejecuta como proceso nativo de CPU a 15 FPS.

## Arranque en la Jetson

En una terminal de la Jetson:

```bash
sudo apt update
sudo apt install -y python3-venv python3-opencv

cd ~/mimix_robot/services/vision
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python vision_service.py
```

`mediapipe==0.10.15` se fija intencionalmente: incluye un wheel para Python
3.12 y Linux ARM64, que corresponde a la Jetson con Ubuntu 24.04. No usar
Docker para esta primera prueba: el proceso debe acceder directamente a la
camara de la Jetson.

Antes de iniciar este servicio, levantar Mimix Web en dos terminales:

```bash
cd ~/mimix_web
npm run install:all
npm run server
```

```bash
cd ~/mimix_web
npm run client
```

Para entrar desde el mundo 3D de Mimix, abrir:

```text
http://localhost:5173/?vision=robot
```

Las zonas de MatemÃ¡ticas y Ciencias conservan automÃ¡ticamente `vision=robot`.
Si se necesita ir a un reto para depurar, tambiÃ©n se puede abrir directamente:

```text
http://localhost:5173/challenges/mathematics/index.html?vision=robot
http://localhost:5173/challenges/science/index.html?vision=robot
```

En este modo el navegador no solicita `getUserMedia`: recibe el video MJPEG
del mismo proceso nativo que detecta la mano. Los puntos cian se dibujan sobre
esa imagen y los gestos siguen llegando por el canal de landmarks.

El video se sirve solo dentro de la Jetson en `127.0.0.1:8081` y Mimix Web lo
reenvia por `/api/vision/video`; no expone un puerto adicional a la red.

Por defecto se transmite a 15 FPS con JPEG calidad 60 y la cÃ¡mara usa un
buffer de un frame para reducir latencia. Se puede bajar el uso de CPU con
`MIMIX_VIDEO_FPS=10` o mejorar la imagen con `MIMIX_VIDEO_JPEG_QUALITY=70`.

## Camara USB y CSI

Por defecto se abre `/dev/video0`. Para ver los dispositivos disponibles:

```bash
v4l2-ctl --list-devices
```

Para una USB en otro indice, por ejemplo `/dev/video2`:

```bash
export MIMIX_CAMERA_INDEX=2
python vision_service.py
```

Para una CSI, exportar un pipeline GStreamer antes de arrancar:

```bash
export MIMIX_CAMERA_PIPELINE='nvarguscamerasrc ! video/x-raw(memory:NVMM),width=640,height=480,framerate=30/1 ! nvvidconv ! video/x-raw,format=BGRx ! videoconvert ! video/x-raw,format=BGR ! appsink drop=true sync=false'
python vision_service.py
```

El estado del enlace se puede comprobar desde la Jetson:

```bash
curl http://localhost:4000/api/vision/status
```
