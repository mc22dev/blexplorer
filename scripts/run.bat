@echo off
if not exist "venv" (
    python -m venv venv
)
call venv\\Scripts\\activate.bat
pip install -r requirements.txt
pytest
python main_kivy.py
