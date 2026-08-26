# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Matériaux"
__doc__ = "Gestion et édition des matériaux du modèle."
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
from core.selection import all_materials


def _classe(materiau):
    """Classe du matériau (« Béton », « Bois »...), vide si non renseignée."""
    try:
        return materiau.MaterialClass or u''
    except Exception:
        return u''


if __name__ == '__main__':
    materiaux = all_materials(doc) if doc is not None else []
    materiaux_par_id = {}
    descripteurs = []
    for m in materiaux:
        materiaux_par_id[m.Id] = m
        descripteurs.append((m.Id, _classe(m), m.Name))

    vm = MainViewModel(doc=doc, uidoc=uidoc)
    vm.charger(descripteurs, [])

    view = MainWindowView(vm, materiaux_par_id)
    view.show()
