# -*- coding: utf-8 -*-
"""Script de démarrage de l'extension 418 (exécuté par pyRevit au lancement).

Seul rôle actuel : enregistrer les panneaux ancrables. L'API Revit n'accepte
``RegisterDockablePane`` que pendant OnStartup — impossible de le faire
paresseusement depuis un bouton, d'où ce fichier.
"""
from __future__ import unicode_literals
import os
import sys

# pyRevit met déjà 418.extension/lib sur sys.path pour les scripts de bouton ;
# on le garantit ici, le contexte de démarrage n'offrant pas la même certitude.
_LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib')
if _LIB not in sys.path:
    sys.path.append(_LIB)

from pyrevit import forms

from ui.OpenArchiPanel import OpenArchiPanel

if not forms.is_registered_dockable_panel(OpenArchiPanel):
    try:
        forms.register_dockable_panel(OpenArchiPanel, default_visible=False)
    except Exception as e:
        # Un « Reload » pyRevit rejoue ce script hors OnStartup : Revit refuse
        # alors l'enregistrement. Un redémarrage de Revit suffit.
        print('OpenArchi: enregistrement du panneau impossible '
              '(redémarrez Revit): {}'.format(e))
