#!/usr/bin/env bash
# Push the canonical Persona monorepo to ArmadilloArmada/Persona.
# Requires a GitHub PAT with repo write access to Persona.
#
# Usage:
#   PERSONA_SYNC_TOKEN=ghp_xxx ./scripts/sync-to-persona.sh

set -euo pipefail

if [ -z "${PERSONA_SYNC_TOKEN:-}" ]; then
  echo "Set PERSONA_SYNC_TOKEN to a GitHub PAT with write access to ArmadilloArmada/Persona"
  exit 1
fi

BRANCH="${1:-cursor/persona-canonical-11bf}"
git push "https://x-access-token:${PERSONA_SYNC_TOKEN}@github.com/ArmadilloArmada/Persona.git" "${BRANCH}:main" --force
echo "Done: https://github.com/ArmadilloArmada/Persona"
