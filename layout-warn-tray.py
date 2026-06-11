#!/usr/bin/env python3
"""
layout-warn-tray — трей-иконка вкл/выкл для сторожа раскладки layout-warn.

Управляет systemd --user сервисом layout-warn.service:
  - иконка показывает состояние (клавиатура = активен, пауза = выключен)
  - меню: переключатель активности + выход из трея
Сам сторож работает отдельным сервисом; трей лишь старт/стоп.
"""

import subprocess
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('AyatanaAppIndicator3', '0.1')
from gi.repository import Gtk, GLib
from gi.repository import AyatanaAppIndicator3 as AppIndicator

SERVICE = 'layout-warn.service'
ICON_ON = 'input-keyboard-symbolic'
ICON_OFF = 'media-playback-pause-symbolic'


def sysctl(*args):
    """systemctl --user ... ; returns (rc, stdout)."""
    r = subprocess.run(['systemctl', '--user', *args],
                       capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def is_active():
    return sysctl('is-active', SERVICE)[1] == 'active'


class Tray:
    def __init__(self):
        self.ind = AppIndicator.Indicator.new(
            'layout-warn', ICON_ON,
            AppIndicator.IndicatorCategory.APPLICATION_STATUS)
        self.ind.set_status(AppIndicator.IndicatorStatus.ACTIVE)

        self.menu = Gtk.Menu()
        self.toggle = Gtk.CheckMenuItem(label='Сторож активен')
        self.toggle.connect('toggled', self.on_toggle)
        self.menu.append(self.toggle)
        self.menu.append(Gtk.SeparatorMenuItem())
        quit_item = Gtk.MenuItem(label='Выход (трей)')
        quit_item.connect('activate', lambda _: Gtk.main_quit())
        self.menu.append(quit_item)
        self.menu.show_all()
        self.ind.set_menu(self.menu)

        self._syncing = False
        self.refresh()
        GLib.timeout_add_seconds(2, self.refresh)  # следить за внешними изменениями

    def on_toggle(self, item):
        if self._syncing:
            return
        if item.get_active():
            sysctl('start', SERVICE)
        else:
            sysctl('stop', SERVICE)
        self.refresh()

    def refresh(self):
        active = is_active()
        self._syncing = True
        self.toggle.set_active(active)
        self._syncing = False
        self.ind.set_icon_full(ICON_ON if active else ICON_OFF,
                               'layout-warn')
        self.ind.set_title('Раскладка: сторож ' +
                           ('включён' if active else 'выключен'))
        return True  # keep timeout running


if __name__ == '__main__':
    Tray()
    Gtk.main()
