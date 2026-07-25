# Despliegue en Jetson

## Arranque de demostración física

Con `mimix_web` y `mimix_robot` instalados como directorios hermanos, configura
una única vez el puerto estable del ESP32 en `~/mimix_robot/.env`:

```bash
MIMIX_SERIAL_PORT=/dev/serial/by-id/REEMPLAZAR_POR_EL_ESP32
```

Después, el arranque completo —Web, visión, Chromium, ROS, voz y gestos— usa
una sola terminal y un solo comando:

```bash
cd ~/mimix_robot
bash deploy/jetson/start_mimix.sh --physical
```

`--physical` reconstruye ROS, inicia el puente de gestos, conecta el ESP32 con
`dry_run=false`, arma la seguridad y recién después inicia Wall-E. Si falta el
puerto serial o el puerto local `8092` ya está ocupado, el lanzador se detiene
sin mover el robot y explica cómo corregirlo. No carga firmware.

`--ros` inicia ROS en simulación segura y desarmada. `--voice` inicia solo la
voz. Usa `--no-browser` al ejecutarlo por SSH o para diagnóstico remoto, y
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
