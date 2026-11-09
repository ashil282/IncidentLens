#!/usr/bin/env bash
set -euo pipefail
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
mkdir -p data
if [[ ! -f .env ]]; then cp .env.example .env; fi
printf '\nEnvironment ready. Run: source .venv/bin/activate\n'
