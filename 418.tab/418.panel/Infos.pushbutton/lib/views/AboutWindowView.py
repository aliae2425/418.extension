# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

from ui.base.BaseWindow import BaseWindow

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_XAML = os.path.join(_ROOT, 'GUI', 'Views', 'AboutWindow.xaml')


class AboutWindowView(object):
    def __init__(self, view_model):
        self._vm = view_model
        self._win = BaseWindow(_XAML, view_model) if BaseWindow is not None else None

    def show(self):
        if self._win is None:
            print('AboutWindowView: BaseWindow non disponible')
            return
        self._win.show()
