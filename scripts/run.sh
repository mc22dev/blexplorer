#!/bin/bash
if [ ! -d "tmp/venv" ]; then
    python3 -m venv tmp/venv
fi
source tmp/venv/bin/activate
pip install -r requirements.txt
pytest
python src/main.py
