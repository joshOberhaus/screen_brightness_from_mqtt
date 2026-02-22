$ErrorActionPreference = "Stop"

Set-Location (Split-Path $PSScriptRoot -Parent)

python -m venv .venv
. .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

pyinstaller --onefile --name brightness_from_mqtt brightness_from_mqtt.py
