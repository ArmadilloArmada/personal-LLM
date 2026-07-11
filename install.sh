#!/usr/bin/env bash
# Install Persona from the canonical repo.
# Usage: curl -fsSL https://raw.githubusercontent.com/ArmadilloArmada/Persona/main/persona-app/install.sh | bash

set -euo pipefail

REPO="https://github.com/ArmadilloArmada/Persona.git"
INSTALL_DIR="${PERSONA_INSTALL_DIR:-$HOME/Persona}"

echo "==> Persona installer"
echo "    Repo: $REPO"
echo "    Dir:  $INSTALL_DIR"
echo ""
echo "NOTE: personal-LLM has moved to ArmadilloArmada/Persona."
echo ""

if [ -d "$INSTALL_DIR/.git" ]; then
  echo "==> Updating existing install..."
  git -C "$INSTALL_DIR" pull --ff-only
else
  echo "==> Cloning..."
  git clone --depth 1 "$REPO" "$INSTALL_DIR" 2>/dev/null || {
    echo "Clone failed. Try: git clone $REPO"
    exit 1
  }
fi

cd "$INSTALL_DIR/persona-app"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "Python 3.11+ required. Install Python and re-run."
  exit 1
fi

echo "==> Installing Python package..."
"$PY" -m pip install --upgrade pip
"$PY" -m pip install -e ".[desktop]"

echo ""
echo "Done. Run: persona app"
echo "Or download the Windows .exe from:"
echo "  https://github.com/ArmadilloArmada/Persona/releases/latest"
