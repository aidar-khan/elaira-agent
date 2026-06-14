#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/aidar-khan/elaira-agent.git}"
TARGET_DIR="${TARGET_DIR:-/opt/agent}"
SERVICE_NAME="${SERVICE_NAME:-elaira-agent}"
PORT="${PORT:-8000}"

if [[ "${EUID}" -ne 0 ]]; then
  SUDO="sudo"
else
  SUDO=""
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This installer currently supports Ubuntu/Debian with apt-get." >&2
  exit 1
fi

$SUDO apt-get update
$SUDO apt-get install -y python3 python3-venv python3-pip git curl

if [[ -d .git && -f main.py ]]; then
  SRC_DIR="$(pwd)"
  $SUDO mkdir -p "$(dirname "$TARGET_DIR")"
  if [[ "$SRC_DIR" != "$TARGET_DIR" ]]; then
    $SUDO rm -rf "$TARGET_DIR"
    $SUDO mkdir -p "$TARGET_DIR"
    $SUDO cp -a "$SRC_DIR"/. "$TARGET_DIR"/
  fi
else
  $SUDO rm -rf "$TARGET_DIR"
  $SUDO git clone "$REPO_URL" "$TARGET_DIR"
fi

cd "$TARGET_DIR"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

mkdir -p secrets sessions history workspace input output logs tmp knowledge memory tools/custom

if [[ ! -f config.json ]]; then
  cp config.example.json config.json
fi

if [[ ! -f secrets/.env ]]; then
  cat > secrets/.env <<'EOF'
OPENROUTER_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GITHUB_TOKEN=
STORY_GITHUB_TOKEN=
ELAIRA_AGENT_PASSWORD=change-me
EOF
fi

if [[ -t 0 ]]; then
  read -r -p "OpenRouter API key (leave blank to skip): " OPENROUTER_API_KEY_INPUT || true
  read -r -p "Admin password (leave blank to keep current): " ADMIN_PASSWORD_INPUT || true
  if [[ -n "${OPENROUTER_API_KEY_INPUT:-}" ]]; then
    sed -i "s/^OPENROUTER_API_KEY=.*/OPENROUTER_API_KEY=${OPENROUTER_API_KEY_INPUT//\//\\/}/" secrets/.env
  fi
  if [[ -n "${ADMIN_PASSWORD_INPUT:-}" ]]; then
    sed -i "s/^ELAIRA_AGENT_PASSWORD=.*/ELAIRA_AGENT_PASSWORD=${ADMIN_PASSWORD_INPUT//\//\\/}/" secrets/.env
  fi
fi

if [[ ! -d .git ]]; then
  git init -b main >/dev/null
fi
git remote remove origin >/dev/null 2>&1 || true
git remote add origin "${REPO_URL}"


cat > "/tmp/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=Elaira self-hosted agent
After=network.target

[Service]
Type=simple
WorkingDirectory=${TARGET_DIR}
ExecStart=${TARGET_DIR}/.venv/bin/uvicorn main:app --host 0.0.0.0 --port ${PORT}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

$SUDO mv "/tmp/${SERVICE_NAME}.service" "/etc/systemd/system/${SERVICE_NAME}.service"
$SUDO systemctl daemon-reload
$SUDO systemctl enable --now "${SERVICE_NAME}.service"

echo "Installed to ${TARGET_DIR}"
echo "Service: ${SERVICE_NAME}"
echo "UI: http://$(hostname -I | awk '{print $1}'):${PORT}/"
