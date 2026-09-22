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

# --- Serveur MCP (upstream vendorisé, NE JAMAIS éditer vendor/) -------------
# Le dossier porte un tiret : non importable en package, d'où le sys.path.
# On exécute leur startup.py tel quel plutôt que de recopier leur liste de
# routes — un `git subtree pull` ne doit rien casser ici.
_MCP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    'vendor', 'mcp-server-for-revit')
if _MCP not in sys.path:
    sys.path.append(_MCP)

try:
    with open(os.path.join(_MCP, 'startup.py')) as _f:
        exec(_f.read(), {'__name__': 'revit_mcp_startup'})
except Exception as e:
    print('418: serveur MCP non démarré: {}'.format(e))
