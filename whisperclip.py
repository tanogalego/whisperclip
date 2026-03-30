#!/usr/bin/env python3
"""
WhisperClip — Voice to text para macOS
Icono en barra de menu + hotkeys globales + Whisper offline + Claude
"""

import os
import sys
import time
import threading
import tempfile
import subprocess
import json
import re
from pathlib import Path
from datetime import datetime

# ─── Dependencias ───────────────────────────────────────────────────────────
try:
    import sounddevice as sd
    import numpy as np
    import whisper
    import anthropic
    from pynput import keyboard
    import pyperclip
    import rumps
except ImportError as e:
    missing = str(e).split("'")[1] if "'" in str(e) else str(e)
    print(f"Falta dependencia: {missing}")
    if missing == "rumps":
        print("Corre: pip install rumps")
    else:
        print("Corre: pip install sounddevice numpy openai-whisper anthropic pynput pyperclip rumps")
    sys.exit(1)

CONFIG_PATH = Path.home() / ".whisperclip" / "config.json"

DEFAULT_CONFIG = {
    "hotkeys": [
        {"key": "vk:44", "claude_mode": "transcription", "language": "es", "label": "ES"},
        {"key": "vk:39", "claude_mode": "english",       "language": "es", "label": "EN"},
    ],
    "whisper_model":      "base",
    "sample_rate":        16000,
    "channels":           1,
    "claude_model":       "claude-haiku-4-5-20251001",
    "claude_enabled":     True,
    "anthropic_api_key":  "",
    "max_record_seconds": 120,
    "silence_threshold":  0.01,
    "silence_duration":   2.0,
    "auto_stop_silence":  False,
    "show_notifications": True,
    "sound_feedback":     False,
}

CLAUDE_MODES = {
    "transcription": {
        "name":   "Transcripcion limpia",
        "prompt": "Corregi ortografia, puntuacion y gramatica del siguiente texto transcripto de voz. Mantenes el mismo idioma y tono. Solo devuelve el texto corregido, sin explicaciones.",
    },
    "formal": {
        "name":   "Formal / Profesional",
        "prompt": "Reescribi el siguiente texto en un tono formal y profesional, corrigiendo errores. Mantenes el idioma original. Solo devuelve el texto, sin explicaciones.",
    },
    "casual": {
        "name":   "Casual / Relajado",
        "prompt": "Reescribi el siguiente texto en un tono casual y natural, como se habla normalmente. Mantenes el idioma original. Solo devuelve el texto, sin explicaciones.",
    },
    "email": {
        "name":   "Email",
        "prompt": "Converti el siguiente texto en un email bien estructurado con asunto, saludo, cuerpo y cierre. Mantene el idioma original. Solo devuelve el email, sin explicaciones.",
    },
    "bullet": {
        "name":   "Lista de puntos",
        "prompt": "Converti el siguiente texto en una lista de puntos clara y concisa. Mantene el idioma original. Solo devuelve la lista, sin explicaciones.",
    },
    "english": {
        "name":   "Traducir al ingles",
        "prompt": "Traduce el siguiente texto al ingles, manteniendo el tono y la intencion original. Solo devuelve la traduccion, sin explicaciones.",
    },
    "none": {
        "name":   "Sin procesamiento",
        "prompt": None,
    },
}

ICON_IDLE       = "mic"
ICON_RECORDING  = "rec"
ICON_PROCESSING = "..."
ICON_ERROR      = "err"


def notify(title, message):
    try:
        subprocess.run(
            ["osascript", "-e", f'display notification "{message}" with title "{title}"'],
            capture_output=True
        )
    except Exception:
        pass


def paste_text(text):
    pyperclip.copy(text)
    time.sleep(0.15)
    kb = keyboard.Controller()
    with kb.pressed(keyboard.Key.cmd):
        kb.tap("v")


def load_config():
    config = DEFAULT_CONFIG.copy()
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                saved = json.load(f)
            config.update(saved)
        except Exception as e:
            print(f"Warning: {e}")
    return config


