@echo off
if not exist "tmp\venv" (
    python -m venv tmp\venv
)
call tmp\venv\Scripts\activate.bat
pip install -r requirements.txt
pytest
python src\main.py
