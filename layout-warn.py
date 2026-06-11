#!/usr/bin/env python3
"""
layout-warn — beep-only wrong-keyboard-layout watchdog (X11).

Watches typed words globally. When a finished word looks like it was typed
in the WRONG layout (gibberish in the current alphabet, but a real word once
key-swapped to the other layout), it plays a short bell. It NEVER switches
the layout or touches your text — a false bell costs nothing, just ignore it.

Deps: python3-xlib, hunspell + hunspell-en-us + hunspell-ru, paplay (libcanberra/pulse).
Layouts assumed: us (latin) + ru (cyrillic). Group 1 = russian.
"""

import subprocess
import sys
import os
import time

from Xlib import X, XK, display
from Xlib.ext import record
from Xlib.protocol import rq

# --- physical key map: us letter -> russian letter (ЙЦУКЕН) ---
EN2RU = {
    'q': 'й', 'w': 'ц', 'e': 'у', 'r': 'к', 't': 'е', 'y': 'н', 'u': 'г',
    'i': 'ш', 'o': 'щ', 'p': 'з', '[': 'х', ']': 'ъ',
    'a': 'ф', 's': 'ы', 'd': 'в', 'f': 'а', 'g': 'п', 'h': 'р', 'j': 'о',
    'k': 'л', 'l': 'д', ';': 'ж', "'": 'э',
    'z': 'я', 'x': 'ч', 'c': 'с', 'v': 'м', 'b': 'и', 'n': 'т', 'm': 'ь',
    ',': 'б', '.': 'ю', '`': 'ё',
}
RU2EN = {v: k for k, v in EN2RU.items()}

BELL = '/usr/share/sounds/freedesktop/stereo/bell.oga'
MIN_LEN = 3            # ignore words shorter than this
MOD_MASK = (X.ControlMask | X.Mod1Mask | X.Mod4Mask)  # Ctrl/Alt/Super => shortcut


class Speller:
    """Persistent `hunspell -a` (ispell-compatible) pipe for one dictionary.

    Self-healing: if the pipe dies, it is respawned on the next query so a
    crashed hunspell never permanently disables detection.
    """
    def __init__(self, dic):
        self.dic = dic
        self.p = None
        self.ok = False
        self._spawn()

    def _spawn(self):
        try:
            self.p = subprocess.Popen(
                ['hunspell', '-a', '-d', self.dic],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, bufsize=1)
            self.p.stdout.readline()  # consume version banner
            self.ok = True
        except Exception as e:
            self.p = None
            self.ok = False
            print(f'[layout-warn] hunspell {self.dic} unavailable: {e}',
                  file=sys.stderr)

    def _query(self, word):
        self.p.stdin.write(word + '\n')
        self.p.stdin.flush()
        verdict = True
        while True:
            line = self.p.stdout.readline()
            if line == '':                      # pipe closed -> hunspell died
                raise BrokenPipeError
            if line == '\n':
                break
            if line[0] in ('&', '#'):           # miss / none
                verdict = False
        return verdict

    def known(self, word):
        for _ in range(2):                      # one retry after respawn
            if not self.ok or self.p is None or self.p.poll() is not None:
                self._spawn()
                if not self.ok:
                    return None
            try:
                return self._query(word)
            except Exception:
                self.ok = False                 # force respawn on next loop
        return None


def beep():
    try:
        subprocess.Popen(['paplay', BELL],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        sys.stdout.write('\a')
        sys.stdout.flush()


class Watcher:
    def __init__(self):
        self.en = Speller('en_US')
        self.ru = Speller('ru_RU')
        if not self.ru.ok:
            print('[layout-warn] WARNING: no russian dict (hunspell-ru). '
                  'Latin->cyrillic detection disabled.', file=sys.stderr)
        self.local = display.Display()
        self.record = display.Display()
        self.typed = []   # chars as seen on screen
        self.swap = []    # same word swapped to the other layout

    def reset(self):
        self.typed = []
        self.swap = []

    def finalize(self):
        if len(self.typed) < MIN_LEN:
            self.reset()
            return
        typed = ''.join(self.typed).lower()
        swap = ''.join(self.swap).lower()
        if typed.isascii():                       # latin typed, maybe meant ru
            ok_now = self.en.known(typed)
            ok_swap = self.ru.known(swap)
        else:                                     # cyrillic typed, maybe meant en
            ok_now = self.ru.known(typed)
            ok_swap = self.en.known(swap)
        # beep only when current word is clearly wrong AND swap is a real word
        if ok_now is False and ok_swap is True:
            beep()
        self.reset()

    def key_to_char(self, keycode):
        """us-layout base char for this physical key, or None."""
        ks = self.local.keycode_to_keysym(keycode, 0)
        if ks == X.NoSymbol:
            return None
        s = XK.keysym_to_string(ks)
        if s and len(s) == 1:
            return s
        return None

    def handle(self, keycode, state):
        if state & MOD_MASK:          # Ctrl/Alt/Super held => shortcut
            self.finalize()
            return
        ks = self.local.keycode_to_keysym(keycode, 0)
        if ks == XK.XK_BackSpace:
            if self.typed:
                self.typed.pop()
                self.swap.pop()
            return
        base = self.key_to_char(keycode)
        if base is None:              # Enter/Tab/arrows/etc -> boundary
            self.finalize()
            return
        base = base.lower()
        ru_char = EN2RU.get(base)
        # word-key = anything that is a letter in EITHER layout. The keys
        # [ ] ; ' , . ` are punctuation in us but letters (х ъ ж э б ю ё) in ru,
        # so they must NOT break a word typed in the wrong layout.
        if ru_char is None:           # real non-letter (space/digit/-/etc) -> boundary
            self.finalize()
            return
        group = (state >> 13) & 3
        if group == 1:                # russian layout active
            self.typed.append(ru_char)
            self.swap.append(base)
        else:                         # latin layout active
            self.typed.append(base)
            self.swap.append(ru_char)

    def run(self):
        ctx = self.record.record_create_context(
            0,
            [record.AllClients],
            [{
                'core_requests': (0, 0),
                'core_replies': (0, 0),
                'ext_requests': (0, 0, 0, 0),
                'ext_replies': (0, 0, 0, 0),
                'delivered_events': (0, 0),
                'device_events': (X.KeyPress, X.KeyPress),
                'errors': (0, 0),
                'client_started': False,
                'client_died': False,
            }])
        self.record.record_enable_context(ctx, self.callback)
        self.record.record_free_context(ctx)

    def callback(self, reply):
        if reply.category != record.FromServer or reply.client_swapped:
            return
        data = reply.data
        while data:
            ev, data = rq.EventField(None).parse_binary_value(
                data, self.record.display, None, None)
            if ev.type == X.KeyPress:
                self.handle(ev.detail, ev.state)


    def close(self):
        for d in (self.local, self.record):
            try:
                d.close()
            except Exception:
                pass


def main():
    if not os.path.exists(BELL):
        print(f'[layout-warn] bell sound missing: {BELL}', file=sys.stderr)
    while True:                       # supervisor: survive X restarts / crashes
        w = None
        try:
            w = Watcher()
            w.run()                   # blocks until the record stream ends
        except KeyboardInterrupt:
            return
        except Exception as e:
            print(f'[layout-warn] restart after error: {e!r}', file=sys.stderr)
        finally:
            if w is not None:
                w.close()
        time.sleep(2)                 # backoff before reconnecting


if __name__ == '__main__':
    main()
