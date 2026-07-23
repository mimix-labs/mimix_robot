# speech_service

Guía de voz de Wall-E para Mimix. Se ejecuta directamente en la Jetson: toma
el audio del micrófono y parlante predeterminados, conversa con el agente de
ElevenLabs y llama a Mimix Web por `localhost` mediante herramientas locales.

## Alcance inicial

Solo hay dos funciones permitidas:

| Herramienta | Parámetros | Resultado |
| --- | --- | --- |
| `get_mimix_context` | ninguno | Consulta en qué zona o reto está Mimix Web. |
| `navigate_to` | `destination` = `world`, `mathematics` o `science` | Solicita abrir uno de esos destinos. |

El LLM no recibe permisos para ejecutar URLs, JavaScript, terminal ni control
de motores. Mimix Web valida los destinos y el navegador realiza la navegación.

## Configurar ElevenLabs

1. En el agente Wall-E, abre **Herramientas** y crea dos herramientas de tipo
   **Client** con los nombres exactos `get_mimix_context` y `navigate_to`.
2. Activa **Wait for response** en ambas.
3. `get_mimix_context` no lleva parámetros.
4. `navigate_to` lleva un parámetro obligatorio de texto: `destination`.
   Describe que acepta solamente `world`, `mathematics` o `science`.
5. Agrega al mensaje del sistema del agente:

```text
Cuando el estudiante pida ir a Matemáticas, Ciencias o volver al mundo, usa
la herramienta navigate_to con el destino permitido. Espera su resultado antes
de confirmar que la navegación ocurrió. Cuando necesites saber dónde está el
estudiante o qué objeto eligió, usa get_mimix_context.
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
