# Arquitectura ROS 2 inicial

La Jetson Orin Nano ejecuta ROS 2 Jazzy como bus interno. ROS no se expone a
Internet y Mimix Web conserva la interfaz de estudiante, los retos 3D y el
backend HTTP existente.

```mermaid
flowchart LR
  Web[Mimix Web + backend] <-- HTTP --> WB[web_bridge]
  Source[MediaPipe u otra percepción] --> PA[perception_adapter]
  PA --> PE[/mimix/perception/event]
  Voice[Servicio de voz] --> BI[/mimix/behavior/intent]
  PE --> Behavior[behavior]
  BI --> Behavior
  Behavior -->|navegación| WB
  Behavior -->|solicitud simbólica| Safety[safety]
  Safety -->|solo armado| USB[usb_serial_bridge]
  USB -. protocolo futuro .-> ESP[ESP32-C3 por USB]
```

## Contratos

| Canal | Contenido | Responsabilidad |
| --- | --- | --- |
| `/mimix/perception/event` | `PerceptionEvent` | Un hallazgo genérico: fuente, modalidad, confianza y JSON. Ejemplos de modalidad: `hands`, `pose`, `face`, `object`. |
| `/mimix/behavior/intent` | `BehaviorIntent` | Una intención de alto nivel, como `open_mathematics` o `greet`. |
| `/mimix/web/command` | JSON | Solo navegación explícita hacia mundo, Matemáticas o Ciencias. |
| `/mimix/motion/request` | `MotionRequest` | Solicitud simbólica, nunca PWM ni posiciones físicas. |
| `/mimix/motion/approved` | `MotionRequest` | Salida después del filtro de seguridad. |
| `/mimix/robot/status` | `RobotStatus` | Diagnóstico de cada nodo. |

## Seguridad de la primera versión

- `safety` empieza desarmado.
- `usb_serial_bridge` inicia con `dry_run=true` y no abre ni escribe el puerto
  USB, aunque se le pase una ruta.
- Aún con `dry_run=false`, el nodo bloquea toda salida porque no existe un
  protocolo de firmware acordado. Esto evita que el firmware actual ejecute
  movimientos accidentales al conectar el ESP32.
- La futura ruta USB debe ser `/dev/serial/by-id/...`, no un nombre cambiante
  como `/dev/ttyACM0`.

## Decisiones deliberadamente diferidas

1. Convertir `vision_service.py` a un nodo ROS o conectar un adaptador HTTP.
   El contrato genérico ya permite ambas cosas sin limitarse a manos.
2. Integrar el servicio de voz como productor de `BehaviorIntent`.
3. Especificar, implementar y probar el protocolo serial con el ESP32-C3.
4. Incorporar sensores, estados de movimiento y acciones reales.

No hace falta un backend adicional para esta etapa: el backend de Mimix Web ya
ofrece contexto y comandos del robot, y `web_bridge` los reutiliza.
