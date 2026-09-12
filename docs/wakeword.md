# Training the "Hey Ned" wake word

openWakeWord trains a custom phrase entirely from synthetic speech. No recordings needed for
the first model; add real ones later if false wakes are a problem.

**Do not use the notebook in the openWakeWord repo.** Its setup cell pins packages that have no
builds for the Python that Colab ships in 2026 (`piper-phonemize`, `speexdsp-ns`), so it fails
before training starts. Observed on hardware day. Use the patched community notebook instead:

https://colab.research.google.com/github/alfiedennen/openwakeword-colab-2026/blob/main/train_wakeword.ipynb

1. Open it in a desktop browser. Runtime → Change runtime type → a GPU (T4 on the free tier).
2. Find the cell that sets the phrase (cell 10 in the current version) and change it to:

   ```python
   TARGET_PHRASE = ['hey ned']
   MODEL_NAME    = 'hey_ned'
   ```

3. Runtime → Run all. Expect about 2.5 hours on a free T4, about 80 minutes on a Pro L4. Every
   cell checks its own output and re-creates what is missing, so a dropped session can simply
   be re-run.
4. The last cell downloads `hey_ned.onnx` through the browser. Keep the ONNX, not tflite.
5. Copy it to the Pi and commit it:

   ```
   scp hey_ned.onnx mike@ned:~/ned-robot/models/
   ```

   then in Ned Brain: "commit models/hey_ned.onnx and push a branch".

Tuning knobs on the Pi (in `/etc/ned/env`): `NED_WAKE_THRESHOLD` (0.5 default; raise toward
0.7 if it false-wakes during calls) and `NED_WAKE_FRAMES` (consecutive 80 ms frames above the
threshold; 2 default). The mute file `/etc/ned/mute` disables listening entirely:
`touch /etc/ned/mute` before a client call, `rm` it after.

## Did he hear me?

Ned plays a short rising two-tone chime the moment he starts listening, and a falling one
when he stops. `NED_WAKE_CHIME=0` turns it off. A visual cue comes with the camera mast LED
in Phase 3, which is already planned for "camera live" and can double as "listening".

## Missed wakes (saying "hey ned" three times)

The synthetic model's recall is mediocre; on the first hardware day it caught about half of
real attempts at threshold 0.5. Tightening the threshold to stop false wakes makes this
worse, so do not fight the two problems with the same knob. **Train the personal verifier
(step 3 below) and the trade-off goes away**: set `NED_WAKE_THRESHOLD` back to 0.5 with
`NED_WAKE_FRAMES=1`, and let the verifier make the final call on your voice.

## False wakes (Ned waking when nobody said "hey ned")

Three levers, cheapest first. Each one is independent; stop when it is quiet.

1. **Tighten the gate.** The first hardware day loosened `NED_WAKE_THRESHOLD` to 0.35 and
   `NED_WAKE_FRAMES` to 1 because the synthetic model was weak. Put them back to `0.5` and
   `2` in `/etc/ned/env`. Watch what a real "hey ned" scores first so you do not overshoot:

   ```
   uv run --extra pi ned-agent wakescore
   ```

   One line per second, peak score as a bar, `WAKE` when it would have fired. Sit quietly,
   type, move the chair, then say "hey ned" from the desk and from six feet. The threshold
   goes just under your real scores and above everything else.

2. **Speech gate.** `NED_WAKE_VAD` (default 0.5) runs Silero VAD next to the wake model and
   zeroes the score when nobody is speaking. On by default; set `0` to turn it off.

3. **Personal verifier.** A second, tiny model trained on your own voice that gets the final
   say whenever the base model fires. Ten minutes, on the Pi, no cloud:

   ```
   uv run --extra pi ned-agent record positive 10     # say "hey ned" ten times
   uv run --extra pi ned-agent record negative 10     # say ten other things
   uv run --extra pi ned-agent train-verifier
   ```

   Writes `models/hey_ned_verifier.pkl` next to the wake model; the next `ned-agent run`
   picks it up (the start-up log says `verifier on`). Commit it from Ned Brain. Vary the
   positives: normal, quiet, across the room, mid-sentence. Negatives should include
   near-misses like "hey Ted", "Ned", and whatever you say most at the desk.

Every wake is logged with its score (`wake: Hey Ned (score 0.71)`), so a false wake in the
log tells you how far to move the threshold.

If all three are not enough, the base model itself needs real recordings: the Colab notebook
accepts your positive clips alongside the synthetic ones. That is a retrain, not a tweak.
