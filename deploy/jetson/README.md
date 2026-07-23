# Despliegue en Jetson

## Arranque de demostración

Con `mimix_web` y `mimix_robot` instalados como directorios hermanos, usa:

```bash
cd ~/mimix_robot
bash deploy/jetson/start_mimix.sh --voice
```

El lanzador inicia el backend Web, el cliente Vite accesible por la red local,
la visión nativa y Chromium con su perfil aislado y las opciones GPU requeridas.
`--voice` agrega el servicio Wall-E; sin esa opción la voz queda detenida.
Usa `--no-browser` al ejecutarlo por SSH o para diagnóstico remoto. Los
registros quedan en `~/mimix_robot/logs/jetson/` y `Ctrl+C` detiene los
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
