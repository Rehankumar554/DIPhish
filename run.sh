#!/bin/bash
echo "[*] Launching Device Info Tool..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python DIPhish.py
