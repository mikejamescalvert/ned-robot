#!/usr/bin/env bash
# The only sanctioned deploy path (PROJECT.md): pull -> deps -> restart -> health -> report.
# Phase 0: no motion unit yet, no colcon. Those lines land in Phase 1.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

echo "==> git"
git fetch -q origin main
git checkout -q main
git pull -q --ff-only origin main
echo "    at $(git rev-parse --short HEAD): $(git log -1 --format=%s)"

echo "==> deps"
uv sync --extra pi -q

echo "==> systemd"
sudo install -m 0644 deploy/ned-agent.service /etc/systemd/system/ned-agent.service
sudo systemctl daemon-reload
sudo systemctl enable -q ned-agent.service
sudo systemctl restart ned-agent.service
sleep 2
if systemctl is-active -q ned-agent.service; then
  echo "    ned-agent: active"
else
  echo "    ned-agent: FAILED"; sudo journalctl -u ned-agent -n 30 --no-pager; exit 1
fi
echo "==> done"
