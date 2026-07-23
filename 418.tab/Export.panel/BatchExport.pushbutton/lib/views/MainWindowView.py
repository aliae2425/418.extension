# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

try:
    from ui.base.BaseWindow import BaseWindow
except Exception:
    BaseWindow = object


def _xaml_path():
    here = os.path.dirname(os.path.abspath(__file__))
    button = os.path.abspath(os.path.join(here, '..', '..'))
    return os.path.join(button, 'GUI', 'Views', 'MainWindow.xaml')


class MainWindowView(BaseWindow):
    def __init__(self, view_model):
        super(MainWindowView, self).__init__(_xaml_path(), view_model)
        self._vm = view_model

    def _load(self):
        super(MainWindowView, self)._load()
        self.wire_navigation()
        try:
            self._vm.refresh_par_jeu()
        except Exception:
            pass

    def wire_navigation(self):
        if self._window is None:
            return
        mapping = (('NavAuto', u'auto'),
                   ('NavManual', u'manual'),
                   ('NavSettings', u'settings'))
        for name, mode in mapping:
            btn = self._window.FindName(name)
            if btn is None:
                continue
            self._bind_nav(btn, mode)

    def _bind_nav(self, btn, mode):
        vm = self._vm

        def _on_checked(sender, args):
            try:
                vm.set_mode(mode)
            except Exception:
                pass
        try:
            btn.Checked += _on_checked
        except Exception:
            pass
