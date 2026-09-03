# Bill of materials

Buy per phase, not all at once. Nothing for a phase is ordered until the previous phase is
signed off in `STATUS.md`. Prices and availability drift; check the live listing, and say
plainly when a part looks discontinued. Amazon ASINs given where the part was bought there;
the Amazon app accepts an ASIN in its search bar.

## Phase 0 — Desk brain (ordered 2026-09-03, ETA 2026-09-08)

| Part | ASIN | Notes |
|---|---|---|
| Raspberry Pi 5, 16GB | B0DSPYPKRG | |
| Seeed reSpeaker XVF3800 USB 4-Mic Array, with case | B0GVJ5YQ58 | Replaces Mic Array v2.0 (back-ordered). Has 3.5mm out + JST speaker header w/ 5W amp. |
| Creative Pebble V2 speaker | B07VVP8BGD | 3.5mm aux from the mic array. USB-C power from a spare charger, not the Pi. |
| Official Raspberry Pi 27W USB-C PSU | B0D3MFLNC1 | Pi 5 wants 5V/5A. A phone charger throttles USB power. |
| SanDisk Extreme 64GB microSD, A2 | B09X7C7LL1 | A2 rating matters for an OS card. |
| Official Raspberry Pi Active Cooler | B0CLXZBR5P | Sustained audio + Node + Python throttles without it. |
| Spare USB phone charger | already owned | Powers the Pebble. |

Not needed: case (bare on the desk, then on the faceplate), micro-HDMI cable or keyboard
(headless via Raspberry Pi Imager with Wi-Fi + SSH key baked in), camera (Phase 3).

Wiring: Pi USB → mic array. Mic array 3.5mm → Pebble aux in. Pebble USB-C → charger.

## Phase 1 — Motion layer (do not order until Phase 0 is signed off)

| Part | Source | Notes |
|---|---|---|
| iRobot Create 3 | iRobot Education channel | Education channels only. Verify price and availability before ordering; ~$300+ historically. Confirm firmware supports ROS 2 Jazzy at time of purchase. |
| Faceplate mounting hardware | TBD | Standoffs for the Pi + mast base for the camera. Standard mount pattern on the removable faceplate. |
| Bare 4Ω/8Ω speaker with JST lead | TBD | Onto the mic array's 5W amp header. Retires the Pebble and its charger from the robot. |
| USB-C to USB-C cable, short | TBD | Create 3 payload port → Pi 5 power. |

The Pebble and its charger stay on the desk as the bench setup.

## Phase 3 — Senses (do not order until Phase 2 is signed off)

| Part | Source | Notes |
|---|---|---|
| Raspberry Pi Camera Module 3 | Pi resellers | Standard or wide. |
| Pi 5 camera cable, 22-pin to 15-pin | Pi resellers | Module 3 ships with the wrong cable for the Pi 5's mini connector. |
| Camera mast, ~40–60cm, + mount | TBD | Desk height. Decide in Phase 1 so the faceplate layout allows for it. |
| Camera-active LED | any 5mm LED + resistor, or a small addressable LED | On whenever the camera is live. Non-negotiable per `PROJECT.md`. |

## Phase 5 — Polish (optional)

| Part | Source | Notes |
|---|---|---|
| RPLIDAR C1 | Slamtec / resellers | SLAM. Optional. |
| Second body | repeat Phase 0 + Phase 1 lists | One per floor. Not before Phase 2 is signed off on the first body. |

## Open purchasing questions

- Create 3 stock and price on the education channel at Phase 1 time.
- Mast material and mount: 3D-printed vs. off-the-shelf pole. Decide in Phase 1.
