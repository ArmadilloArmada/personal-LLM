#!/usr/bin/env bash
# Build a portable macOS Persona folder — unzip and double-click Persona.command
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/dist/Persona-macOS"

rm -rf "$DEST"
mkdir -p "$DEST"

cp "$ROOT/pyproject.toml" "$ROOT/README.md" "$ROOT/install.sh" "$DEST/"
cp -R "$ROOT/src" "$ROOT/personas" "$DEST/"

cat > "$DEST/Persona.command" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
if ! command -v python3 &>/dev/null; then
  osascript -e 'display alert "Persona" message "Python 3.11+ is required. Install from python.org or run: brew install python"'
  exit 1
fi
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -e ".[desktop]"
fi
exec .venv/bin/persona app -w
EOF
chmod +x "$DEST/Persona.command"

cat > "$DEST/README-macOS.txt" << 'EOF'
Persona for macOS
=================

1. Unzip this folder anywhere
2. Double-click Persona.command
3. If macOS blocks it: right-click → Open → Open

First launch installs dependencies into .venv (needs internet once).
Uses demo mode, Ollama, or a cloud API key from Settings.

Data is stored in ~/.persona/
EOF

cd "$ROOT/dist"
rm -f Persona-macOS-portable.zip
zip -r Persona-macOS-portable.zip Persona-macOS
echo "Built dist/Persona-macOS-portable.zip"
