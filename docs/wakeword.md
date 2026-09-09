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
