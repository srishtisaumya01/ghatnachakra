#!/bin/bash
# Local development: Django API on :8010 and the web app on http://127.0.0.1:5174 (web/dev.py also forwards /api to the API,
# the way vercel.json does in production).
cd "$(dirname "$0")"
PY=backend/.venv/bin/python
[ -x "$PY" ] || { echo "Create the backend environment first:  cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"; exit 1; }
(cd backend && "../$PY" manage.py migrate --noinput >/dev/null && exec "../$PY" manage.py runserver 127.0.0.1:8010 --noreload) &
API=$!
trap 'kill $API 2>/dev/null' EXIT
exec python3 web/dev.py --port "${PORT:-5174}" --api http://127.0.0.1:8010
