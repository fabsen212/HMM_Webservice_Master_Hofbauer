#!/bin/bash

# Starte RQ Worker in neuem Terminalfenster
gnome-terminal -- bash -c "rq worker app.rq; exec bash" &

# Starte Flask App im aktuellen Terminal
python3 app.py
