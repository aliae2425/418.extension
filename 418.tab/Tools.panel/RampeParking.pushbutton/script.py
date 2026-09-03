# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

__title__ = "Rampe\nparking"
__doc__ = ("Lit les contraintes d'une rampe de parking dans la maquette et "
           "les envoie au calculateur NF P91-100 de la toolbox.")
__author__ = 'Aliae'
__min_revit_ver__ = 2026

try:
    uidoc = __revit__.ActiveUIDocument  # type: ignore
    doc = __revit__.ActiveUIDocument.Document  # type: ignore
except Exception:
    uidoc = None
    doc = None

try:
    from Autodesk.Revit.UI import TaskDialog
except Exception:
    TaskDialog = None

from lib.services import contraintes as contraintes_module
from lib.viewmodels.MainViewModel import MainViewModel
from lib.views.MainWindowView import MainWindowView
from core.AppPaths import AppPaths


def _selection():
    """Éléments sélectionnés dans l'UI Revit.

    `core.selection` ne propose que des filtres typés (feuilles, vues,
    matériaux) : ici on veut la sélection brute, la reconnaissance du type se
    fait dans `contraintes.lire`.
    """
    if uidoc is None or doc is None:
        return []
    return [doc.GetElement(eid) for eid in uidoc.Selection.GetElementIds()]


if __name__ == '__main__':
    elements = _selection()
    if not elements and TaskDialog is not None:
        TaskDialog.Show('Rampe parking', contraintes_module.AIDE_SELECTION)
    else:
        vm = MainViewModel(contraintes_module.lire(elements, doc))
        # WebView2 a besoin d'un dossier inscriptible pour son cache ; le
        # dossier `data/` de l'extension est déjà l'endroit prévu pour ça.
        dossier = os.path.join(AppPaths().data_dir(), 'webview2')
        MainWindowView(vm, dossier).show()
