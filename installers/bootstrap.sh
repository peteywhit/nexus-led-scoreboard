#!/usr/bin/env bash
set -e

echo "Creating venv..."
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

echo "Done."
