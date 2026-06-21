# LayoutWarn (Windows)

Beep-only wrong-layout warner, RU<->EN. Windows port of the Linux `layout-warn`.
Never switches layout or text — just beeps when a finished word is gibberish in
the layout it was typed but a real word in the other layout.

## How it works
1. Global low-level keyboard hook (`keyboard` lib) buffers the *current word only*.
2. On word boundary (space/enter/tab/punctuation) the word is checked:
   - valid in its own alphabet's Hunspell dict -> silent;
   - else remap to opposite physical keys; if that is valid -> **beep** (2200 Hz).
3. Buffer cleared every boundary. Nothing is stored or sent anywhere.

## Run it (nothing to install)
This zip already bundles a portable Python (`.\python`), all dependencies, and
the dictionaries. On Windows just:

**Double-click `run.bat`.**

It starts with no console window and sits in the tray (green dot);
right-click -> Enabled (toggle) / Change hotkey / Quit.
Use `run_debug.bat` instead if you want to see errors in a console.

No Python install, no internet, no build step needed.

## Optional: make a single .exe
If you'd rather have one `LayoutWarn.exe`, run `build.bat` on Windows (needs a
normal Python install + internet). It re-downloads dicts and runs PyInstaller
to produce `dist\LayoutWarn.exe`.

## Controls
- Hotkey toggles beeping on/off. Confirmation chirp: rising = on, falling = off.
  Default **Ctrl+Alt+P**.
- **Change the hotkey:** tray menu -> **Change hotkey…** -> press the new combo
  (one beep = listening, two = saved). Persists to
  `%APPDATA%\LayoutWarn\config.json`, survives restarts. No rebuild needed.
- Tray menu also has a checkable **Enabled** item (same toggle) and **Quit**.

## Dictionaries
Full LibreOffice dicts: ru_RU = Lebedev's large affixed dictionary, en_US =
SCOWL-based. Pulled by `get_dicts.py` into `.\dict`. Big -> few false silences.

## Autostart
Win+R -> `shell:startup` -> drop a shortcut to `run.bat` (or the exe) there.

## Notes / gotchas
- Low-level keyboard hook looks like a keylogger to AV / anti-cheat. Whitelist
  the folder; expect some games to block hooks.
- `keyboard` needs admin to receive keys from elevated windows. For elevated
  apps, run as admin too.
- Tune beep in `layoutwarn.py` -> `winsound.Beep(2200, 90)`.
- Min word length is 2 (`_is_wrong_layout`) to cut noise on single keys.
