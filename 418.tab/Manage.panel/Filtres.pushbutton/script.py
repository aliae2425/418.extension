# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Filtres"
__doc__ = ("Gestion des filtres de vue : audit du modèle et repérage des "
           "coupes sur les plans de repérage.")
__author__ = 'Aliae'
__min_revit_ver__ = 2026

try:
    uidoc = __revit__.ActiveUIDocument  # type: ignore
    doc = uidoc.Document
except Exception:
    uidoc = None
    doc = None

from lib.services.FiltresService import FiltresService
from lib.viewmodels.MainViewModel import MainViewModel
from lib.views.MainWindowView import MainWindowView


def _activer(vue_id):
    """Active la vue demandée par « Aller au plan ».

    Ici et pas dans la fenêtre : changer de vue demande que la modale soit
    refermée, et l'`ActiveUIDocument` n'a rien à faire dans une couche vue.
    """
    if vue_id is None or uidoc is None or doc is None:
        return
    try:
        uidoc.ActiveView = doc.GetElement(vue_id)
    except Exception as erreur:
        print(u'Impossible d\'activer le plan ({}).'.format(erreur))


if __name__ == '__main__':
    vm = MainViewModel(service=FiltresService(doc))
    vm.charger()
    fenetre = MainWindowView(vm)
    fenetre.show()
    _activer(fenetre.plan_a_activer())
