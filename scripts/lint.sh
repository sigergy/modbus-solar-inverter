#!/usr/bin/env bash
# Gates estáticos locales (sin tests): ruff, import-linter y compileall.
set -eu
cd "$(dirname "$0")/.."
bin=.venv/bin
[ -d .venv/Scripts ] && bin=.venv/Scripts
"$bin/ruff" format .
"$bin/ruff" check .
# import-linter añade el cwd a sys.path: desde custom_components/ encuentra modbus_solar
(cd custom_components && "../$bin/lint-imports" --config ../pyproject.toml)
"$bin/python" -m compileall -q custom_components tests
