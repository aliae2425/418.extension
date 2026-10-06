# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Feuilles"
__doc__ = ("SCAFFOLD — ossature d'une future gestion des feuilles (nommage, "
           "tri, duplication). La fenêtre s'ouvre, mais aucune logique métier "
           "n'est encore branchée.")
__author__ = 'Aliae'
__min_revit_ver__ = 2026
__beta__ = True

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
