# -*- coding: utf-8 -*-

import os


class AppPaths(object):
    def __init__(self, base_dir=None):
        # base_dir = dossier lib/core/
        self._base = base_dir or os.path.dirname(__file__)

    def gui_root(self):
        return os.path.normpath(os.path.join(self._base, '..', '..', 'GUI'))

    def windows_xaml(self):
        return os.path.join(self.gui_root(), 'windows.xaml')

    def main_xaml(self):
        return os.path.normpath(os.path.join(self.gui_root(), 'Views', 'index.xaml'))

    def edit_record_xaml(self):
        return os.path.normpath(os.path.join(self.gui_root(), 'Modals', 'EditRecord.xaml'))

    def resource_path(self, filename):
        return os.path.join(self.gui_root(), 'resources', filename)
