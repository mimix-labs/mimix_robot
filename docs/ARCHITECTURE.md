# Arquitectura de Mimix Robot

## Propósito

`mimix_robot` es un runtime de borde: continúa la experiencia de aprendizaje aunque Internet sea inestable y protege el hardware frente a órdenes inválidas. No reemplaza a Mimix Web ni aloja su interfaz principal.

## Frontera entre los sistemas

| Sistema | Responsabilidad |
| --- | --- |
| Mimix Web | Interfaz del estudiante, cámara/MediaPipe en el dispositivo del estudiante, actividades 3D y progreso. |
| Backend Mimix | Usuarios, sesiones, autorización, historial y puente con el broker. |
| Broker MQTT | Entrega autenticada de eventos entre nube y robot. |
| Mimix Robot | Interpretación pedagógica local, voz, estado, persistencia offline y ejecución física segura. |
| Arduino | Control de bajo nivel, límites de actuadores y parada segura. |

No se enviará vídeo de la cámara por MQTT. La plataforma actual puede ejecutar MediaPipe en el navegador del estudiante. Si se necesita vídeo de la cámara del robot, se evaluará WebRTC como proyecto separado.

## Redes Wi-Fi

### Modo cliente: predeterminado

La Jetson se asocia al Wi-Fi de la institución y abre una conexión saliente TLS al broker. Los tablets o computadoras acceden a la plataforma web hospedada normalmente. No requiere abrir puertos entrantes en la Jetson.

### Modo punto de acceso: contingencia

La Jetson publica un SSID, por ejemplo `Mimix-Robot-XXXX`. Los dispositivos se conectan a esa red y abren una página local, por ejemplo `http://mimix.local`. Esa página debe ser una versión local o caché; no puede depender de que el sitio público cargue desde Internet.

El punto de acceso es una capacidad de continuidad, no un reemplazo de la red escolar. Hay que probar que el adaptador Wi-Fi soporte el modo requerido y las restricciones de la Jetson.

## Flujo de interacción

1. Mimix Web registra una acción educativa, por ejemplo un acierto.
2. El backend autoriza la sesión y publica una intención como `feedback.celebrate`.
3. `robot_gateway` valida el mensaje y lo entrega a `learning_agent`.
4. `learning_agent` decide una respuesta según el contexto local.
5. `speech_service` sintetiza la frase y `motion_service` solicita una acción semántica.
6. `arduino_bridge` envía un comando serial acotado; Arduino lo confirma o rechaza.
7. El robot publica el resultado y lo guarda localmente si no hay red.

## ROS 2: decisión condicionada

ROS 2 es una buena capa interna si existen varios nodos de hardware y percepción: movimiento, sensores, voz, visión y comportamiento. No debe exponer sus tópicos directamente a Internet.

La Jetson Nano está limitada por su JetPack oficial, basado en una generación antigua de Ubuntu. Las versiones actuales de ROS 2 requieren sistemas más recientes para tener soporte binario pleno. La distribución ROS se decidirá después de una prueba física. [Soporte de ROS 2 Humble](https://docs.ros.org/en/humble/Releases/Release-Humble-Hawksbill.html) y [compatibilidad de Jetson Nano](https://forums.developer.nvidia.com/t/jetson-nano-ubuntu-version/319330).

Mientras tanto, las fronteras se diseñan como nodos ROS 2. Así se puede iniciar con procesos Python ligeros y migrar adaptadores de hardware a ROS 2 sin cambiar el protocolo externo.

## Despliegue

| Entorno | Forma de ejecución |
| --- | --- |
| PC de desarrollo | Docker Compose: broker MQTT y simuladores. |
| Jetson Nano | Contenedores ARM64 compatibles con su JetPack/L4T, con acceso explícito a serial. |
| Hardware crítico | Arduino independiente; un fallo de Docker o Jetson debe resultar en parada segura. |

No se considera válida una prueba de cámara, GPU, Wi-Fi AP, audio o serial hasta realizarla en la Jetson real.
