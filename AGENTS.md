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
- `client/status_client.py`: Python Tkinter GUI and command-line client.
- `firmware/configure_wifi.py`: generates the Git-ignored credentials header.
- `firmware/configure_local_wifi.sh`: local provisioning command for the user.

## Credentials

Never read, print, copy, or commit `~/.wifi` or `firmware/include/secrets.h` in an agent session. Do not expose their contents in logs, diffs, or command output.

When credentials are needed, ask the user to run this from the repository root:

```sh
cd firmware
./configure_local_wifi.sh 'your-wifi-ssid'
```

The SSID argument can be omitted if it is stored in the local credentials file. The helper reads the password locally without displaying it. The generated header is Git-ignored.

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

## Verification

- Build firmware after firmware changes and flash the physical board when available.
- Ask the user to confirm the physical LED colors; serial output alone cannot verify them.
- Exercise the client with real HTTP requests against the ESP32 or a temporary local simulator.
- Test all three GUI buttons, status retrieval, and offline handling.
- Do not claim the Ubuntu application was verified on Ubuntu when it has only run on the Mac.
- Keep generated credentials, `.venv/`, `.pio/`, and Python caches out of Git.

## Current status

Completed:

- Board detection and project-local PlatformIO installation.
- Standalone green/blue/red self-test source, build, flashing, and physical color verification.
- Persistent `StatusLight` module with non-default state restoration verified across reboot.
- Integrated Wi-Fi, mDNS, HTTP API, and reconnect logic, compiled and flashed successfully.
- Local Wi-Fi credential provisioning without exposing the password.
- Desktop GUI and CLI client.
- GUI button, status retrieval, and offline-handling checks against a local simulator.
- Real HTTP health/status checks and all three CLI state changes against the ESP32.
- User confirmation of blue/red/green hardware states and automatic reconnection after a router outage.

Not completed:

- Ubuntu application verification remains; end-to-end testing was performed on the Mac.

Next steps:

1. Run the desktop client on Ubuntu against `status-light.local`.
2. Test all three GUI buttons, status refresh, and offline handling on Ubuntu.
