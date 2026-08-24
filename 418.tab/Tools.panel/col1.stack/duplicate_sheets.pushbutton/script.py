# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Dupliquer\nfeuilles"
__doc__ = "Duplique les feuilles sélectionnées (vues, légendes, nomenclatures, éléments) avec renommage."
__author__ = 'Aliae'
__min_revit_ver__ = 2026

try:
    uidoc = __revit__.ActiveUIDocument  # type: ignore
    doc = __revit__.ActiveUIDocument.Document  # type: ignore
except Exception:
    uidoc = None
    doc = None

# Racine d'import unique : <bouton>/lib. Déclarée ici explicitement plutôt que
# de dépendre de la convention pyRevit sur les dossiers `lib` de bundle — ainsi
# modules et tests utilisent la MÊME forme d'import (`from services.X import Y`),
# ce qui évite qu'un même fichier soit chargé sous deux noms de module
# distincts (et donc avec deux états séparés — cf. lib/core/UserConfig.py).
import os as _os
import sys as _sys
_LIB = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'lib')
if _LIB not in _sys.path:
    _sys.path.insert(0, _LIB)

from viewmodels.MainViewModel import MainViewModel
from views.MainWindowView import MainWindowView
from services.DuplicationSheetsService import DuplicationSheetsService
from core.selection import get_selected_sheets, all_sheets

if __name__ == '__main__':
    sheets = all_sheets(doc) if doc is not None else []
    sheets_par_id = {}
    descripteurs = []
    for s in sheets:
        sheets_par_id[s.Id] = s
        descripteurs.append((s.Id, s.SheetNumber, s.Name))

    ids_courants = [s.Id for s in (get_selected_sheets(uidoc) if uidoc is not None else [])]

    service = DuplicationSheetsService(doc)
    vm = MainViewModel(doc=doc, uidoc=uidoc, service=service)
    vm.charger(descripteurs, ids_courants)

    view = MainWindowView(vm, sheets_par_id)
    view.show()
