#!/usr/bin/env bash
# Установка layout-warn — beep-only сторож неправильной раскладки.
# Запуск:  bash install.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"

echo ">>> 1/6  Проверка сессии (нужен X11)"
SESSION="${XDG_SESSION_TYPE:-}"
if [ -z "$SESSION" ]; then
    sid=$(loginctl 2>/dev/null | awk -v u="$USER" '$3==u{print $1; exit}') || true
    SESSION=$(loginctl show-session "$sid" -p Type --value 2>/dev/null) || true
fi
if [ "$SESSION" = "wayland" ]; then
    echo "ОШИБКА: сессия Wayland. Сторож использует X11 RECORD — под Wayland" >&2
    echo "глобальный перехват клавиш не работает. Войди в сессию X11/Xorg и повтори." >&2
    echo "(Можно forced-продолжить:  FORCE=1 bash install.sh  — но работать не будет.)" >&2
    [ "${FORCE:-}" = "1" ] || exit 1
elif [ "$SESSION" != "x11" ]; then
    echo "ВНИМАНИЕ: тип сессии '$SESSION' (не определён как x11). Продолжаю, но" >&2
    echo "если это Wayland — сторож не заработает." >&2
fi

echo ">>> 2/6  Зависимости (нужен sudo)"
sudo apt-get update
sudo apt-get install -y python3-xlib hunspell hunspell-ru hunspell-en-us \
                        pulseaudio-utils sound-theme-freedesktop \
                        python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1

echo ">>> 3/6  Скрипты -> ~/.local/bin"
mkdir -p ~/.local/bin
install -m 755 "$DIR/layout-warn.py"      ~/.local/bin/layout-warn.py
install -m 755 "$DIR/layout-warn-tray.py" ~/.local/bin/layout-warn-tray.py

echo ">>> 4/6  systemd --user сервис (сам сторож)"
mkdir -p ~/.config/systemd/user
install -m 644 "$DIR/layout-warn.service" ~/.config/systemd/user/layout-warn.service
systemctl --user daemon-reload
systemctl --user enable --now layout-warn.service

echo ">>> 5/6  Трей-иконка вкл/выкл (автозапуск)"
mkdir -p ~/.config/autostart
# подставить реальный $HOME в Exec= автозапуска
sed "s|^Exec=.*|Exec=$HOME/.local/bin/layout-warn-tray.py|" \
    "$DIR/layout-warn-tray.desktop" > ~/.config/autostart/layout-warn-tray.desktop
# запустить трей сразу (если есть графический сеанс)
setsid "$HOME/.local/bin/layout-warn-tray.py" >/dev/null 2>&1 < /dev/null & disown || true

echo ">>> 6/6  Проверка"
sleep 2
echo -n "Состояние сервиса: "; systemctl --user is-active layout-warn.service || true
echo
echo "ГОТОВО. Набери в любом поле  ghbdtn  + пробел -> должен пискнуть."
echo "Иконка клавиатуры в трее: клик -> меню вкл/выкл."
echo "Логи:      journalctl --user -u layout-warn -f"
echo "Рестарт:   systemctl --user restart layout-warn"
