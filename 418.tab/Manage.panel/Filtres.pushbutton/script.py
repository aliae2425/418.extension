# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Filtres"
__doc__ = ("Gestion des filtres de vue par famille : audit, filtres des "
           "coupes, filtres des plans de repérage.")
__author__ = 'Aliae'
__min_revit_ver__ = 2026

try:
    doc = __revit__.ActiveUIDocument.Document  # type: ignore
except Exception:
    doc = None

from lib.services.FiltresService import FiltresService
from lib.viewmodels.MainViewModel import MainViewModel
from lib.views.MainWindowView import MainWindowView

if __name__ == '__main__':
    vm = MainViewModel(service=FiltresService(doc))
    vm.charger()
    MainWindowView(vm).show()
