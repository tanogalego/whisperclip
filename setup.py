"""
setup.py — Construye WhisperClip.app como bundle nativo de macOS.

El bundle usa un launcher compilado en Swift (binario Mach-O real) que lanza
whisperclip.py via el venv. Un binario real es necesario para que macOS TCC
otorgue correctamente los permisos de Micrófono, Accesibilidad e Input Monitoring.

Uso:
    python setup.py build_app
"""
import re
import subprocess
import sys
from pathlib import Path

# Leer version sin importar el modulo completo
with open("version.py") as f:
    version = re.search(r'__version__\s*=\s*"(.+?)"', f.read()).group(1)

INSTALL_DIR = Path(__file__).resolve().parent
APP_DIR     = INSTALL_DIR / "dist" / "WhisperClip.app"
MACOS_DIR   = APP_DIR / "Contents" / "MacOS"
RESOURCES_DIR = APP_DIR / "Contents" / "Resources"

PLIST = f"""<?xml version="1.0" encoding="UTF-8"?>
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
    <string>{version}</string>
    <key>CFBundleShortVersionString</key>
    <string>{version}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>WhisperClip necesita el microfono para transcribir tu voz.</string>
    <key>NSAppleEventsUsageDescription</key>
    <string>WhisperClip usa AppleEvents para pegar texto.</string>
    <key>NSAccessibilityUsageDescription</key>
    <string>WhisperClip necesita Accesibilidad para detectar hotkeys y pegar texto.</string>
</dict>
</plist>"""


def build_app():
    print(f"Building WhisperClip.app v{version}...")

    MACOS_DIR.mkdir(parents=True, exist_ok=True)
    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)

    # Compilar launcher Swift -> binario Mach-O real (necesario para permisos TCC)
    launcher_bin = MACOS_DIR / "WhisperClip"
    print("  Compilando launcher Swift...")
    result = subprocess.run(
        ["swiftc", str(INSTALL_DIR / "Launcher.swift"), "-o", str(launcher_bin)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Error compilando Launcher.swift:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Info.plist
    (APP_DIR / "Contents" / "Info.plist").write_text(PLIST)

    print(f"  -> {APP_DIR}")
    print("Done.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "build_app":
        build_app()
    else:
        print(__doc__)
