# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "À propos"
__doc__ = "Informations sur l'extension 418 (version, dépôt, licence)."
__author__ = 'Aliae'
__min_revit_ver__ = 2026

from lib.viewmodels.AboutViewModel import AboutViewModel
from lib.views.AboutWindowView import AboutWindowView

if __name__ == '__main__':
    vm = AboutViewModel()
    view = AboutWindowView(vm)
    view.show()
