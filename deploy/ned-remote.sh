#!/usr/bin/env bash
# Start (or reattach to) the Remote Control session "ned" inside tmux.
# Server mode gives up after ~10 min of network outage; the loop brings it back and
# re-serves the existing sessions. Detach with Ctrl+B then D.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if tmux has-session -t ned 2>/dev/null; then
  exec tmux attach -t ned
fi

# Claude Code refuses to run in a folder until the workspace trust dialog has been
# accepted interactively once. Detect the first run and ask for that up front.
if ! claude --version >/dev/null 2>&1; then
  echo "claude is not on PATH. Log out and back in after bootstrap, then rerun." >&2
  exit 1
fi
if [[ ! -f "$HOME/.claude.json" ]] || ! grep -q "\"$REPO\"" "$HOME/.claude.json" 2>/dev/null; then
  cat <<MSG
First run in this checkout. Claude Code needs the workspace trust dialog accepted once:
  cd $REPO && claude      # choose "Yes, I trust this folder", then /exit
Then rerun deploy/ned-remote.sh.
MSG
  exit 1
fi

tmux new-session -d -s ned -c "$REPO" \
  "while true; do claude remote-control --name \"Ned Brain\" --permission-mode acceptEdits --spawn=same-dir; \
   echo; echo 'remote-control exited; restarting in 10 s (Ctrl+C to stop)'; sleep 10; done"
echo "tmux session 'ned' started in $REPO."
echo "Attach: tmux attach -t ned    Detach: Ctrl+B then D"
echo "Find it in the Claude app under Code as 'Ned Brain'."
