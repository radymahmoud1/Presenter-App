@echo off
cd /d "%~dp0"
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name PresenterApp --icon assets\icon.ico --add-data "assets\icon.ico;assets" main.py
pause
