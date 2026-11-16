# -*- coding: utf-8 -*-
"""Script de démarrage de l'extension 418 (exécuté par pyRevit au lancement).

Deux rôles :

- enregistrer les panneaux ancrables — l'API Revit n'accepte
  ``RegisterDockablePane`` que pendant OnStartup, impossible de le faire
  paresseusement depuis un bouton ;
- démarrer le serveur MCP vendorisé (``vendor/mcp-server-for-revit``).

Les deux appartiennent au harnais, qui est en bêta. Or `is_beta` ne couvre que
la construction du ruban : pyRevit exécute ce script quoi qu'il arrive. D'où la
garde explicite sur `load_beta` ci-dessous — sans elle, « Load Beta Tools »
décoché laisserait quand même tourner le serveur MCP.
"""
from __future__ import unicode_literals
import os
import sys

from pyrevit.userconfig import user_config

if user_config.core.load_beta:
    # pyRevit met déjà 418.extension/lib sur sys.path pour les scripts de
    # bouton ; on le garantit ici, le contexte de démarrage n'offrant pas la
    # même certitude.
    _LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib')
    if _LIB not in sys.path:
        sys.path.append(_LIB)

    from pyrevit import forms

    from ui.OpenArchiPanel import OpenArchiPanel

    if not forms.is_registered_dockable_panel(OpenArchiPanel):
        try:
            forms.register_dockable_panel(OpenArchiPanel, default_visible=False)
        except Exception as e:
            # Un « Reload » pyRevit rejoue ce script hors OnStartup : Revit
            # refuse alors l'enregistrement. Un redémarrage de Revit suffit.
            print('OpenArchi: enregistrement du panneau impossible '
                  '(redémarrez Revit): {}'.format(e))

    # --- Presse-papiers : panneau flottant + suivi de Ctrl+C ----------------
    # Tout passe par le journal : un print au démarrage ne se relit pas.
    from core.journal import journal as _journal
    _log_pp = _journal('presse_papiers')

    # Ctrl+C d'abord : un panneau qui ne se construit pas ne doit pas
    # empêcher l'historique de se remplir. Sans installer, demander() met en
    # file sans jamais lever l'ExternalEvent.
    try:
        from core.presse_papiers import installer as _installer_pp
        _log_pp.info('démarrage : Ctrl+C suivi = %s', _installer_pp(__revit__))
    except Exception:
        _log_pp.exception('démarrage : Ctrl+C non suivi')

    try:
        from ui.PressePapiersPanel import PressePapiersPanel
        if not forms.is_registered_dockable_panel(PressePapiersPanel):
            forms.register_dockable_panel(PressePapiersPanel,
                                          default_visible=False)
        _log_pp.info('démarrage : panneau enregistré')
    except Exception:
        # Un « Reload » pyRevit rejoue ce script hors OnStartup : Revit
        # refuse alors l'enregistrement. Un redémarrage de Revit suffit.
        _log_pp.exception('démarrage : panneau non enregistré')

    # --- Serveur MCP (upstream vendorisé, NE JAMAIS éditer vendor/) ---------
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

    # --- Routes propres à 418 ----------------------------------------------
    # Ce qui manque au serveur vendorisé s'ajoute sous notre propre API, jamais
    # dans vendor/ (miroir git subtree : toute édition part en conflit au
    # prochain pull). Enregistrer une route ne fait qu'inscrire une fonction
    # dans le routeur global — aucune socket, aucun fil, aucun WPF.
    try:
        from core.api418 import enregistrer as _enregistrer_418
        if _enregistrer_418() is not None:
            print('418: routes /418/ enregistrées')
    except Exception as e:
        print('418: routes propres non enregistrées: {}'.format(e))

# 418 ne DÉMARRE aucun serveur : le chat se branche sur celui de pyRevit
# (port découvert, cf. lib/core/routes418.py). L'essai d'en lancer un a coûté
# deux plantages de Revit. Ne rien relancer ici sans relire ce module.
