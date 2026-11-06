#!/usr/bin/env python3

import argparse
import os
import queue
import signal
from pathlib import Path

try:
    import gi

    gi.require_version("Gtk", "3.0")
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3, GLib, Gtk
except (ImportError, ValueError) as error:
    AyatanaAppIndicator3 = None
    GLib = None
    Gtk = None
    GI_IMPORT_ERROR = error
else:
    GI_IMPORT_ERROR = None

from status_client import DeviceClient
from tray_state import (
    STATE_LABELS,
    ConfigError,
    StatusWorker,
    load_desired_state,
    save_desired_state,
)

ICON_DIR = Path(__file__).resolve().parent / "icons"
REFRESH_INTERVAL_MS = 5000
EVENT_POLL_INTERVAL_MS = 100


class StatusTray:
    def __init__(self, client, saved_state=None, config_error=None):
        self.client = client
        self.worker = StatusWorker(client)
        self.desired_state = saved_state
        self.confirmed_state = None
        self.revision = 0
        self.awaiting_confirmation = False
        self.online = None
        self.request_error = None
        self.config_error = config_error
        self.closing = False
        self.updating_menu = False
        self.event_source = None
        self.refresh_source = None
        self.close_source = None
        self.signal_sources = []

        self.indicator = AyatanaAppIndicator3.Indicator.new(
            "esp32-status-light",
            str(ICON_DIR / "connecting.svg"),
            AyatanaAppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        self.indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self._build_menu())
        self._update_view()

        self.worker.start()
        self.event_source = GLib.timeout_add(
            EVENT_POLL_INTERVAL_MS, self._process_events
        )
        self.refresh_source = GLib.timeout_add(
            REFRESH_INTERVAL_MS, self._request_refresh
        )
        if hasattr(GLib, "unix_signal_add"):
            for signal_number in (signal.SIGINT, signal.SIGTERM):
                self.signal_sources.append(
                    GLib.unix_signal_add(
                        GLib.PRIORITY_DEFAULT, signal_number, self.close
                    )
                )

        if saved_state is not None:
            self._select_state(saved_state, persist=False)
        else:
            self.worker.submit_refresh()

    def _build_menu(self):
        menu = Gtk.Menu()
        self.status_item = Gtk.MenuItem(label="Подключение…")
        self.status_item.set_sensitive(False)
        menu.append(self.status_item)
        menu.append(Gtk.SeparatorMenuItem())

        self.state_items = {}
        group = None
        for state, label in STATE_LABELS.items():
            item = Gtk.RadioMenuItem(label=label)
            if group is None:
                group = item
            else:
                item.join_group(group)
            item.connect("activate", self._on_state_activated, state)
            menu.append(item)
            self.state_items[state] = item

        menu.append(Gtk.SeparatorMenuItem())
        self.quit_item = Gtk.MenuItem(label="Выход")
        self.quit_item.connect("activate", self.close)
        menu.append(self.quit_item)
        menu.show_all()
        return menu

    def _on_state_activated(self, item, state):
        if not self.updating_menu and item.get_active():
            self._select_state(state)

    def _select_state(self, state, persist=True):
        if self.closing:
            return
        if persist:
            try:
                save_desired_state(state)
            except ConfigError as error:
                self.config_error = str(error)
            else:
                self.config_error = None
        self.desired_state = state
        self.awaiting_confirmation = True
        self.request_error = None
        revision = self.worker.submit_state(state)
        if revision is not None:
            self.revision = revision
        self._update_view()

    def _request_refresh(self):
        if not self.closing:
            self.worker.submit_refresh()
        return not self.closing

    def _process_events(self):
        if self.closing:
            return False
        while True:
            try:
                event = self.worker.events.get_nowait()
            except queue.Empty:
                break
            if event.revision < self.revision:
                continue

            self.online = event.kind == "confirmed"
            self.request_error = None if self.online else event.error
            if self.online:
                self.confirmed_state = event.state
                if event.pending and event.revision == self.revision:
                    self.awaiting_confirmation = False
            elif not event.pending:
                self.confirmed_state = None
            self._update_view()
        return not self.closing

    def _update_view(self):
        self._update_indicator()
        self._update_menu()

    def _update_indicator(self):
        if self.awaiting_confirmation and self.desired_state is not None:
            state = self.desired_state
            icon_name = f"{state}-pending.svg"
            label = f"Ожидает: {STATE_LABELS[state]}"
            title = f"Ожидает подтверждения: {STATE_LABELS[state]}"
            if self.online is False:
                title += ". ESP32 недоступен; отправка будет повторена"
            elif self.confirmed_state in STATE_LABELS:
                title += f". На устройстве: {STATE_LABELS[self.confirmed_state]}"
        elif self.online is False:
            icon_name = "offline.svg"
            label = "Нет связи"
            title = "ESP32 недоступен"
        elif self.confirmed_state in STATE_LABELS:
            icon_name = f"{self.confirmed_state}.svg"
            label = STATE_LABELS[self.confirmed_state]
            title = f"Текущий режим: {label}"
        else:
            icon_name = "connecting.svg"
            label = "Подключение"
            title = "Получение состояния ESP32"

        self.indicator.set_icon_full(str(ICON_DIR / icon_name), title)
        self.indicator.set_label(label, "Ожидает: На созвоне")
        if hasattr(self.indicator, "set_title"):
            self.indicator.set_title(title)

    def _update_menu(self):
        lines = []
        if self.awaiting_confirmation and self.desired_state is not None:
            lines.append(f"Ожидает отправки: {STATE_LABELS[self.desired_state]}")
        if self.online is False:
            lines.append("ESP32 недоступен")
        elif self.confirmed_state in STATE_LABELS:
            lines.append(f"На устройстве: {STATE_LABELS[self.confirmed_state]}")
        else:
            lines.append("Получение состояния…")
        if self.request_error:
            lines.append(f"Ошибка: {self._short_error(self.request_error)}")
        if self.config_error:
            lines.append(self._short_error(self.config_error))
        self.status_item.set_label("\n".join(lines))

        self.updating_menu = True
        try:
            for state, item in self.state_items.items():
                annotations = []
                if self.online is not False and state == self.confirmed_state:
                    annotations.append("на устройстве")
                if self.awaiting_confirmation and state == self.desired_state:
                    annotations.append("ожидает")
                label = STATE_LABELS[state]
                if annotations:
                    label += f" ({', '.join(annotations)})"
                item.set_label(label)
                item.set_active(self.online is not False and state == self.confirmed_state)
        finally:
            self.updating_menu = False

    @staticmethod
    def _short_error(error):
        message = " ".join(str(error).splitlines())
        if len(message) > 160:
            return message[:157] + "…"
        return message

    def _remove_source(self, source_id):
        if source_id is not None:
            GLib.source_remove(source_id)

    def close(self, *args):
        if self.closing:
            return False
        self.closing = True
        self._remove_source(self.event_source)
        self._remove_source(self.refresh_source)
        for source_id in self.signal_sources:
            self._remove_source(source_id)
        self.event_source = None
        self.refresh_source = None
        self.signal_sources = []
        self.worker.stop()
        self.status_item.set_label("Завершение…")
        for item in self.state_items.values():
            item.set_sensitive(False)
        self.quit_item.set_sensitive(False)
        self.close_source = GLib.timeout_add(50, self._finish_close)
        return False

    def _finish_close(self):
        if self.worker.is_alive():
            return True
        self.close_source = None
        Gtk.main_quit()
        return False


def main():
    parser = argparse.ArgumentParser(description="Tray-клиент ESP32 Status Light")
    parser.add_argument(
        "--host",
        default=os.environ.get("ESP32_STATUS_HOST", "status-light.local"),
        help="hostname или IP-адрес устройства (по умолчанию: status-light.local)",
    )
    parser.add_argument("--port", type=int, default=80)
    parser.add_argument("--timeout", type=float, default=3.0)
    args = parser.parse_args()

    if Gtk is None:
        raise SystemExit(
            "Для tray-клиента нужны PyGObject, GTK3 и AyatanaAppIndicator3. "
            "В Ubuntu установите системные пакеты: python3-gi gir1.2-gtk-3.0 "
            f"gir1.2-ayatanaappindicator3-0.1 ({GI_IMPORT_ERROR})"
        )

    saved_state = None
    config_error = None
    try:
        saved_state = load_desired_state()
    except ConfigError as error:
        config_error = str(error)

    app = StatusTray(
        DeviceClient(args.host, args.port, args.timeout),
        saved_state=saved_state,
        config_error=config_error,
    )
    try:
        Gtk.main()
    finally:
        app.worker.stop()
        app.worker.join()


if __name__ == "__main__":
    main()
