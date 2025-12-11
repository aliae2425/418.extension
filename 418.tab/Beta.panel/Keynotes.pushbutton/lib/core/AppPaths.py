# -*- coding: utf-8 -*-
import os

class AppPaths(object):
    def __init__(self, base_dir=None):
        self._base = base_dir or os.path.dirname(__file__)

    def main_xaml(self):
        return os.path.normpath(os.path.join(self._base, '..', '..', 'GUI', 'MainWindow.xaml'))

    def gui_root(self):
        return os.path.normpath(os.path.join(self._base, '..', '..', 'GUI'))

    def windows_xaml(self):
        return os.path.join(self.gui_root(), 'windows.xaml')

    def resource_path(self, filename):
        return os.path.join(self.gui_root(), 'resources', filename)
