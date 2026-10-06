# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

try:
    from ui.base.BaseWindow import BaseWindow
except Exception:
    BaseWindow = None

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_XAML = os.path.join(_ROOT, 'GUI', 'Views', 'MainWindow.xaml')


class MainWindowView(object):
    def __init__(self, view_model):
        self._vm = view_model
        self._win = BaseWindow(_XAML, view_model) if BaseWindow is not None else None

    def show(self):
        if self._win is None:
            print('MainWindowView: BaseWindow non disponible')
            return
        self._win.show()
