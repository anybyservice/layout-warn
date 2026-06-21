"""
LayoutWarn (Windows) — beeps when a word looks like it was typed in the wrong
keyboard layout (RU<->EN), Punto-style, warn-only (never switches anything).

Logic: buffer characters as they are typed. On a word boundary, take the word.
  - If it is a valid word in its own alphabet's dictionary -> OK, stay silent.
  - Otherwise remap it to the opposite physical-key layout. If THAT is a valid
    word in the opposite dictionary -> the user typed in the wrong layout -> beep.

No keystroke content is stored or sent anywhere. Buffer is the current word only
and is cleared on every word boundary.
"""

import json
import os
import sys
import threading
import winsound

import keyboard
from spylls.hunspell import Dictionary


# --- Physical key map QWERTY <-> ЙЦУКЕН (standard Windows RU layout) ----------
_EN = r"qwertyuiop[]asdfghjkl;'zxcvbnm,./"
_RU = r"йцукенгшщзхъфывапролджэячсмитьбю."

EN2RU = {e: r for e, r in zip(_EN, _RU)}
RU2EN = {r: e for e, r in zip(_EN, _RU)}


def _remap(word, table):
    out = []
    for ch in word:
        if ch not in table:
            return None          # contains a char with no mapping -> give up
        out.append(table[ch])
    return "".join(out)


def _has_cyrillic(word):
    return any("а" <= ch <= "я" or ch == "ё" for ch in word)


# --- Dictionaries -------------------------------------------------------------
def _resource(rel):
    # PyInstaller onefile sets _MEIPASS; portable run uses the script's folder.
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


# spylls.Dictionary.from_files wants the path WITHOUT extension; it appends
# .aff / .dic itself. So dict/en -> dict/en.aff + dict/en.dic.
EN_DICT = Dictionary.from_files(_resource(os.path.join("dict", "en")))
RU_DICT = Dictionary.from_files(_resource(os.path.join("dict", "ru")))


def _is_wrong_layout(word):
    word = word.lower()
    if len(word) < 2:
        return False
    if _has_cyrillic(word):
        own, other, table = RU_DICT, EN_DICT, RU2EN
    else:
        own, other, table = EN_DICT, RU_DICT, EN2RU

    if own.lookup(word):
        return False                     # valid as typed -> fine
    converted = _remap(word, table)
    if converted and other.lookup(converted):
        return True                      # gibberish here, valid there -> wrong
    return False


# --- Beep (non-blocking so the hook is never stalled) -------------------------
def _beep():
    threading.Thread(
        target=lambda: winsound.Beep(2200, 90), daemon=True
    ).start()


# --- Enable / disable toggle --------------------------------------------------
_enabled = True


def _toggle():
    global _enabled
    _enabled = not _enabled
    # audible confirmation: rising = on, falling = off
    pair = (1500, 2500) if _enabled else (2500, 1500)

    def _chirp():
        for f in pair:
            winsound.Beep(f, 70)

    threading.Thread(target=_chirp, daemon=True).start()


# --- Configurable hotkey (persisted to %APPDATA%\LayoutWarn\config.json) -------
_DEFAULT_HOTKEY = "ctrl+alt+p"
_CONF_DIR = os.path.join(
    os.environ.get("APPDATA") or os.path.expanduser("~"), "LayoutWarn"
)
_CONF = os.path.join(_CONF_DIR, "config.json")

_hotkey = _DEFAULT_HOTKEY
_hotkey_handle = None


def _load_config():
    global _hotkey
    try:
        with open(_CONF, encoding="utf-8") as f:
            _hotkey = json.load(f).get("hotkey", _DEFAULT_HOTKEY) or _DEFAULT_HOTKEY
    except Exception:
        _hotkey = _DEFAULT_HOTKEY


def _save_config():
    try:
        os.makedirs(_CONF_DIR, exist_ok=True)
        with open(_CONF, "w", encoding="utf-8") as f:
            json.dump({"hotkey": _hotkey}, f)
    except Exception:
        pass


def _apply_hotkey(hk):
    """Bind hk to the toggle, replacing any previous binding."""
    global _hotkey_handle, _hotkey
    if _hotkey_handle is not None:
        try:
            keyboard.remove_hotkey(_hotkey_handle)
        except (KeyError, ValueError):
            pass
    _hotkey_handle = keyboard.add_hotkey(hk, _toggle)
    _hotkey = hk


def _change_hotkey():
    """Record the next key combo the user presses and make it the new hotkey."""

    def _record():
        winsound.Beep(2000, 60)  # listening...
        try:
            hk = keyboard.read_hotkey(suppress=False)
        except Exception:
            return
        if hk:
            _apply_hotkey(hk)
            _save_config()
            winsound.Beep(1500, 70)
            winsound.Beep(2500, 70)  # saved

    threading.Thread(target=_record, daemon=True).start()


# --- Keystroke buffer ---------------------------------------------------------
_buffer = []
_BOUNDARY = {"space", "enter", "tab"}


def _on_key(event):
    if event.event_type != "down":
        return
    name = event.name

    if name == "backspace":
        if _buffer:
            _buffer.pop()
        return

    if name in _BOUNDARY:
        _flush()
        return

    if name and len(name) == 1 and (name.isalpha() or name in EN2RU or name in RU2EN):
        _buffer.append(name)
    else:
        # any other key (punctuation, ctrl, arrows...) ends the current word
        _flush()


def _flush():
    if not _buffer:
        return
    word = "".join(_buffer)
    _buffer.clear()
    if not _enabled:
        return
    try:
        if _is_wrong_layout(word):
            _beep()
    except Exception:
        pass


# --- Tray icon (optional; quit via right-click) -------------------------------
def _run_tray():
    try:
        import pystray
        from PIL import Image, ImageDraw
    except Exception:
        # no tray libs -> just block forever; kill via Task Manager
        keyboard.wait()
        return

    img = Image.new("RGB", (64, 64), (30, 30, 30))
    d = ImageDraw.Draw(img)
    d.ellipse((14, 14, 50, 50), fill=(80, 200, 120))

    def _quit(icon, _item):
        keyboard.unhook_all()
        icon.stop()

    icon = pystray.Icon(
        "LayoutWarn",
        img,
        "LayoutWarn — wrong-layout beeper",
        menu=pystray.Menu(
            pystray.MenuItem(
                "Enabled",
                lambda _i, _it: _toggle(),
                checked=lambda _it: _enabled,
            ),
            pystray.MenuItem(
                lambda _it: f"Change hotkey…  ({_hotkey})",
                lambda _i, _it: _change_hotkey(),
            ),
            pystray.MenuItem("Quit", _quit),
        ),
    )
    icon.run()


def main():
    _load_config()
    keyboard.hook(_on_key)
    _apply_hotkey(_hotkey)
    _run_tray()


if __name__ == "__main__":
    main()
