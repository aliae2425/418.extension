# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Renommer\nvues"
__doc__ = "Renomme les vues sélectionnées avec préfixe/suffixe/rechercher-remplacer."
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
from lib.services.RenameViewsService import RenameViewsService
from core.selection import get_selected_views, all_views


def _type_label(view):
    try:
        return unicode(view.ViewType)
    except Exception:
        try:
            return str(view.ViewType)
        except Exception:
            return u''


if __name__ == '__main__':
    vues = all_views(doc) if doc is not None else []
    views_par_id = {}
    descripteurs = []
    for v in vues:
        views_par_id[v.Id] = v
        descripteurs.append((v.Id, v.Name, _type_label(v)))

    ids_courants = [v.Id for v in (get_selected_views(uidoc) if uidoc is not None else [])]

    service = RenameViewsService(doc)
    vm = MainViewModel(doc=doc, uidoc=uidoc, service=service)
    vm.charger(descripteurs, ids_courants)

    view = MainWindowView(vm, views_par_id)
    view.show()
