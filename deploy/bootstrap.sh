#!/usr/bin/env bash
# Ned Phase 0 bootstrap for Ubuntu Server 24.04 on a Raspberry Pi 5.
# Idempotent: safe to rerun. Run as your login user (not root) from the repo root.
set -euo pipefail

if [[ $(id -u) -eq 0 ]]; then
  echo "Run this as your normal user, not root (it uses sudo where needed)." >&2
  exit 1
fi
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
log() { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }

log "Waiting for first-boot setup (cloud-init) to finish"
sudo cloud-init status --wait >/dev/null 2>&1 || true

log "Ubuntu packages"
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -q
sudo apt-get -y -q full-upgrade
sudo apt-get -y -q install \
  git tmux curl ca-certificates jq unzip usbutils avahi-daemon build-essential \
  python3 python3-venv python3-pip python3-dev \
  alsa-utils libasound2-dev portaudio19-dev libportaudio2

log "Audio device access for $USER"
sudo usermod -aG audio "$USER"

log "Tailscale"
if ! command -v tailscale >/dev/null; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi
if ! tailscale status >/dev/null 2>&1; then
  echo "A login URL follows. Open it on your phone and approve this machine."
  sudo tailscale up --ssh --hostname=ned
else
  echo "Tailscale already up: $(tailscale ip -4 2>/dev/null | head -1)"
fi

log "uv (Python environments)"
if ! command -v uv >/dev/null && [[ ! -x "$HOME/.local/bin/uv" ]]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

log "Claude Code (native installer, no Node.js required)"
if ! command -v claude >/dev/null && [[ ! -x "$HOME/.local/bin/claude" ]]; then
  curl -fsSL https://claude.ai/install.sh | bash
fi

log "Secrets file /etc/ned/env (template only; fill in on the Pi, never in the repo)"
sudo install -d -m 0750 -o root -g "$USER" /etc/ned
if [[ ! -f /etc/ned/env ]]; then
  sudo install -m 0640 -o root -g "$USER" "$REPO/deploy/env.example" /etc/ned/env
fi

log "Cooling"
if grep -qs pwm-fan /sys/class/thermal/cooling_device*/type; then
  echo "Active Cooler detected."
else
  echo "No pwm-fan cooling device found; check the fan lead is in the 4-pin header."
fi

log "Done"
cat <<MSG
Log out and back in now (audio group and ~/.local/bin take effect at login), then:
  cd $REPO && deploy/check-audio.sh
MSG
