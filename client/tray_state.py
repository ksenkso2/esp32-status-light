import json
import os
import queue
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path

from status_client import DeviceError

STATE_LABELS = {
    "free": "Свободен",
    "busy": "Занят",
    "call": "На созвоне",
}


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class WorkerEvent:
    kind: str
    revision: int
    state: object = None
    error: object = None
    pending: bool = False


def config_path():
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        root = Path(config_home).expanduser()
        if not root.is_absolute():
            root = Path.home() / ".config"
    else:
        root = Path.home() / ".config"
    return root / "esp32-status-light" / "tray.json"


def load_desired_state(path=None):
    path = Path(path) if path is not None else config_path()
    try:
        with path.open(encoding="utf-8") as config_file:
            config = json.load(config_file)
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ConfigError(f"Не удалось прочитать настройки: {error}") from None

    if not isinstance(config, dict):
        raise ConfigError(f"Некорректный желаемый режим в {path}")
    state = config.get("state")
    if not isinstance(state, str) or state not in STATE_LABELS:
        raise ConfigError(f"Некорректный желаемый режим в {path}")
    return state


def save_desired_state(state, path=None):
    if state not in STATE_LABELS:
        raise ValueError(f"Unknown state: {state}")
    path = Path(path) if path is not None else config_path()
    temporary_path = None
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as config_file:
            temporary_path = Path(config_file.name)
            json.dump({"state": state}, config_file, ensure_ascii=False)
            config_file.write("\n")
            config_file.flush()
            os.fsync(config_file.fileno())
        os.replace(temporary_path, path)
    except OSError as error:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except OSError:
                pass
        raise ConfigError(f"Не удалось сохранить настройки: {error}") from None


class StatusWorker:
    def __init__(self, client):
        self.client = client
        self.events = queue.Queue()
        self._commands = queue.Queue()
        self._lock = threading.Lock()
        self._stopped = threading.Event()
        self._refresh_queued = False
        self._revision = 0
        self._retry_state = None
        self._retry_revision = 0
        self._thread = threading.Thread(
            target=self._run,
            name="esp32-status-requests",
            daemon=True,
        )

    def start(self):
        self._thread.start()

    def submit_state(self, state):
        if state not in STATE_LABELS:
            raise ValueError(f"Unknown state: {state}")
        with self._lock:
            if self._stopped.is_set():
                return None
            self._revision += 1
            self._retry_state = state
            self._retry_revision = self._revision
            revision = self._revision
            self._commands.put(("set", state, revision))
        return revision

    def submit_refresh(self):
        with self._lock:
            if self._stopped.is_set() or self._refresh_queued:
                return
            self._refresh_queued = True
            self._commands.put(("refresh", None, None))

    def stop(self):
        with self._lock:
            if self._stopped.is_set():
                return
            self._stopped.set()
            self._commands.put(("stop", None, None))

    def is_alive(self):
        return self._thread.is_alive()

    def join(self):
        self._thread.join()

    def _run(self):
        while not self._stopped.is_set():
            command, state, revision = self._commands.get()
            if command == "stop" or self._stopped.is_set():
                break
            if command == "refresh":
                with self._lock:
                    self._refresh_queued = False
                    if self._retry_state is not None:
                        command = "set"
                        state = self._retry_state
                        revision = self._retry_revision
                    else:
                        revision = self._revision
            self._execute(command, state, revision)

    def _execute(self, command, state, revision):
        pending = command == "set"
        try:
            if pending:
                confirmed_state = self.client.set_status(state)
            else:
                confirmed_state = self.client.get_status()
        except (DeviceError, ValueError) as error:
            self.events.put(
                WorkerEvent("error", revision, error=str(error), pending=pending)
            )
        except Exception as error:
            message = str(error) or error.__class__.__name__
            self.events.put(WorkerEvent("error", revision, error=message, pending=pending))
        else:
            if pending:
                with self._lock:
                    if self._retry_revision == revision:
                        self._retry_state = None
            self.events.put(
                WorkerEvent("confirmed", revision, state=confirmed_state, pending=pending)
            )
