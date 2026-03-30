.PHONY: venv run build clean install

PYTHON = venv/bin/python
PIP    = venv/bin/pip

venv:
	python3.11 -m venv venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt

run: venv
	$(PYTHON) whisperclip.py

build: venv
	$(PYTHON) setup.py py2app
	@echo "App construida en dist/WhisperClip.app"

clean:
	rm -rf build/ dist/ *.egg-info/

install: build
	cp -R dist/WhisperClip.app ~/Applications/
	@echo "Instalada en ~/Applications/WhisperClip.app"
