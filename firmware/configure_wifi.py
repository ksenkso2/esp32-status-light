#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


def parse_credentials(text):
    stripped = text.strip()
    if not stripped:
        raise ValueError("The credentials file is empty")

    if stripped.startswith("{"):
        values = json.loads(stripped)
        ssid = values.get("ssid") or values.get("wifi_ssid")
        password = values.get("password") or values.get("wifi_password")
        if not password:
            raise ValueError("The JSON credentials need a password field")
        return ssid, password

    lines = stripped.splitlines()
    values = {}
    for line in lines:
        key, separator, value = line.partition("=")
        if separator:
            values[key.strip().lower()] = value.strip().strip("\"'")

    password = values.get("password") or values.get("wifi_password")
    if password is None:
        for line in lines:
            candidate = line.strip()
            key, separator, _ = candidate.partition("=")
            if not separator or key.strip().lower() not in {
                "ssid",
                "wifi_ssid",
                "password",
                "wifi_password",
            }:
                password = candidate
                break
    ssid = values.get("ssid") or values.get("wifi_ssid")
    if not password:
        raise ValueError("The Wi-Fi password is empty")
    return ssid, password


def main():
    parser = argparse.ArgumentParser(
        description="Create a local ESP32 credentials header without displaying secrets"
    )
    parser.add_argument("--ssid", help="Wi-Fi network name, unless stored in the file")
    parser.add_argument(
        "--password-file",
        type=Path,
        default=Path(__file__).resolve().parent / ".wifi",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "include" / "secrets.h",
    )
    args = parser.parse_args()

    try:
        file_ssid, password = parse_credentials(args.password_file.read_text())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    ssid = args.ssid or file_ssid
    if not ssid:
        parser.error("Add ssid to the credentials file or provide --ssid")

    content = (
        "#pragma once\n\n"
        f"constexpr char kWifiSsid[] = {json.dumps(ssid)};\n"
        f"constexpr char kWifiPassword[] = {json.dumps(password)};\n"
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content)
    args.output.chmod(0o600)
    print(f"Credentials written to {args.output}; the password was not displayed.")


if __name__ == "__main__":
    main()
