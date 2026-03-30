# WhisperClip 🎙️

Dictá con tu voz → transcripción instantánea → se pega solo donde estás escribiendo.

Funciona en cualquier app: Slack, Gmail, Notion, Terminal, lo que sea.

**100% offline** con [Whisper](https://github.com/openai/whisper) de OpenAI. Opcionalmente usa Claude (Anthropic) para pulir el texto o traducirlo al inglés.

---

## Instalación

```bash
curl -fsSL https://raw.githubusercontent.com/tanogalego/whisperclip/main/install.sh | bash
```

El instalador se encarga de todo: Homebrew, Python, ffmpeg, dependencias, modelo Whisper y configuración inicial.

> **Requisitos:** macOS con Apple Silicon (M1/M2/M3/M4), conexión a internet para la instalación.

---

## Uso

| Shortcut | Acción |
|----------|--------|
| `⌥ + /` | Grabá → soltá → transcribe en español |
| `⌥ + '` | Grabá → soltá → transcribe y traduce al inglés |

Presionás el shortcut para empezar a grabar, volvés a presionarlo para parar. El texto se pega automáticamente donde tengas el cursor.

El ícono en la barra de menú muestra el estado: `mic` (idle) → `REC` (grabando) → `...` (procesando).

---

## Permisos de macOS

La primera vez necesitás dar permisos en **Configuración del Sistema → Privacidad y Seguridad**.
En cada sección, hacé click en `+` y seleccioná `~/whisperclip/dist/WhisperClip.app`:

| Permiso | Para qué se usa |
|---------|----------------|
| **Micrófono** | Capturar audio para transcribir |
| **Accesibilidad** | Detectar hotkeys globales |
| **Monitorización de entrada** | Interceptar eventos de teclado |

> **Importante:** agregá `WhisperClip.app` (no Python ni Terminal). La app debe estar construida (`make build`) antes de agregar los permisos.

---

## Inicio automático

Para que WhisperClip arranque solo al iniciar sesión:

**Preferencias del Sistema → General → Ítems de inicio de sesión → `+`** → seleccioná `~/whisperclip/dist/WhisperClip.app`

Para iniciarlo manualmente:
```bash
open ~/whisperclip/dist/WhisperClip.app
```

---

## Configuración

Editá `~/.whisperclip/config.json` para personalizar todo:

```json
{
  "hotkeys": [
    {
      "key": "<alt>+vk:44",
      "claude_mode": "transcription",
      "language": "es",
      "label": "ES"
    },
    {
      "key": "<alt>+vk:39",
      "claude_mode": "english",
      "language": "es",
      "label": "EN"
    }
  ],
  "whisper_model": "base",
  "claude_enabled": true,
  "anthropic_api_key": "tu-api-key-acá",
  "auto_stop_silence": false,
  "show_notifications": false,
  "sound_feedback": false
}
```

### Modelos Whisper

| Modelo | Tamaño | Velocidad | Precisión |
|--------|--------|-----------|-----------|
| `tiny` | 75 MB | rapido | basica |
| `base` | 140 MB | normal | buena (recomendado) |
| `small` | 460 MB | lento | muy buena |
| `medium` | 1.4 GB | muy lento | excelente |

### Modos de Claude

| Modo | Descripción |
|------|-------------|
| `transcription` | Corrige ortografía y puntuación |
| `formal` | Reescribe en tono profesional |
| `casual` | Tono relajado y natural |
| `email` | Formatea como email |
| `bullet` | Convierte a lista de puntos |
| `english` | Traduce al inglés |
| `none` | Sin procesamiento, transcripción directa |

### Detectar el código de una tecla

```bash
cd ~/whisperclip && source venv/bin/activate
python whisperclip.py detect-key
```

---

## API key de Anthropic

WhisperClip funciona sin API key (transcripción directa con Whisper). Para activar el pulido de texto con Claude:

1. Creá una cuenta en [console.anthropic.com](https://console.anthropic.com/)
2. Generá una API key
3. Configurala como variable de entorno (recomendado por seguridad):
   ```bash
   # Agregá esto a tu ~/.zshrc
   export ANTHROPIC_API_KEY='tu-api-key-acá'
   ```
4. O bien guardala directamente en `~/.whisperclip/config.json` en el campo `anthropic_api_key`

> La variable de entorno tiene prioridad sobre el archivo de config.

El costo es mínimo — Claude Haiku con uso moderado sale menos de $1/mes.

---

## Build desde el código fuente

```bash
cd ~/whisperclip
make build        # construye dist/WhisperClip.app
make install      # copia a ~/Applications/
```

O sin `make`:
```bash
source venv/bin/activate
python setup.py build_app
```

---

## Logs y troubleshooting

El log de la app está en `~/.whisperclip/whisperclip.log`.

Desde el menú de la app podés usar **"Ver log..."** para abrirlo, o **"Copiar log"** para copiar las últimas 50 líneas al portapapeles (útil para reportar bugs).

Problemas comunes:

| Síntoma | Causa probable | Solución |
|---------|---------------|---------|
| Hotkeys no responden | Falta permiso de Accesibilidad o Monitorización de entrada | Agregar en Preferencias del Sistema → Privacidad |
| No graba audio | Falta permiso de Micrófono | Agregar en Preferencias del Sistema → Privacidad |
| `ERR` en el ícono | Error de transcripción | Ver el log para detalles |
| Claude no procesa | API key inválida o sin conexión | Verificar `ANTHROPIC_API_KEY` o deshabilitar Claude |

---

## Costo comparado con Superwhisper

| | WhisperClip | Superwhisper Pro |
|--|-------------|-----------------|
| Transcripción | $0 (offline) | incluido |
| Post-procesamiento | ~$0.50/mes | incluido |
| **Total** | **~$0.50/mes** | **$8.49/mes** |

---

## Créditos

- [Whisper](https://github.com/openai/whisper) — OpenAI (MIT)
- [Anthropic Claude](https://www.anthropic.com/) — post-procesamiento
- [rumps](https://github.com/jaredks/rumps) — barra de menú macOS
- [pynput](https://github.com/moses-palmer/pynput) — hotkeys globales
- [sounddevice](https://python-sounddevice.readthedocs.io/) — captura de audio
