#!/bin/bash
# WhisperClip — Instalador para macOS
# Uso: curl -fsSL https://raw.githubusercontent.com/tanogalego/whisperclip/main/install.sh | bash

set -e

REPO="https://github.com/tanogalego/whisperclip.git"
INSTALL_DIR="$HOME/whisperclip"
APP_PATH="$INSTALL_DIR/WhisperClip.app"
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
    # Agregar brew al PATH para Apple Silicon
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

# ─── 8. Modelo Whisper ───────────────────────────────────────────────────────
echo "🎤 Descargando modelo Whisper 'base' (~140MB)..."
python -c "import whisper; whisper.load_model('base')" 2>/dev/null
echo "   Modelo descargado."

# ─── 9. Crear WhisperClip.app ────────────────────────────────────────────────
echo "🖥  Creando WhisperClip.app..."
mkdir -p "$APP_PATH/Contents/MacOS"
mkdir -p "$APP_PATH/Contents/Resources"

cat > "$APP_PATH/Contents/MacOS/WhisperClip" << APPEOF
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate
exec python whisperclip.py
APPEOF
chmod +x "$APP_PATH/Contents/MacOS/WhisperClip"

cat > "$APP_PATH/Contents/Info.plist" << PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleIdentifier</key>
    <string>com.whisperclip.app</string>
    <key>CFBundleName</key>
    <string>WhisperClip</string>
    <key>CFBundleDisplayName</key>
    <string>WhisperClip</string>
    <key>CFBundleExecutable</key>
    <string>WhisperClip</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>WhisperClip necesita el microfono para transcribir tu voz.</string>
</dict>
</plist>
PLISTEOF

# ─── 10. Configuración inicial ───────────────────────────────────────────────
CONFIG_DIR="$HOME/.whisperclip"
CONFIG_FILE="$CONFIG_DIR/config.json"
mkdir -p "$CONFIG_DIR"

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo ""
    echo "══════════════════════════════════════════"
    echo "  Configuración inicial"
    echo "══════════════════════════════════════════"
    echo ""
    echo "Para usar WhisperClip necesitás una API key de Anthropic (Claude)."
    echo "Obtené la tuya gratis en: https://console.anthropic.com/"
    echo "(Podés dejarla vacía por ahora y configurarla después)"
    echo ""
    read -p "🔑 Anthropic API Key: " API_KEY

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
  "anthropic_api_key": "$API_KEY",
  "max_record_seconds": 120,
  "silence_threshold": 0.01,
  "silence_duration": 2.0,
  "auto_stop_silence": false,
  "show_notifications": false,
  "sound_feedback": false
}
CONFIGEOF
    echo "   Configuración guardada en $CONFIG_FILE"
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
echo "  1. Micrófono         → agregar WhisperClip"
echo "  2. Accesibilidad     → agregar WhisperClip"
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
echo "  $APP_PATH/Contents/MacOS/WhisperClip &"
echo ""
echo "Shortcuts por defecto:"
echo "  ⌥ + /  →  Transcribir en español"
echo "  ⌥ + '  →  Transcribir y traducir al inglés"
echo ""
echo "Para cambiar shortcuts u otras opciones:"
echo "  $CONFIG_FILE"
echo ""
