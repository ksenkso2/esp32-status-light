#!/usr/bin/env bash
set -euo pipefail

fail() {
    printf 'Ошибка: %s\n' "$*" >&2
    exit 1
}

(( EUID != 0 )) || fail 'запустите скрипт от того же обычного пользователя, без sudo.'
if [[ -n ${XDG_CONFIG_HOME:-} ]]; then
    config_home=$XDG_CONFIG_HOME
else
    [[ -n ${HOME:-} ]] || fail 'не задана переменная HOME.'
    config_home=$HOME/.config
fi
[[ $config_home == /* ]] || fail 'XDG_CONFIG_HOME должен быть абсолютным путём.'

autostart_file="$config_home/autostart/status-light.desktop"
if [[ -e $autostart_file || -L $autostart_file ]]; then
    rm -- "$autostart_file"
    printf 'Автозапуск удалён: %s\n' "$autostart_file"
else
    printf 'Автозапуск уже отсутствует: %s\n' "$autostart_file"
fi
printf 'Настройки и файлы проекта сохранены: %s\n' "$config_home/esp32-status-light/settings.env"