def save_config(config):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


class AudioRecorder:
    def __init__(self, config):
        self.config = config
        self.frames = []
        self.recording = False
        self._lock = threading.Lock()
        self._silence_counter = 0

    def _audio_callback(self, indata, frames, time_info, status):
        if self.recording:
            with self._lock:
                self.frames.append(indata.copy())
            if self.config.get("auto_stop_silence"):
                volume = np.abs(indata).mean()
                if volume < self.config.get("silence_threshold", 0.01):
                    self._silence_counter += frames
                else:
                    self._silence_counter = 0

    def start(self):
        self.frames = []
        self._silence_counter = 0
        self.recording = True
        sr = self.config.get("sample_rate", 16000)
        ch = self.config.get("channels", 1)
        self._stream = sd.InputStream(
            samplerate=sr, channels=ch,
            callback=self._audio_callback,
            blocksize=1024, dtype="float32",
        )
        self._stream.start()

    def stop(self):
        self.recording = False
        if hasattr(self, "_stream"):
            self._stream.stop()
            self._stream.close()
        with self._lock:
            if not self.frames:
                return None
            return np.concatenate(self.frames, axis=0)

    def should_auto_stop(self):
        sr = self.config.get("sample_rate", 16000)
        return self._silence_counter > (sr * self.config.get("silence_duration", 2.0))


class Transcriber:
    def __init__(self, config):
        self.config = config
        model_name = config["whisper_model"]
        print(f"Cargando Whisper '{model_name}'...")
        self._model = whisper.load_model(model_name)
        print(f"Whisper '{model_name}' listo.")

    def transcribe(self, audio, language=None):
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        audio = audio.astype(np.float32)
        lang = language or self.config.get("language")
        options = {"language": lang} if lang else {}
        import scipy.io.wavfile as wavfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
        wavfile.write(tmp_path, self.config.get("sample_rate", 16000), audio)
        try:
            result = self._model.transcribe(tmp_path, **options)
            return result["text"].strip()
        finally:
            os.unlink(tmp_path)


class ClaudeProcessor:
    def __init__(self, config):
        self.config = config
        api_key = config.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY", "")
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None
        if not self.client:
            print("Sin API key de Anthropic — post-procesamiento desactivado.")

    def process(self, text, mode_key="transcription"):
        if not self.client or not self.config.get("claude_enabled", True):
            return text
        mode = CLAUDE_MODES.get(mode_key, CLAUDE_MODES["transcription"])
        if not mode["prompt"]:
            return text
        try:
            msg = self.client.messages.create(
                model=self.config.get("claude_model", "claude-haiku-4-5-20251001"),
                max_tokens=1024,
                messages=[{"role": "user", "content": f"{mode['prompt']}\n\nTexto:\n{text}"}]
            )
            return msg.content[0].text.strip()
        except Exception as e:
            print(f"Error Claude: {e}")
            return text


