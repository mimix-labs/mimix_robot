# speech_service

Guía de voz de Wall-E para Mimix. Se ejecuta directamente en la Jetson: toma
el audio del micrófono y parlante predeterminados, conversa con el agente de
ElevenLabs y llama a Mimix Web por `localhost` mediante herramientas locales.

## Alcance inicial

Hay tres funciones permitidas:

| Herramienta | Parámetros | Resultado |
| --- | --- | --- |
| `get_mimix_context` | ninguno | Consulta en qué zona o reto está Mimix Web. |
| `navigate_to` | `destination` = `world`, `mathematics` o `science` | Solicita abrir uno de esos destinos. |
| `get_dialogue` | `keyword` = frase completa del estudiante | Busca en `dialogues.json`; devuelve el texto exacto y, si aplica, un destino semántico. |

El LLM no recibe permisos para ejecutar URLs, JavaScript, terminal ni control
de motores. Mimix Web valida los destinos y el navegador realiza la navegación.

### Diálogos configurables (`dialogues.json`)

Los diálogos predefinidos se editan en `dialogues.json`. Cada entrada tiene:

```json
{
  "id": "demo_ciencias",
  "keywords": ["quiero aprender ciencias", "ciencias"],
  "destination": "science",
  "response": "¡Perfecto! Vamos al mundo de Ciencias y a la misión de Química de tu izquierda."
}
```

- **id**: identificador único (no se usa en runtime, solo para organizar)
- **keywords**: lista de frases que disparan este diálogo; la comparación ignora acentos y mayúsculas
- **destination**: opcional; solo `world`, `mathematics` o `science`
- **response**: texto exacto que dirá Wall-E

El agente llama a `get_dialogue` con la frase completa del estudiante. Si `found`
es `true` y aparece `destination`, primero navega al destino y recién entonces
repite `response` textualmente. Si `found` es `false`, usa su conversación libre.

## Configurar ElevenLabs

1. En el agente Wall-E, abre **Herramientas** y crea tres herramientas de tipo
   **Client** con los nombres exactos `get_mimix_context`, `navigate_to` y `get_dialogue`.
2. Activa **Wait for response** en todas.
3. `get_mimix_context` no lleva parámetros.
4. `navigate_to` lleva un parámetro obligatorio de texto: `destination`.
   Describe que acepta solamente `world`, `mathematics` o `science`.
5. `get_dialogue` lleva un parámetro obligatorio de texto: `keyword`.
   Describe que acepta la palabra clave del estudiante (ej. "preséntate", "matemáticas").
6. Deja activada la espera de respuesta para las tres herramientas y confirma
   que los nombres y parámetros coinciden exactamente con el código.

El prompt fuente está en `system_prompt.md`. Para publicarlo de forma repetible
en el agente configurado en `.env`, ejecuta desde la Jetson:

```bash
cd ~/mimix_robot
source services/speech_service/.venv/bin/activate
python services/speech_service/sync_elevenlabs_prompt.py --dry-run
python services/speech_service/sync_elevenlabs_prompt.py
```

El sincronizador obtiene la configuración actual, conserva sus IDs de
herramientas Client, actualiza el prompt y desactiva el evento de interrupción.
Así Wall-E termina cada diálogo antes de volver a escuchar al estudiante. La
clave de API nunca se copia en el navegador ni en Git.

## Arranque en Jetson

Primero instala las dependencias de audio del sistema:

```bash
sudo apt update
sudo apt install -y python3-venv portaudio19-dev libportaudio2 libportaudiocpp0 libasound2-dev libsndfile1-dev
```

Después crea el entorno del servicio:

```bash
cd ~/mimix_robot/services/speech_service
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

En `~/mimix_robot/.env`, que no se sube a Git, configura:

```bash
MIMIX_ELEVENLABS_AGENT_ID=agent_xxx
ELEVENLABS_API_KEY=tu_clave_privada
MIMIX_WEB_URL=http://127.0.0.1:4000
MIMIX_ROBOT_BRIDGE_TOKEN=un_secreto_local_largo
MIMIX_VOICE_GESTURE_URL=http://127.0.0.1:8092/talk
MIMIX_AUDIO_INPUT_SOURCE=alsa_input.usb-...
MIMIX_AUDIO_OUTPUT_SINK=bluez_output....
```

Si defines `MIMIX_ROBOT_BRIDGE_TOKEN`, coloca exactamente el mismo valor en
`~/mimix_web/server/.env`. Puedes partir de `server/.env.example`. Para el
primer piloto aislado puedes omitirlo en ambos proyectos, pero no en una red
compartida.

En la Jetson, usa los nombres exactos que muestran estos comandos para las dos
variables de audio:

```bash
pactl list short sources
pactl list short sinks
```

Luego inicia el servicio con un único comando. El lanzador carga `.env`,
selecciona los dispositivos configurados y arranca Wall-E. Si también tiene
`ELEVENLABS_API_KEY`, sincroniza antes la configuración sin interrupciones; si
la clave no está presente, la voz sigue iniciando normalmente:

```bash
cd ~/mimix_robot
bash services/speech_service/start_walle.sh
```

Para diagnóstico manual, también puedes cargar las variables e iniciarlo así:

```bash
cd ~/mimix_robot
set -a
source .env
set +a
cd services/speech_service
source .venv/bin/activate
python elevenlabs_service.py
```

Mimix Web debe estar ejecutándose en los puertos 4000 y 5173 antes de iniciar
la conversación. Para revisar que haya una pestaña de Mimix conectada:

```bash
curl http://127.0.0.1:4000/api/robot/status
```

## Gestos durante la respuesta

Cuando ElevenLabs comunica una respuesta de Wall-E, el servicio solicita un
gesto corto al puente ROS local. El puente debe estar iniciado mediante
`ros2 launch mimix_bringup robot.launch.py` y el robot debe estar armado. Si
ROS no está iniciado, la conversación de voz continúa sin gestos.

Para la demostración completa no hace falta abrir terminales separadas: usa
`bash deploy/jetson/start_mimix.sh --physical` desde la raíz de `mimix_robot`.
Ese lanzador inicia ROS antes de Wall-E y arma el robot solo si
`MIMIX_SERIAL_PORT` está configurado en `.env`.
