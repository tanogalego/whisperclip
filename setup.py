"""
setup.py para construir WhisperClip.app con py2app
Uso: python setup.py py2app
"""
from setuptools import setup
import re

# Leer version sin importar el modulo completo (evita side-effects)
with open("version.py") as f:
    version = re.search(r'__version__\s*=\s*"(.+?)"', f.read()).group(1)

APP = ["whisperclip.py"]

OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "WhisperClip",
        "CFBundleDisplayName": "WhisperClip",
        "CFBundleIdentifier": "com.whisperclip.app",
        "CFBundleVersion": version,
        "CFBundleShortVersionString": version,
        "LSUIElement": True,
        "NSMicrophoneUsageDescription":
            "WhisperClip necesita el microfono para transcribir tu voz.",
        "NSAppleEventsUsageDescription":
            "WhisperClip usa AppleEvents para pegar texto.",
        "NSAccessibilityUsageDescription":
            "WhisperClip necesita Accesibilidad para detectar hotkeys y pegar texto.",
    },
    "packages": [
        "whisper",
        "anthropic",
        "sounddevice",
        "numpy",
        "scipy",
        "pynput",
        "pyperclip",
        "rumps",
    ],
    "excludes": ["tkinter", "test", "unittest"],
    "semi_standalone": False,
    "site_packages": True,
}

setup(
    app=APP,
    name="WhisperClip",
    version=version,
    data_files=[],
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
