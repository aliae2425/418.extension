# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "PC"
__doc__ = ("SCAFFOLD — ossature du dossier de permis de construire. La "
           "fenêtre s'ouvre, mais aucune logique métier n'est encore "
           "branchée.")
__author__ = 'Aliae'
__min_revit_ver__ = 2026
__beta__ = True

try:
    uidoc = __revit__.ActiveUIDocument  # type: ignore # noqa: F821
    doc = uidoc.Document
except Exception:
    uidoc = doc = None

from lib.viewmodels.MainViewModel import MainViewModel
from lib.views.MainWindowView import MainWindowView

if __name__ == '__main__':
    vm = MainViewModel(doc=doc, uidoc=uidoc)
    view = MainWindowView(vm)
    view.show()
