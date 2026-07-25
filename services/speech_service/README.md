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
| `get_dialogue` | `keyword` = palabra clave del estudiante | Busca en `dialogues.json` y devuelve el texto exacto del diálogo. |

El LLM no recibe permisos para ejecutar URLs, JavaScript, terminal ni control
de motores. Mimix Web valida los destinos y el navegador realiza la navegación.

### Diálogos configurables (`dialogues.json`)

Los diálogos predefinidos se editan en `dialogues.json`. Cada entrada tiene:

```json
{
  "id": "aprender_matematicas",
  "keywords": ["quiero aprender matemáticas", "matematicas"],
  "response": "¡Qué bien! Las matemáticas son increíbles..."
}
```

- **id**: identificador único (no se usa en runtime, solo para organizar)
- **keywords**: lista de frases que disparan este diálogo (sin acentos ni mayúsculas)
- **response**: texto exacto que dirá Wall-E

El agente debe llamar a `get_dialogue` con la palabra clave extraída del mensaje
del estudiante. Si `found` es `true`, debe repetir el texto de `response` textualmente.
Si `found` es `false`, debe responder con su comportamiento normal de conversación.

## Configurar ElevenLabs

1. En el agente Wall-E, abre **Herramientas** y crea tres herramientas de tipo
   **Client** con los nombres exactos `get_mimix_context`, `navigate_to` y `get_dialogue`.
2. Activa **Wait for response** en todas.
3. `get_mimix_context` no lleva parámetros.
4. `navigate_to` lleva un parámetro obligatorio de texto: `destination`.
   Describe que acepta solamente `world`, `mathematics` o `science`.
5. `get_dialogue` lleva un parámetro obligatorio de texto: `keyword`.
   Describe que acepta la palabra clave del estudiante (ej. "preséntate", "matemáticas").
6. Agrega al mensaje del sistema del agente:

```text
## HERRAMIENTAS DISPONIBLES

- get_mimix_context: consulta en qué zona o reto está el estudiante.
- navigate_to: navega a world, mathematics o science.
- get_dialogue: busca diálogos predefinidos por palabra clave. Recibe un parámetro "keyword".
  Si found=true, DEBES repetir el texto de "response" textualmente, sin modificarlo.
  Si found=false, responde con tu comportamiento normal.

Cuando el estudiante use frases como "preséntate", "quiero aprender matemáticas",
"misión sumar", etc., llama primero a get_dialogue. Si encuentra el diálogo,
repite el texto exacto. Si no lo encuentra, conversa normalmente.

Cuando el estudiante pida ir a Matemáticas, Ciencias o volver al mundo, usa
la herramienta navigate_to con el destino permitido. Espera su resultado antes
de confirmar que la navegación ocurrió.

SOLO responde si el mensaje contiene tu nombre "Wall-E" o "Wally".
Si no te llaman por tu nombre, quédate en silencio.
```

Publica el agente después de crear las herramientas. La clave de API nunca se
copia en el navegador ni en Git.

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
selecciona los dispositivos configurados y arranca Wall-E:

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
