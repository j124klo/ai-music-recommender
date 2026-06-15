#!/bin/bash
# Przejście o folder wyżej względem lokalizacji skryptu (do głównego folderu 'backend')
cd "$(dirname "$0")/.."
source .venv/bin/activate
uvicorn main:app --reload