#!/usr/bin/env python3

import argparse
import json
import os
import queue
import threading
import urllib.error
import urllib.request

try:
    import tkinter as tk
except ImportError:
    tk = None

STATES = {
    "free": "Free",
    "busy": "Kinda busy",
    "call": "On a call",
}
BUTTON_COLORS = {
    "free": "#b9f6ca",
    "busy": "#bbdefb",
    "call": "#ffcdd2",
}


class DeviceError(Exception):
    pass


class DeviceClient:
    def __init__(self, host, port=80, timeout=3.0):
        self.base_url = f"http://{host}:{port}" if port != 80 else f"http://{host}"
        self.timeout = timeout

    def get_status(self):
        return self._request("GET", "/status")

    def set_status(self, state):
        if state not in STATES:
            raise ValueError(f"Unknown state: {state}")
        return self._request("POST", "/status", {"state": state})

    def _request(self, method, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(detail).get("error", detail)
            except json.JSONDecodeError:
                pass
            raise DeviceError(f"HTTP {error.code}: {detail}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            reason = getattr(error, "reason", error)
            raise DeviceError(str(reason)) from None

        try:
            state = json.loads(body)["state"]
        except (json.JSONDecodeError, KeyError, TypeError):
            raise DeviceError("The device returned an invalid response") from None
        if state not in STATES:
            raise DeviceError(f"The device returned an unknown state: {state}")
        return state


class StatusApp:
    def __init__(self, root, client):
        self.root = root
        self.client = client
        self.current_state = None
        self.busy = False
        self.events = queue.Queue()
        self.refresh_job = None

        root.title("Status Light")
        root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", self.close)

        self.connection = tk.StringVar(value=f"Connecting to {client.base_url}…")
        tk.Label(root, textvariable=self.connection, width=38).pack(
            padx=16, pady=(16, 8)
        )

        self.buttons = {}
        for state, label in STATES.items():
            button = tk.Button(
                root,
                text=label,
                width=24,
                height=2,
                bg=BUTTON_COLORS[state],
                activebackground=BUTTON_COLORS[state],
                command=lambda selected=state: self.change_state(selected),
            )
            button.pack(padx=16, pady=5)
            self.buttons[state] = button

        tk.Label(root, text="ESP32 status light").pack(padx=16, pady=(8, 16))
        root.after(0, self.refresh)
        root.after(100, self.process_events)

    def refresh(self):
        self.start_operation(self.client.get_status)

    def change_state(self, state):
        self.start_operation(lambda: self.client.set_status(state))

    def start_operation(self, operation):
        if self.busy:
            return
        self.busy = True
        self.update_buttons()

        def run():
            try:
                self.events.put(("success", operation()))
            except (DeviceError, ValueError) as error:
                self.events.put(("error", str(error)))

        threading.Thread(target=run, daemon=True).start()

    def process_events(self):
        try:
            kind, value = self.events.get_nowait()
        except queue.Empty:
            self.root.after(100, self.process_events)
            return

        self.busy = False
        if kind == "success":
            self.current_state = value
            self.connection.set(f"Connected to {self.client.base_url}")
        else:
            self.current_state = None
            self.connection.set(f"Offline: {value}")
        self.update_buttons()
        self.refresh_job = self.root.after(5000, self.refresh)
        self.root.after(100, self.process_events)

    def update_buttons(self):
        for state, button in self.buttons.items():
            active = state == self.current_state
            button.config(
                state=tk.DISABLED if self.busy else tk.NORMAL,
                relief=tk.SUNKEN if active else tk.RAISED,
                borderwidth=3 if active else 1,
                text=f"{STATES[state]} — active" if active else STATES[state],
            )

    def close(self):
        if self.refresh_job is not None:
            self.root.after_cancel(self.refresh_job)
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description="Control an ESP32 status light")
    parser.add_argument(
        "--host",
        default=os.environ.get("ESP32_STATUS_HOST", "status-light.local"),
        help="device hostname or IP address (default: status-light.local)",
    )
    parser.add_argument("--port", type=int, default=80)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--state", choices=STATES, help="set a state without opening the GUI")
    args = parser.parse_args()

    client = DeviceClient(args.host, args.port, args.timeout)
    if args.state:
        state = client.set_status(args.state)
        print(f"Status set to {STATES[state]}")
        return

    try:
        root = tk.Tk()
    except tk.TclError as error:
        raise SystemExit(f"Cannot open the desktop window: {error}") from None
    StatusApp(root, client)
    root.mainloop()


if __name__ == "__main__":
    if tk is None:
        raise SystemExit("Tkinter is required. On Ubuntu, install the python3-tk package.")
    main()
