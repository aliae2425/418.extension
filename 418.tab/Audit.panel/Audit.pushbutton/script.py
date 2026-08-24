# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Audit"
__doc__ = "Analyse et rapport sur la santé du modèle Revit."
__author__ = 'Aliae'
__min_revit_ver__ = 2026

try:
    doc = __revit__.ActiveUIDocument.Document  # type: ignore
except Exception:
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

if __name__ == '__main__':
    vm = MainViewModel(doc=doc)
    view = MainWindowView(vm)
    view.show()
