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

from lib.viewmodels.MainViewModel import MainViewModel
from lib.views.MainWindowView import MainWindowView
from lib.services.DuplicationSheetsService import DuplicationSheetsService
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
