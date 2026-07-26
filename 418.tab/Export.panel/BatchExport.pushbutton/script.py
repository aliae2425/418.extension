# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Export"
__doc__ = "Export en lot PDF/DWG des feuilles et jeux de feuilles."
__author__ = 'Aliae'
__min_revit_ver__ = 2026

try:
    doc = __revit__.ActiveUIDocument.Document  # type: ignore
except Exception:
    doc = None

from lib.viewmodels.MainViewModel import MainViewModel
from lib.views.MainWindowView import MainWindowView

if __name__ == '__main__':
    vm = MainViewModel(doc=doc)
    view = MainWindowView(vm)
    view.show()
