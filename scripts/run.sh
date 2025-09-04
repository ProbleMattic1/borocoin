#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../backend"
python3 -m venv venv || true
source venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -r requirements.txt
export JWT_SECRET=change-me
uvicorn app:app --reload --port 8000
