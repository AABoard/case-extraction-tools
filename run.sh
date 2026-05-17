#!/usr/bin/env bash
# Run case-extract CLI. Use after: source .venv/bin/activate && pip install -r requirements.txt
cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}src"
exec python -m case_extraction.cli "$@"
