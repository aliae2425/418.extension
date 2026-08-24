# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

# _lib_dir = 418.extension/lib/
_lib_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# _ext_dir = 418.extension/ (racine de l'extension)
_ext_dir = os.path.dirname(_lib_dir)


class AppPaths(object):
    def resources_dir(self):
        return os.path.join(_lib_dir, 'ui', 'GUI', 'resources')

    def data_dir(self):
        # Dossier de données commun à TOUTES les features (persistance des
        # réglages, caches, etc.) : 418.extension/data/. Créé si absent.
        d = os.path.join(_ext_dir, 'data')
        try:
            if not os.path.isdir(d):
                os.makedirs(d)
        except Exception:
            pass
        return d

    def resource_path(self, filename):
        return os.path.join(self.resources_dir(), filename)

    def logo_path(self, dark=False):
        # Retourne le logo sombre si demandé et présent, sinon le logo clair.
        if dark:
            sombre = self.resource_path('logo.dark.png')
            if os.path.exists(sombre):
                return sombre
        return self.resource_path('logo.png')
