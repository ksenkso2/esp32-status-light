# ESP32 Status Light

## Goal

Build a local-network status light controlled from an Ubuntu desktop client.

States and colors:

- `free`: green
- `busy`: blue
- `call`: red

The ESP32 should provide `GET /status`, `POST /status`, and `GET /health`. No cloud service or MQTT broker is needed.

## Hardware

- Board: ESP32-S3-DevKitC-1.
- Onboard addressable RGB LED: GPIO48.
- Keep LED brightness low; the current value is 24 out of 255.
- The separate red power LED and other indicator LEDs are not used for statuses.
- Use the board's native USB interface. Redetect the serial port before flashing or monitoring.
- Provision the Wi-Fi SSID locally. The ESP32 requires a 2.4 GHz network.

## Project layout

- `firmware/`: PlatformIO Arduino firmware.
- `firmware/src/main.cpp`: Wi-Fi, mDNS, HTTP API, and status-light application.
- `firmware/lib/StatusLight/`: state parsing, LED control, and persistent state.
- `client/status_client.py`: Python Tkinter GUI, command-line client, and shared HTTP `DeviceClient`.
- `client/status_tray.py`: Ubuntu GNOME AppIndicator tray client.
- `client/tray_state.py`: background HTTP worker and XDG desired-state persistence.
- `client/icons/`: tray state and pending/offline icons.
- `client/install_ubuntu.sh` and `client/uninstall_ubuntu.sh`: per-user XDG autostart setup and removal.
- `client/status-light.desktop`: autostart template.
- `client/UBUNTU.md`: Ubuntu 24.04 installation, configuration, and troubleshooting instructions.
- `firmware/configure_wifi.py`: generates the Git-ignored credentials header.
- `firmware/generate_credentials.py`: PlatformIO pre-build credential generation hook.
- `firmware/configure_local_wifi.sh`: optional manual header regeneration command.
- `case/enclosure.py`: parametric CadQuery enclosure for the user's S3-N16R8-compatible board (GPIO48, USB-C, module antenna overhang).
- `case/index.html`: offline interactive 3D preview with assembled, exploded, and print-layout views.
- `case/stl/`: print-oriented base, lid, diffuser, and USB-insert STL meshes.
- `case/PRINT.txt` and `case/esp32-status-light-case.zip`: printer handoff instructions and bundle.
- `.github/workflows/pages.yml`: deploys `case/` to GitHub Pages at `https://ksenkso2.github.io/esp32-status-light/` when the viewer changes on `main`.
- `README.md`: repository overview with public viewer and printer-bundle links.

## Credentials

Never read, print, copy, or commit `firmware/.wifi` or `firmware/include/secrets.h` in an agent session. Do not expose their contents in logs, diffs, or command output.

Store local settings in `firmware/.wifi`, using this format:

```ini
ssid=your-wifi-ssid
password=your-wifi-password
```

A legacy bare password line can also be combined with an `ssid=...` line. Both this file and the generated header are Git-ignored. Each checkout needs its own `.wifi`; Git does not sync credentials between machines.

PlatformIO generates `firmware/include/secrets.h` automatically before every build, so agents can run the normal build command without inspecting credentials or asking the user to generate the header. `configure_local_wifi.sh` remains available for optional manual regeneration.

## Commands

Run PlatformIO through the project-local virtual environment from the repository root:

```sh
cd firmware
../.venv/bin/pio run
../.venv/bin/pio device list
../.venv/bin/pio run --target upload --upload-port /dev/cu.usbmodem...
../.venv/bin/pio device monitor --port /dev/cu.usbmodem...
```

Replace the example serial device with the detected upload or monitor port.

Run the desktop client from the repository root:

```sh
python3 client/status_client.py --host status-light.local
python3 client/status_client.py --host status-light.local --state free
python3 client/status_client.py --host status-light.local --state busy
python3 client/status_client.py --host status-light.local --state call
```

On Ubuntu, Tkinter is provided by the `python3-tk` package if it is not already installed.

Run the Ubuntu tray client and manage its per-user autostart:

```sh
python3 client/status_tray.py --host status-light.local
bash client/install_ubuntu.sh
bash client/uninstall_ubuntu.sh
```

The tray client requires the Ubuntu system packages documented in `client/UBUNTU.md`. Autostart runs after the user logs into the graphical session. Desired tray state is stored in `~/.config/esp32-status-light/tray.json` or under an absolute `XDG_CONFIG_HOME`; connection settings for autostart are stored separately in `settings.env` in the same directory.

Regenerate the enclosure with CadQuery 2.8+ and open its offline preview from the repository root:

```sh
python3 case/enclosure.py --output-dir case/stl
open case/index.html
```

## Verification

- Build firmware after firmware changes and flash the physical board when available.
- Ask the user to confirm the physical LED colors; serial output alone cannot verify them.
- Exercise clients with real HTTP requests against the ESP32 or a temporary local simulator.
- Test all three GUI buttons or tray selections, status retrieval, desired-state persistence, and offline handling.
- Verify the tray indicator and XDG autostart on Ubuntu 24.04 before calling those features Ubuntu-verified.
- Do not claim the Ubuntu application was verified on Ubuntu when it has only run on the Mac.
- Check enclosure solids and PCB clearance after CAD changes; validate exported meshes and exercise the offline viewer in a browser.
- Do not claim the enclosure is physically verified until a printed set has been fitted to the real board and USB cable.
- Keep generated credentials, `.venv/`, `.pio/`, and Python caches out of Git.

## Current status

Completed:

- Board detection and project-local PlatformIO installation.
- Standalone green/blue/red self-test source, build, flashing, and physical color verification.
- Persistent `StatusLight` module with non-default state restoration verified across reboot.
- Integrated Wi-Fi, mDNS, HTTP API, and reconnect logic, compiled and flashed successfully.
- Local Wi-Fi credential provisioning without exposing the password.
- Desktop GUI, CLI client, and Ubuntu AppIndicator tray client.
- Per-user XDG autostart installer, uninstaller, and Russian Ubuntu documentation.
- GUI button, tray state, persistence, status retrieval, retry, and offline-handling checks against local simulators.
- Real HTTP health/status checks and all three CLI state changes against the ESP32.
- User confirmation of blue/red/green hardware states and automatic reconnection after a router outage.
- Parametric four-part enclosure with a removable USB insert, side vents, and board locating stops; offline interactive preview, watertight print-oriented STLs, and printer handoff bundle.

Not completed:

- Ubuntu 24.04 AppIndicator display, graphical-session autostart, and end-to-end client verification on Ubuntu remain; current tray checks were performed on the Mac.
- Physical printing, board/USB-insert fit, cable clearance, lid friction, and LED visibility through the diffuser remain unverified.

Next steps:

1. Install the documented dependencies and run `bash client/install_ubuntu.sh` on Ubuntu 24.04.
2. Verify all three tray selections, pending/offline retry, status refresh, persistence, and autostart on Ubuntu against `status-light.local`.
3. Print the enclosure, check the real board and USB cable, and adjust the insert, `fit_clearance`, or LED placement if needed.
