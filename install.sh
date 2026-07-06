#!/usr/bin/env bash
# Persona — one-command install & launch
# Usage: curl -fsSL https://raw.githubusercontent.com/ArmadilloArmada/personal-LLM/main/install.sh | bash
set -euo pipefail

INSTALL_DIR="${PERSONA_INSTALL_DIR:-$HOME/.local/share/persona-app}"
BIN_DIR="${HOME}/.local/bin"
DESKTOP_DIR="${HOME}/.local/share/applications"

echo ""
echo "  🎭  Installing Persona..."
echo ""

# Need Python 3.11+
if ! command -v python3 &>/dev/null; then
  echo "Error: python3 is required. Install Python 3.11+ and try again."
  exit 1
fi

PYVER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "  → Python $PYVER"

# Clone or update
if [ -d "$INSTALL_DIR/.git" ]; then
  echo "  → Updating existing install at $INSTALL_DIR"
  git -C "$INSTALL_DIR" pull --ff-only 2>/dev/null || true
elif [ -f "$(dirname "$0")/pyproject.toml" ] && grep -q 'name = "persona"' "$(dirname "$0")/pyproject.toml" 2>/dev/null; then
  INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
  echo "  → Installing from local source: $INSTALL_DIR"
else
  echo "  → Downloading Persona to $INSTALL_DIR"
  mkdir -p "$(dirname "$INSTALL_DIR")"
  git clone --depth 1 https://github.com/ArmadilloArmada/personal-LLM.git "$INSTALL_DIR" 2>/dev/null || {
  echo "  → Git clone failed; copy this repo to $INSTALL_DIR manually"
  exit 1
  }
fi

# Venv + install
cd "$INSTALL_DIR"
if [ ! -d ".venv" ]; then
  echo "  → Creating virtual environment"
  python3 -m venv .venv
fi

.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -e .

# Launcher script
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/persona" << EOF
#!/usr/bin/env bash
exec "$INSTALL_DIR/.venv/bin/persona" "\$@"
EOF
chmod +x "$BIN_DIR/persona"

# Desktop entry
mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_DIR/persona.desktop" << EOF
[Desktop Entry]
Name=Persona
Comment=Cartoon AI crew — your personal agents
Exec=$BIN_DIR/persona app
Icon=applications-graphics
Terminal=false
Type=Application
Categories=Utility;Office;
StartupWMClass=Persona
EOF

echo ""
echo "  ✅  Persona installed!"
echo ""
echo "  Launch options:"
echo "    persona          — open the app (easiest)"
echo "    persona app -w   — native window (after: pip install persona[desktop])"
echo "    Desktop menu     — search 'Persona'"
echo ""
echo "  No Ollama? No problem — demo mode works instantly."
echo "  For full AI: install https://ollama.com then run: ollama pull llama3.2"
echo ""

# Add ~/.local/bin to PATH hint
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  echo "  Add to your shell profile:  export PATH=\"\$HOME/.local/bin:\$PATH\""
  echo ""
fi

# Launch if interactive
if [ -t 0 ] && [ "${PERSONA_NO_LAUNCH:-}" != "1" ]; then
  read -r -p "  Launch Persona now? [Y/n] " ans
  if [[ ! "$ans" =~ ^[Nn] ]]; then
    exec "$BIN_DIR/persona" app
  fi
fi
