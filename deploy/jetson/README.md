# Despliegue en Jetson (pendiente de validación física)

Este directorio todavía no contiene una imagen de producción. Antes de crearla se debe registrar:

1. Modelo exacto de Jetson Nano, versión de JetPack y arquitectura.
2. Adaptador Wi-Fi y soporte comprobado para modo cliente y punto de acceso.
3. Dispositivos seriales del Arduino y regla estable de `udev`.
4. Cámara, audio, alimentación y comportamiento ante corte de energía.
5. Distribución ROS 2 compatible, si se decide usarla.

La futura configuración de contenedores tendrá que mapear dispositivos requeridos, por ejemplo el puerto serial. Nunca se usará `privileged: true` como sustituto de permisos definidos.