class WhisperClipMenuApp(rumps.App):

    def __init__(self, config):
        super().__init__("WhisperClip", title=ICON_IDLE, quit_button=None)
        self.config = config
        self.recorder = AudioRecorder(config)
        self.transcriber = Transcriber(config)
        self.processor = ClaudeProcessor(config)
        self.is_recording = False
        self.is_paused = False
        self._active_hk = None
        self._last_trigger = {}
        self._build_menu()
        self._start_keyboard_listener()

    def _build_menu(self):
        hotkeys_cfg = self.config.get("hotkeys", [])
        shortcut_items = []
        for hk in hotkeys_cfg:
            mode_name = CLAUDE_MODES.get(hk.get("claude_mode", ""), {}).get("name", "?")
            item = rumps.MenuItem(f"  [{hk['label']}]  {hk['key']}  ->  {mode_name}")
            shortcut_items.append(item)

        self.pause_item = rumps.MenuItem("Pausar", callback=self.toggle_pause)
        self.menu = (
            [rumps.MenuItem("WhisperClip")] +
            [rumps.separator] +
            shortcut_items +
            [rumps.separator,
             self.pause_item,
             rumps.MenuItem("Ver log...", callback=self.open_log),
             rumps.MenuItem("Editar configuracion...", callback=self.open_config),
             rumps.separator,
             rumps.MenuItem("Cerrar WhisperClip", callback=self.quit_app)]
        )

    def set_state(self, state, label=""):
        icons = {
            "idle":       "mic",
            "recording":  "REC",
            "processing": "...",
            "error":      "ERR",
        }
        suffix = f" {label}" if label else ""
        self.title = icons.get(state, "mic") + suffix

    def toggle_pause(self, _):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_item.title = "Reanudar"
            self.title = "| |"
        else:
            self.pause_item.title = "Pausar"
            self.set_state("idle")

    def quit_app(self, _):
        rumps.quit_application()

    def open_log(self, _):
        subprocess.run(["open", "-a", "Console", "/tmp/whisperclip.log"], capture_output=True)
        subprocess.run(["open", "/tmp/whisperclip.log"], capture_output=True)

    def open_config(self, _):
        subprocess.run(["open", str(CONFIG_PATH)])

    def _start_keyboard_listener(self):
        hotkeys_cfg = self.config.get("hotkeys", [])
        # Parsear hotkeys: formato "vk:44" o "<alt>+vk:44"
        # "<alt>+vk:44" significa: Option presionado + tecla con vk 44
        parsed = []
        for hk in hotkeys_cfg:
            key_str = hk["key"]
            requires_alt = "<alt>" in key_str
            m = re.search(r"vk:(\d+)", key_str)
            if m:
                parsed.append((int(m.group(1)), requires_alt, hk))
                continue
            m2 = re.search(r"<(\d+)>", key_str)
            if m2:
                parsed.append((int(m2.group(1)), requires_alt, hk))

        self._parsed_hotkeys = parsed
        self._kb_ctrl = keyboard.Controller()
        self._alt_pressed = False

        def on_press(key):
            # Trackear Option
            if key in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r):
                self._alt_pressed = True
                return

            if self.is_paused:
                return

            vk = getattr(key, "vk", None)
            if vk is None:
                return

            for (keycode, requires_alt, hk_cfg) in self._parsed_hotkeys:
                if vk == keycode and self._alt_pressed == requires_alt:
                    label = hk_cfg.get("label", "")
                    now = time.time()
                    if now - self._last_trigger.get(label, 0) < 0.3:
                        return
                    self._last_trigger[label] = now
                    def trigger(hk=hk_cfg):
                        time.sleep(0.05)
                        self._kb_ctrl.tap(keyboard.Key.backspace)
                        self._toggle(hk)
                    threading.Thread(target=trigger, daemon=True).start()
                    return

        def on_release(key):
            if key in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r):
                self._alt_pressed = False

        self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self._listener.daemon = True
        self._listener.start()

    def _toggle(self, hk_cfg):
        if not self.is_recording:
            self._start_recording(hk_cfg)
        else:
            self._stop_and_process()

    def _start_recording(self, hk_cfg):
        self.is_recording = True
        self._active_hk = hk_cfg
        self.recorder.start()
        label = hk_cfg.get("label", "")
        self.set_state("recording", label)
        if self.config.get("show_notifications"):
            mode_name = CLAUDE_MODES.get(hk_cfg.get("claude_mode", ""), {}).get("name", "")
            threading.Thread(
                target=notify,
                args=(f"WhisperClip [{label}]", f"Grabando..."),
                daemon=True
            ).start()
        if self.config.get("auto_stop_silence"):
            def watch():
                time.sleep(2.0)
                while self.is_recording:
                    if self.recorder.should_auto_stop():
                        self._stop_and_process()
                        break
                    time.sleep(0.1)
            threading.Thread(target=watch, daemon=True).start()
        max_sec = self.config.get("max_record_seconds", 120)
        threading.Timer(max_sec, self._stop_and_process).start()

    def _stop_and_process(self):
        if not self.is_recording:
            return
        self.is_recording = False
        self.set_state("processing")
        hk_cfg = self._active_hk
        threading.Thread(target=self._process_audio, args=(hk_cfg,), daemon=True).start()

    def _process_audio(self, hk_cfg):
        audio = self.recorder.stop()
        if audio is None or len(audio) < 1000:
            self.set_state("idle")
            return
        lang        = hk_cfg.get("language") or self.config.get("language", "es")
        claude_mode = hk_cfg.get("claude_mode", "transcription")
        label       = hk_cfg.get("label", "")
        try:
            raw_text = self.transcriber.transcribe(audio, language=lang)
        except Exception as e:
            print(f"Error transcribiendo: {e}")
            self.set_state("error")
            time.sleep(2)
            self.set_state("idle")
            return
        if not raw_text:
            self.set_state("idle")
            return
        if self.config.get("claude_enabled") and claude_mode != "none":
            try:
                final_text = self.processor.process(raw_text, mode_key=claude_mode)
            except Exception:
                final_text = raw_text
        else:
            final_text = raw_text
        try:
            paste_text(final_text)
        except Exception:
            pyperclip.copy(final_text)
        self.set_state("idle")
        if self.config.get("show_notifications"):
            preview = final_text[:60] + ("..." if len(final_text) > 60 else "")
            notify(f"WhisperClip [{label}]", preview)


