#!/usr/bin/env bash
# Persona — one-command install & launch
# Usage: curl -fsSL https://raw.githubusercontent.com/ArmadilloArmada/personal-LLM/main/persona-app/install.sh | bash
#
# Windows users: use the installer instead — see persona-app/DOWNLOAD.md
set -euo pipefail

INSTALL_DIR="${PERSONA_INSTALL_DIR:-$HOME/.local/share/persona-app}"
REPO_DIR="${PERSONA_REPO_DIR:-$(dirname "$INSTALL_DIR")/persona}"
SOURCE_DIR="$INSTALL_DIR"
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
if [ -f "$(dirname "$0")/pyproject.toml" ] && grep -q 'name = "persona"' "$(dirname "$0")/pyproject.toml" 2>/dev/null; then
  SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
  INSTALL_DIR="$SOURCE_DIR"
  echo "  → Installing from local source: $SOURCE_DIR"
elif [ -d "$REPO_DIR/.git" ]; then
  echo "  → Updating existing install at $REPO_DIR"
  git -C "$REPO_DIR" pull --ff-only 2>/dev/null || true
  SOURCE_DIR="$REPO_DIR/persona-app"
  INSTALL_DIR="$SOURCE_DIR"
elif [ -d "$INSTALL_DIR/.git" ] && [ -f "$INSTALL_DIR/pyproject.toml" ]; then
  echo "  → Updating existing install at $INSTALL_DIR"
  git -C "$INSTALL_DIR" pull --ff-only 2>/dev/null || true
  SOURCE_DIR="$INSTALL_DIR"
else
  echo "  → Downloading Persona to $REPO_DIR"
  mkdir -p "$(dirname "$REPO_DIR")"
  git clone --depth 1 https://github.com/ArmadilloArmada/personal-LLM.git "$REPO_DIR" 2>/dev/null || {
    echo "  → Git clone failed; copy this repo to $REPO_DIR manually"
    exit 1
  }
  SOURCE_DIR="$REPO_DIR/persona-app"
  INSTALL_DIR="$SOURCE_DIR"
fi

# Venv + install
cd "$SOURCE_DIR"
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
