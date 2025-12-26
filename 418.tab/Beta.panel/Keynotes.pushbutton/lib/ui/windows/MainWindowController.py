# -*- coding: utf-8 -*-

from .KeynoteManagerWindow import KeynoteManagerWindow


class MainWindowController(object):
    def __init__(self):
        self._win = None

    def show(self, reset_config=False):
        self._win = KeynoteManagerWindow(reset_config=reset_config)
        self._win.ShowDialog()
        return True
