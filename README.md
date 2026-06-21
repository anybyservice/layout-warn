# Переключатель раскладки — layout-warn

Аналог Punto Switcher под Linux, но **только предупреждает писком**, когда слово
похоже на набранное в неправильной раскладке (us/ru). Раскладку **не меняет** и
текст **не трогает** — ложный писк безвреден (в отличие от ошибочной авто-смены).

> **Windows-версия** — в папке [`windows/`](windows/). Тот же принцип
> (keyboard + spylls + winsound), настраиваемая горячая клавиша, трей,
> portable-сборка с вложенным Python (на винде ничего ставить не надо).

## Что внутри
| Файл | Назначение |
|------|-----------|
| `layout-warn.py` | сам сторож (python3-xlib + hunspell) |
| `layout-warn.service` | systemd --user юнит (автозапуск + Restart=always) |
| `layout-warn-tray.py` | трей-иконка вкл/выкл (GTK3 + AyatanaAppIndicator) |
| `layout-warn-tray.service` | systemd --user сервис трея (автозапуск + Restart=always) |
| `install.sh` | автоустановка одной командой |

## Установка (быстро)
```bash
bash install.sh
```
Спросит sudo для пакетов. После — проверь: набери `ghbdtn` + пробел, должно пискнуть.

## Установка вручную
```bash
# 1. зависимости
sudo apt-get install -y python3-xlib hunspell hunspell-ru hunspell-en-us \
                        pulseaudio-utils sound-theme-freedesktop \
                        python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1

# 2. скрипты
mkdir -p ~/.local/bin
install -m 755 layout-warn.py      ~/.local/bin/layout-warn.py
install -m 755 layout-warn-tray.py ~/.local/bin/layout-warn-tray.py

# 3. сервис (сам сторож)
mkdir -p ~/.config/systemd/user
install -m 644 layout-warn.service ~/.config/systemd/user/layout-warn.service
systemctl --user daemon-reload
systemctl --user enable --now layout-warn.service

# 4. трей-сервис вкл/выкл
install -m 644 layout-warn-tray.service ~/.config/systemd/user/layout-warn-tray.service
systemctl --user daemon-reload
systemctl --user enable --now layout-warn-tray.service
```

## Управление
```bash
systemctl --user status  layout-warn       # состояние сторожа
systemctl --user restart layout-warn       # перезапуск (после правки скрипта)
systemctl --user stop    layout-warn       # стоп сторожа
systemctl --user restart layout-warn-tray  # перезапуск трея (после правки трея)
journalctl --user -u layout-warn -f        # логи живьём
```

## Трей-иконка
Иконка клавиатуры в системном лотке. Клик → меню:
- **Сторож активен** — галка вкл/выкл (запускает/останавливает сервис).
- **Выход (трей)** — закрыть иконку (сам сторож продолжит работать; сервис трея
  перезапустит иконку через ~3с — чтобы убрать насовсем: `systemctl --user stop layout-warn-tray`).

Иконка меняется: клавиатура = активен, пауза = выключен. Состояние
синхронизируется каждые 2 сек (если включил/выключил сервис из терминала —
иконка догонит). Трей лишь управляет сервисом, детект делает `layout-warn.service`.

## Как работает
1. Перехватывает нажатия клавиш глобально (X11 RECORD).
2. Собирает текущее слово; на границе (пробел/enter/пунктуация) проверяет:
   - слово в текущем алфавите — **не** словарное,
   - а его «перестановка» в другую раскладку — словарное.
3. Если да → короткий писк (`bell.oga` через paplay). Иначе тихо.

Словари — hunspell `en_US` + `ru_RU`. Карта клавиш — ЙЦУКЕН ↔ QWERTY.
Скрипт самовосстанавливается: переживает рестарт X-сервера и смерть hunspell-пайпов.

## Настройка (в `layout-warn.py`)
- `MIN_LEN` — мин. длина слова для проверки (по умолчанию 3).
- `BELL` — путь к звуку.
После правки: `cp layout-warn.py ~/.local/bin/ && systemctl --user restart layout-warn`.

## Добавить своё слово (чтобы не пищало на нём)
hunspell авто-подхватывает личный словарь `~/.hunspell_<словарь>`:
`~/.hunspell_ru_RU` для русского, `~/.hunspell_en_US` для английского.
Просто допиши слова, по одному на строку, и перезапусти сервис:
```bash
echo 'кряк'  >> ~/.hunspell_ru_RU
echo 'myword' >> ~/.hunspell_en_US
systemctl --user restart layout-warn      # перечитать словари
```
(проверено: слово из файла становится «известным» — писк на нём пропадает.
Традиционная первая строка-счётчик не обязательна, hunspell её игнорирует.)

## Требования
X11 (не Wayland), Linux Mint / Ubuntu с systemd. Раскладки: us + ru.

## Удаление
```bash
systemctl --user disable --now layout-warn layout-warn-tray
rm -f ~/.config/systemd/user/layout-warn.service \
      ~/.config/systemd/user/layout-warn-tray.service \
      ~/.local/bin/layout-warn.py ~/.local/bin/layout-warn-tray.py
systemctl --user daemon-reload
```
