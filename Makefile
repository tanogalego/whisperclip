.PHONY: venv run build clean install

PYTHON = venv/bin/python
PIP    = venv/bin/pip

venv:
	/opt/homebrew/bin/python3.11 -m venv venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run: venv
	$(PYTHON) whisperclip.py

build: venv
	$(PYTHON) setup.py build_app
	@echo "App construida en dist/WhisperClip.app"

clean:
	rm -rf build/ dist/

install: build
	cp -R dist/WhisperClip.app ~/Applications/
	@echo "Instalada en ~/Applications/WhisperClip.app"
