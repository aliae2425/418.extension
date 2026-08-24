# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "À propos"
__doc__ = "Informations sur l'extension 418 (version, dépôt, licence)."
__author__ = 'Aliae'
__min_revit_ver__ = 2026

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

from viewmodels.AboutViewModel import AboutViewModel
from views.AboutWindowView import AboutWindowView

if __name__ == '__main__':
    vm = AboutViewModel()
    view = AboutWindowView(vm)
    view.show()
