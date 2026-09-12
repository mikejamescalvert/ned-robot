#!/usr/bin/env bash
# Verify the reSpeaker XVF3800 is seen, record 5 s, play it back through the array.
set -euo pipefail

echo "USB:"
if ! lsusb | grep -iE 'xmos|seeed|respeaker|xvf' ; then
  echo "  !! mic array not found on USB. Try another port; check lsusb output:"; lsusb; exit 1
fi

CARD="$(arecord -l | grep -iE 'xvf3800|respeaker|xmos|seeed' | head -1 | sed -E 's/^card ([0-9]+):.*/\1/' || true)"
if [[ -z "$CARD" ]]; then
  echo "!! array not listed as an ALSA capture device. arecord -l says:"; arecord -l; exit 1
fi
echo "reSpeaker is ALSA card $CARD"
echo "Capture:";  arecord -l | grep "card $CARD"
echo "Playback:"; aplay -l | grep "card $CARD" || echo "  !! no playback on card $CARD; speaker must be on the array's 3.5mm jack"

# Playback volume. The array boots around 67%, which is -20 dB and inaudible through the
# Pebble: on hardware day this looked exactly like "Ned hears me but never answers". ALSA
# also forgets mixer levels across reboots unless they are stored, so do both.
echo
echo "Playback volume:"
for CTL in PCM Speaker Headphone Master; do
  if amixer -c "$CARD" sget "$CTL" >/dev/null 2>&1; then
    amixer -c "$CARD" sset "$CTL" 100% unmute >/dev/null 2>&1 || true
    echo "  $CTL -> $(amixer -c "$CARD" sget "$CTL" | grep -oE '\[[0-9]+%\]' | head -1) unmuted"
  fi
done
if sudo -n true 2>/dev/null; then
  sudo alsactl store && echo "  saved; survives reboot"
else
  echo "  !! run 'sudo alsactl store' or the volume resets at the next reboot"
fi

DEV="plughw:$CARD,0"
OUT="${TMPDIR:-/tmp}/ned-mic-test.wav"
echo
echo "Recording 5 s from $DEV. Say something from across the room."
arecord -D "$DEV" -f S16_LE -r 16000 -c 1 -d 5 "$OUT"
echo "Playing back through $DEV."
aplay -D "$DEV" "$OUT"
echo
echo "If you heard yourself: mic, speaker, and echo-cancel path are wired correctly."
echo "If you heard nothing: the Pebble's own power and volume knob, then the 3.5mm cable."
echo "Record in STATUS.md: card=$CARD, heard=yes/no, distance."
