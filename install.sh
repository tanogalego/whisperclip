#!/bin/bash
# WhisperClip — Instalador para macOS
# Uso: curl -fsSL https://raw.githubusercontent.com/tanogalego/whisperclip/main/install.sh | bash

set -e

REPO="https://github.com/tanogalego/whisperclip.git"
INSTALL_DIR="$HOME/whisperclip"
APP_PATH="$INSTALL_DIR/dist/WhisperClip.app"
PLIST_PATH="$HOME/Library/LaunchAgents/com.whisperclip.plist"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║        WhisperClip — Instalador          ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ─── 1. Verificar macOS ───────────────────────────────────────────────────────
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ WhisperClip solo funciona en macOS."
    exit 1
fi

# ─── 2. Homebrew ─────────────────────────────────────────────────────────────
echo "📦 Verificando Homebrew..."
if ! command -v brew &>/dev/null; then
    echo "   Instalando Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    if [[ -f "/opt/homebrew/bin/brew" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
else
    echo "   Homebrew ya instalado."
fi

# ─── 3. Python ───────────────────────────────────────────────────────────────
echo "🐍 Verificando Python 3.11+..."
if ! brew list python@3.11 &>/dev/null; then
    echo "   Instalando Python 3.11..."
    brew install python@3.11
else
    echo "   Python ya instalado."
fi
PYTHON="$(brew --prefix)/bin/python3.11"

# ─── 4. ffmpeg ───────────────────────────────────────────────────────────────
echo "🎬 Verificando ffmpeg..."
if ! command -v ffmpeg &>/dev/null; then
    echo "   Instalando ffmpeg..."
    brew install ffmpeg
else
    echo "   ffmpeg ya instalado."
fi

# ─── 5. Clonar o actualizar el repo ──────────────────────────────────────────
echo "📥 Descargando WhisperClip..."
if [[ -d "$INSTALL_DIR/.git" ]]; then
    echo "   Actualizando instalación existente..."
    cd "$INSTALL_DIR"
    git pull
else
    git clone "$REPO" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# ─── 6. Entorno virtual ──────────────────────────────────────────────────────
echo "🔧 Configurando entorno Python..."
if [[ ! -d "$INSTALL_DIR/venv" ]]; then
    "$PYTHON" -m venv "$INSTALL_DIR/venv"
fi
source "$INSTALL_DIR/venv/bin/activate"

# ─── 7. Dependencias ─────────────────────────────────────────────────────────
echo "📚 Instalando dependencias (puede tardar unos minutos)..."
pip install --upgrade pip --quiet
pip install -r "$INSTALL_DIR/requirements.txt" --quiet
pip install -r "$INSTALL_DIR/requirements-dev.txt" --quiet

# ─── 8. Modelo Whisper ───────────────────────────────────────────────────────
echo "🎤 Descargando modelo Whisper 'base' (~140MB)..."
python -c "import whisper; whisper.load_model('base')" 2>/dev/null
echo "   Modelo descargado."

# ─── 9. Construir WhisperClip.app ────────────────────────────────────────────
echo "🖥  Construyendo WhisperClip.app..."
cd "$INSTALL_DIR"
python setup.py build_app
echo "   App construida en $APP_PATH"

# ─── 10. Configuración inicial ───────────────────────────────────────────────
CONFIG_DIR="$HOME/.whisperclip"
CONFIG_FILE="$CONFIG_DIR/config.json"
mkdir -p "$CONFIG_DIR"
chmod 700 "$CONFIG_DIR"

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo ""
    echo "══════════════════════════════════════════"
    echo "  Configuración inicial"
    echo "══════════════════════════════════════════"
    echo ""
    echo "Para usar el post-procesamiento con Claude necesitás una API key de Anthropic."
    echo "Obtené la tuya en: https://console.anthropic.com/"
    echo "(Podés dejarla vacía por ahora y configurarla después)"
    echo ""
    read -p "🔑 Anthropic API Key (Enter para omitir): " API_KEY

    # Guardar config sin la API key — usar variable de entorno es más seguro
    cat > "$CONFIG_FILE" << CONFIGEOF
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
  "sample_rate": 16000,
  "channels": 1,
  "claude_model": "claude-haiku-4-5-20251001",
  "claude_enabled": true,
  "anthropic_api_key": "",
  "max_record_seconds": 120,
  "silence_threshold": 0.01,
  "silence_duration": 2.0,
  "auto_stop_silence": false,
  "show_notifications": true,
  "sound_feedback": false
}
CONFIGEOF
    chmod 600 "$CONFIG_FILE"
    echo "   Configuración guardada en $CONFIG_FILE"

    if [[ -n "$API_KEY" ]]; then
        echo ""
        echo "   Para que la API key esté disponible al iniciar sesión, agregá esto a tu ~/.zshrc:"
        echo "   export ANTHROPIC_API_KEY='$API_KEY'"
        echo ""
        echo "   (La clave NO se guardó en config.json por seguridad)"
    fi
fi

# ─── 11. Inicio de sesión ─────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════"
echo "  Inicio automático"
echo "══════════════════════════════════════════"
echo ""
echo "Para que WhisperClip arranque automáticamente al iniciar sesión:"
echo ""
echo "  1. Abrí Preferencias del Sistema → General → Ítems de inicio de sesión"
echo "  2. Hacé click en '+'"
echo "  3. Navegá a: $APP_PATH"
echo "  4. Agregala"
echo ""

# ─── 12. Permisos ────────────────────────────────────────────────────────────
echo "══════════════════════════════════════════"
echo "  Permisos de macOS (IMPORTANTE)"
echo "══════════════════════════════════════════"
echo ""
echo "Necesitás dar estos permisos en Preferencias del Sistema → Privacidad:"
echo ""
echo "  1. Micrófono             → agregar WhisperClip"
echo "  2. Accesibilidad         → agregar WhisperClip"
echo "  3. Monitorización de entrada → agregar WhisperClip"
echo ""
echo "Ruta de la app: $APP_PATH"
echo ""

# ─── 13. Listo ───────────────────────────────────────────────────────────────
echo "╔══════════════════════════════════════════╗"
echo "║         ✅ Instalación completa          ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "Para iniciar WhisperClip ahora:"
echo "  open \"$APP_PATH\""
echo ""
echo "Shortcuts por defecto:"
echo "  ⌥ + /  →  Transcribir en español"
echo "  ⌥ + '  →  Transcribir y traducir al inglés"
echo ""
echo "Para cambiar shortcuts u otras opciones:"
echo "  $CONFIG_FILE"
echo ""
echo "Log de la app:"
echo "  $CONFIG_DIR/whisperclip.log"
echo ""
