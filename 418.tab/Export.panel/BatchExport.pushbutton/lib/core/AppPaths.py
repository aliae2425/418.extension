# -*- coding: utf-8 -*-
# Centralisation des chemins vers les fichiers XAML et ressources

import os

class AppPaths(object):
    def __init__(self, base_dir=None):
        # base_dir = dossier lib/ (celui-ci)
        self._base = base_dir or os.path.dirname(__file__)

    # Retourne le chemin absolu vers Views/index.xaml
    def main_xaml(self):
        return os.path.normpath(os.path.join(self._base, '..', '..', 'GUI', 'Views', 'index.xaml'))

    # Retourne la racine GUI
    def gui_root(self):
        return os.path.normpath(os.path.join(self._base, '..', '..', 'GUI'))

    # Retourne le dossier Controls
    def controls_dir(self):
        return os.path.join(self.gui_root(), 'Controls')

    # Retourne windows.xaml
    def windows_xaml(self):
        return os.path.join(self.gui_root(), 'windows.xaml')

    # Retourne le chemin absolu d'une ressource XAML (Colors.xaml, Styles.xaml, etc)
    def resource_path(self, filename):
        return os.path.join(self.gui_root(), 'resources', filename)
