# Training the "Hey Ned" wake word

openWakeWord trains a custom phrase entirely from synthetic speech. No recordings needed for
the first model; add real ones later if false wakes are a problem.

1. Open the openWakeWord training notebook in Google Colab (free GPU is enough):
   https://github.com/dscripka/openWakeWord/blob/main/notebooks/automatic_model_training.ipynb
2. Set the target phrase to `hey ned`. Leave the rest at defaults for the first run.
   Expect roughly 30–60 minutes.
3. Download the resulting `hey_ned.onnx` (ONNX, not tflite).
4. Put it at `models/hey_ned.onnx`, commit, push, and deploy.

Tuning knobs on the Pi (in `/etc/ned/env`): `NED_WAKE_THRESHOLD` (0.5 default; raise toward
0.7 if it false-wakes during calls) and `NED_WAKE_FRAMES` (consecutive 80 ms frames above the
threshold; 2 default). The mute file `/etc/ned/mute` disables listening entirely:
`touch /etc/ned/mute` before a client call, `rm` it after.