def install_launchd():
    venv_python = sys.executable
    script_path = Path(__file__).resolve()
    plist_path  = Path.home() / "Library/LaunchAgents/com.whisperclip.plist"
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.whisperclip</string>
    <key>ProgramArguments</key>
    <array>
        <string>{venv_python}</string>
        <string>{script_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>/tmp/whisperclip.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/whisperclip.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin')}</string>
    </dict>
</dict>
</plist>"""
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    plist_path.write_text(plist)
    subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
    result = subprocess.run(["launchctl", "load", str(plist_path)], capture_output=True)
    if result.returncode == 0:
        print(f"WhisperClip instalado como servicio de inicio automatico.")
        print(f"Archivo plist: {plist_path}")
        print(f"\nPara iniciarlo ahora sin reiniciar:")
        print(f"  launchctl start com.whisperclip")
    else:
        print(f"Error: {result.stderr.decode()}")


def uninstall_launchd():
    plist_path = Path.home() / "Library/LaunchAgents/com.whisperclip.plist"
    if plist_path.exists():
        subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
        plist_path.unlink()
        print("WhisperClip desinstalado del inicio automatico.")
    else:
        print("WhisperClip no estaba instalado como servicio.")


def main():
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print("""
WhisperClip — Uso:
  python whisperclip.py             Correr la app
  python whisperclip.py config      Ver configuracion actual
  python whisperclip.py modes       Listar modos disponibles
  python whisperclip.py detect-key  Detectar codigo de cualquier tecla
  python whisperclip.py install     Instalar inicio automatico (launchd)
  python whisperclip.py uninstall   Desinstalar inicio automatico
""")
        return

    if "config" in args:
        print(json.dumps(load_config(), indent=2, ensure_ascii=False))
        return
    elif "modes" in args:
        for key, mode in CLAUDE_MODES.items():
            print(f"  {key:<15} -> {mode['name']}")
        return
    elif "detect-key" in args:
        print("\nPresiona la tecla que queres usar (Ctrl+C para salir)...\n")
        def on_press(k):
            vk = getattr(k, "vk", None)
            char = getattr(k, "char", None)
            print(f"  key={k}  char={char}  vk={vk}  -> usa 'vk:{vk}' en config.json")
        with keyboard.Listener(on_press=on_press) as l:
            try:
                l.join()
            except KeyboardInterrupt:
                pass
        return
    elif "install" in args:
        install_launchd()
        return
    elif "uninstall" in args:
        uninstall_launchd()
        return

    config = load_config()
    if not CONFIG_PATH.exists():
        save_config(config)

    app = WhisperClipMenuApp(config)
    app.run()


if __name__ == "__main__":
    main()
