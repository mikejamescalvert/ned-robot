# Bringing up the Pi (Phase 0, hardware day)

Target: Ubuntu Server **24.04 LTS** (64-bit) on the Pi 5. This is the ROS 2 Jazzy pairing;
do not flash 26.04. Total time about 30 minutes. The first 10 need a laptop with an SD card
slot; after that everything is SSH or the phone.

## 1. Flash the card (laptop)

1. Install **Raspberry Pi Imager** from raspberrypi.com/software.
2. Device: *Raspberry Pi 5*. OS: *Other general-purpose OS → Ubuntu → Ubuntu Server 24.04 LTS
   (64-bit)*. Storage: the SanDisk card.
3. When asked to apply OS customisation, choose **Edit settings**:
   - Hostname: `ned`
   - Username: your name, with a password
   - Wi-Fi: your SSID and password, country `US`
   - Services tab: **enable SSH**, use password authentication (keys come via Tailscale)
4. Write. Eject.

## 2. Assemble

- Peel the Active Cooler's thermal pads, seat it on the Pi, push the two pins through the
  board, plug its lead into the 4-pin fan header next to the USB-C.
- Card in. Mic array into a blue USB 3 port. Speaker's 3.5mm plug into the **mic array's**
  jack, not the Pi. Speaker's USB-C into a spare phone charger.
- Official 27W supply into the Pi last. Green LED blinks for a minute or two on first boot
  while the disk resizes; it may reboot once.

## 3. First login

From the laptop:

```bash
ssh <yourname>@ned.local
```

If `ned.local` does not resolve yet, get the IP from your router's device list and use that.
Once Tailscale is up, the address is simply `ned` from any of your devices, forever.

## 4. Bootstrap

```bash
git clone https://github.com/mikejamescalvert/ned-robot.git
cd ned-robot
deploy/bootstrap.sh
```

The script is idempotent; rerun it if anything fails. It will pause once to show a Tailscale
login URL: open it on the phone, approve, and the script continues. Afterwards, log out and
back in so the audio group and `~/.local/bin` take effect.

## 5. Check the mic and speaker

```bash
cd ~/ned-robot && deploy/check-audio.sh
```

It records five seconds and plays it back through the array. If you hear yourself, Phase 0
hardware is verified. Note the ALSA card number it prints; the agent config will use it.

## 6. Start the Remote Control session

```bash
claude auth login          # first time only; opens a URL to approve on the phone
cd ~/ned-robot && claude   # first time only; accept "trust this folder", then /exit
deploy/ned-remote.sh       # starts tmux session "ned" running claude remote-control
```

The interactive `claude` run is required once per checkout: Claude Code will not run in a
folder whose trust dialog has not been accepted, and the wrapper cannot answer it. The
wrapper passes `--spawn=same-dir` so the server never prompts about spawn mode.

Detach with `Ctrl+B` then `D`. From then on, the session is in the Claude app under Code as
**Ned Brain**. To reattach over SSH: `tmux attach -t ned`. The wrapper restarts the server if it
gives up after a long network outage.

## 7. Record the observation

Open the **Ned Brain** session from the phone and tell it what `check-audio.sh` printed and whether
you heard yourself. It updates `STATUS.md` and pushes a branch. That is the hardware
observation that Phase 0 setup requires.

## If something goes wrong

- **Pi never appears on the network**: re-check Wi-Fi SSID and country in Imager. Plug in
  Ethernet for the first boot if you have a cable handy; Wi-Fi can be fixed afterwards.
- **No sound**: the speaker must be on the array's jack, and the Pebble needs its own USB
  power. `aplay -l` must list the array as a playback device.
- **`arecord: Permission denied`**: you have not logged out and back in since bootstrap.
- **`claude: command not found`**: same cause; `~/.local/bin` joins PATH at login.
- **Remote Control session shows offline**: SSH in and run `deploy/ned-remote.sh`; it
  reattaches or restarts. The tmux session survives the app losing track of it.
- **`Workspace not trusted` in the tmux loop**: the one-time interactive `claude` run above
  was skipped. Ctrl+C, `tmux kill-session -t ned`, do that step, rerun the wrapper.
- **The loop sits at a `Choose [1/2]` prompt**: an older wrapper without `--spawn`. Answer
  `1`, or pull `main` and rerun `deploy/ned-remote.sh`.
- **`ned-<word>-<word>` sessions appear and vanish**: the account has "Enable Remote Control
  for all sessions" on, so every interactive `claude` on the Pi registers briefly. Harmless.

## Ned hears you but never answers

Playback volume. The array comes up around 67%, which ALSA reports as **-20 dB** and which is
inaudible through the Pebble, so Ned looks broken while the log happily records completed
turns and their cost. ALSA also forgets mixer levels across reboots unless they are stored,
which is why this can appear after a restart on a rig that worked yesterday.

```
amixer -c 0 sset 'PCM',0 100%
amixer -c 0 sset 'PCM',1 100%
speaker-test -D plughw:0,0 -c 2 -t sine -f 440 -l 1   # should be audible
sudo alsactl store                                     # survives the next reboot
```

`deploy/check-audio.sh` now does all of that for you. If a tone still does not play, the fault
is past the array: the Pebble's power, its volume knob, or the 3.5mm cable. The Pi 5 has no
headphone socket, so that cable belongs in the **array's** jack.

Diagnosing from the log: `turn logged; session cost $0.00xx` means Claude answered and the
audio reached the output transport. Seeing that line and hearing nothing puts the fault in the
speaker path, never in the code.

## Running Ned as a service

Once the wake word behaves, stop babysitting it in SSH:

```
sudo cp ~/ned-robot/deploy/ned-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ned-agent
```

Day to day:

| | |
|---|---|
| is it alive | `systemctl is-active ned-agent` |
| watch the log | `journalctl -u ned-agent -f` |
| after a `git pull` | `sudo systemctl restart ned-agent` |
| silence it | `sudo systemctl stop ned-agent` |

**Only one process can hold the microphone.** With the service running, `ned-agent run`,
`wakescore`, and `record` all fail with "no audio devices at all", because PortAudio drops a
busy device from its list rather than reporting it as busy, and the Pi 5 has no other sound
card. Stop the service first, then start it again when you are done.
