# -*- coding: utf-8 -*-
"""Script de démarrage de l'extension 418 (exécuté par pyRevit au lancement).

Deux rôles :

- enregistrer les panneaux ancrables — l'API Revit n'accepte
  ``RegisterDockablePane`` que pendant OnStartup, impossible de le faire
  paresseusement depuis un bouton ;
- démarrer le serveur MCP vendorisé (``vendor/mcp-server-for-revit``).
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

# --- Outils Revit de 418 ---------------------------------------------------
# Remplace vendor/mcp-server-for-revit, supprimé : le miroir git subtree
# interdisait d'éditer ce qu'on utilisait tous les jours. Enregistrer une
# route ne fait qu'inscrire une fonction dans le routeur global de pyRevit —
# aucune socket, aucun fil, aucun WPF.
#
# 418 ne DÉMARRE aucun serveur : le chat se branche sur celui de pyRevit
# (port découvert, cf. lib/core/routes418.py). L'essai d'en lancer un a coûté
# deux plantages de Revit. Ne rien relancer ici sans relire ce module.
try:
    from rvt import enregistrer as _enregistrer_418
    if _enregistrer_418() is not None:
        print('418: outils Revit enregistrés')
except Exception as e:
    print('418: outils Revit non enregistrés: {}'.format(e))
