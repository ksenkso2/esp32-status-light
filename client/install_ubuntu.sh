#!/usr/bin/env bash
set -euo pipefail

readonly PACKAGES=(
    python3
    python3-gi
    gir1.2-gtk-3.0
    gir1.2-ayatanaappindicator3-0.1
)

fail() {
    printf 'Ошибка: %s\n' "$*" >&2
    exit 1
}

(( EUID != 0 )) || fail 'запустите скрипт от обычного пользователя, без sudo.'
[[ $(uname -s) == Linux ]] || fail 'установка поддерживается только в Ubuntu 24.04.'
[[ -r /etc/os-release ]] || fail 'не удалось определить операционную систему.'
(
    . /etc/os-release
    [[ ${ID:-} == ubuntu && ${VERSION_ID:-} == 24.04 ]]
) || fail 'установка поддерживается только в Ubuntu 24.04.'

command -v dpkg-query >/dev/null 2>&1 || fail 'не найден dpkg-query.'
missing_packages=()
for package in "${PACKAGES[@]}"; do
    status=$(dpkg-query -W -f='${Status}' "$package" 2>/dev/null || true)
    [[ $status == 'install ok installed' ]] || missing_packages+=("$package")
done
if (( ${#missing_packages[@]} > 0 )); then
    printf 'Не установлены пакеты: %s\n' "${missing_packages[*]}" >&2
    printf 'Выполните: sudo apt update && sudo apt install %s\n' "${PACKAGES[*]}" >&2
    exit 1
fi

[[ -x /usr/bin/python3 ]] || fail 'не найден системный интерпретатор /usr/bin/python3.'
if ! /usr/bin/python3 - <<'PY'
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("AyatanaAppIndicator3", "0.1")
from gi.repository import AyatanaAppIndicator3, Gtk
PY
then
    fail 'Python не видит GTK3 или AyatanaAppIndicator3; проверьте системные пакеты и отсутствие активного virtualenv.'
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
entrypoint="$script_dir/status_tray.py"
template="$script_dir/status-light.desktop"
[[ -f $entrypoint ]] || fail "не найден $entrypoint."
[[ -f $template ]] || fail "не найден $template."

if [[ -n ${XDG_CONFIG_HOME:-} ]]; then
    config_home=$XDG_CONFIG_HOME
else
    [[ -n ${HOME:-} ]] || fail 'не задана переменная HOME.'
    config_home=$HOME/.config
fi
[[ $config_home == /* ]] || fail 'XDG_CONFIG_HOME должен быть абсолютным путём.'
config_dir="$config_home/esp32-status-light"
config_file="$config_dir/settings.env"
autostart_dir="$config_home/autostart"
autostart_file="$autostart_dir/status-light.desktop"

mkdir -p -- "$config_dir" "$autostart_dir"
if [[ -e $config_file && ! -f $config_file ]]; then
    fail "$config_file существует, но не является обычным файлом."
fi
if [[ ! -f $config_file ]]; then
    (
        umask 077
        printf '%s\n' \
            'ESP32_STATUS_HOST="status-light.local"' \
            'ESP32_STATUS_PORT="80"' \
            'ESP32_STATUS_TIMEOUT="3"' > "$config_file"
    )
fi

ESP32_STATUS_HOST=status-light.local
ESP32_STATUS_PORT=80
ESP32_STATUS_TIMEOUT=3
. "$config_file"
host=$ESP32_STATUS_HOST
port=$ESP32_STATUS_PORT
timeout=$ESP32_STATUS_TIMEOUT

[[ -n $host ]] || fail 'ESP32_STATUS_HOST не должен быть пустым.'
[[ $host != *$'\n'* && $host != *$'\r'* ]] || fail 'ESP32_STATUS_HOST содержит недопустимый перевод строки.'
[[ $script_dir != *$'\n'* && $script_dir != *$'\r'* ]] || fail 'путь к репозиторию содержит неподдерживаемый перевод строки.'
[[ $port =~ ^[0-9]+$ ]] || fail 'ESP32_STATUS_PORT должен быть целым числом от 1 до 65535.'
(( 10#$port >= 1 && 10#$port <= 65535 )) || fail 'ESP32_STATUS_PORT должен быть от 1 до 65535.'
[[ $timeout =~ ^([0-9]+([.][0-9]*)?|[.][0-9]+)$ ]] || fail 'ESP32_STATUS_TIMEOUT должен быть положительным числом секунд.'
/usr/bin/python3 -c 'import sys; sys.exit(0 if float(sys.argv[1]) > 0 else 1)' "$timeout" \
    || fail 'ESP32_STATUS_TIMEOUT должен быть больше нуля.'

desktop_quote() {
    local value=${1//\\/\\\\}
    value=${value//\"/\\\"}
    value=${value//\`/\\\`}
    value=${value//\$/\\\$}
    value=${value//%/%%}
    printf '"%s"' "$value"
}

exec_line="$(desktop_quote /usr/bin/python3) $(desktop_quote "$entrypoint")"
exec_line+=" --host $(desktop_quote "$host") --port $(desktop_quote "$port")"
exec_line+=" --timeout $(desktop_quote "$timeout")"

temporary=$(mktemp "$autostart_dir/.status-light.desktop.XXXXXX")
trap 'rm -f -- "$temporary"' EXIT
exec_replaced=false
while IFS= read -r line || [[ -n $line ]]; do
    if [[ $line == 'Exec=@EXEC@' ]]; then
        printf 'Exec=%s\n' "$exec_line"
        exec_replaced=true
    else
        printf '%s\n' "$line"
    fi
done < "$template" > "$temporary"
[[ $exec_replaced == true ]] || fail 'в шаблоне status-light.desktop отсутствует строка Exec=@EXEC@.'
chmod 0644 "$temporary"
mv -f -- "$temporary" "$autostart_file"
trap - EXIT

printf 'Автозапуск установлен: %s\n' "$autostart_file"
printf 'Настройки: %s\n' "$config_file"
printf 'После изменения настроек повторно запустите client/install_ubuntu.sh.\n'
printf 'Для запуска автоматически созданного экземпляра завершите и повторно войдите в графический сеанс.\n'
