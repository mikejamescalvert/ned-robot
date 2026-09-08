#!/usr/bin/env bash
# Start (or reattach to) the Remote Control session "ned" inside tmux.
# Server mode gives up after ~10 min of network outage; the loop brings it back and
# re-serves the existing sessions. Detach with Ctrl+B then D.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if tmux has-session -t ned 2>/dev/null; then
  exec tmux attach -t ned
fi

tmux new-session -d -s ned -c "$REPO" \
  "while true; do claude remote-control --name ned --permission-mode acceptEdits; \
   echo; echo 'remote-control exited; restarting in 10 s (Ctrl+C to stop)'; sleep 10; done"
echo "tmux session 'ned' started in $REPO."
echo "Attach: tmux attach -t ned    Detach: Ctrl+B then D"
echo "Find it in the Claude app under Code as 'ned'."
