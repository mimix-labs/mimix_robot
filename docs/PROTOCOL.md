# Protocolo inicial de eventos

## Principios

- MQTT transporta eventos; no define la lógica pedagógica.
- El navegador nunca usa las credenciales MQTT del robot.
- Los comandos son idempotentes y vencen.
- El robot confirma recepción y resultado.

## Convención de tópicos

Para el robot `robot-123` y versión `v1`:

```text
mimix/v1/robots/robot-123/commands     # Nube -> robot
mimix/v1/robots/robot-123/events       # Robot -> nube
mimix/v1/robots/robot-123/status       # Estado retenido del robot
```

## Sobre de mensaje

```json
{
  "message_id": "uuid",
  "schema_version": "v1",
  "session_id": "uuid",
  "type": "feedback.celebrate",
  "created_at": "2026-07-22T18:00:00Z",
  "expires_at": "2026-07-22T18:00:10Z",
  "payload": {
    "student_id": "opaque-id",
    "reason": "correct-answer"
  }
}
```

`student_id` debe ser opaco; no se publican nombres ni datos sensibles por el broker.

## Tipos iniciales

| Dirección | Tipo | Finalidad |
| --- | --- | --- |
| Nube -> robot | `session.start` | Carga una sesión autorizada y disponible offline. |
| Nube -> robot | `feedback.celebrate` | Solicita una celebración pedagógica. |
| Nube -> robot | `lesson.prompt` | Pide explicar o reforzar un concepto. |
| Robot -> nube | `command.accepted` | Reconocimiento de recepción. |
| Robot -> nube | `action.completed` | Resultado de voz o movimiento. |
| Robot -> nube | `session.event` | Acierto, intento o avance producido localmente. |
| Robot -> nube | `robot.fault` | Fallo no seguro o que requiere atención. |

## Acciones prohibidas en el protocolo externo

No se aceptan ángulos de servo, PWM, velocidad de motor, scripts arbitrarios ni rutas de archivos. Esos detalles pertenecen al protocolo interno entre `motion_service`, `arduino_bridge` y Arduino.
