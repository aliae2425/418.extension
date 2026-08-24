# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Dupliquer\nvues"
__doc__ = "Duplique les vues sélectionnées (nombre de copies + mode de duplication)."
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
from services.ViewsDuplicationService import ViewsDuplicationService
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

    service = ViewsDuplicationService(doc)
    vm = MainViewModel(doc=doc, uidoc=uidoc, service=service)
    vm.charger(descripteurs, ids_courants)

    view = MainWindowView(vm, views_par_id, uidoc)
    view.show()
