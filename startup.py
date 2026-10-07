# -*- coding: utf-8 -*-
"""Script de démarrage de l'extension 418 (exécuté par pyRevit au lancement).

Deux rôles :

- enregistrer le volet ancrable OpenArchi — l'API Revit n'accepte
  ``RegisterDockablePane`` que pendant OnStartup, impossible de le faire
  paresseusement depuis un bouton ;
- poser les routes ``/418/``, qui donnent accès à la maquette.

**Aucune étape n'a le droit d'emporter les autres.** Ce script tourne hors de
toute fenêtre de sortie : une exception qui s'en échappe rend un code non nul,
pyRevit journalise « Startup script returned non-zero result » — et c'est tout
ce qu'on en saura. Le volet manque, les routes avec, et rien ne dit pourquoi.
D'où le journal en tête et une garde par étape : chacune tombe seule, et sa
trace se relit dans ``data/418.log``.

Le volet appartient au harnais, qui est en bêta. Or `is_beta` ne couvre que la
construction du ruban : pyRevit exécute ce script quoi qu'il arrive. D'où la
garde explicite sur `load_beta` — sans elle, « Load Beta Tools » décoché
laisserait quand même apparaître le volet. Les routes, elles, n'ouvrent
aucune fenêtre et servent aussi les clients HTTP extérieurs : elles ne sont
pas derrière le drapeau.
"""
from __future__ import unicode_literals
import os
import sys

# pyRevit met déjà 418.extension/lib sur sys.path pour les scripts de bouton ;
# on le garantit ici, le contexte de démarrage n'offrant pas la même certitude
# — et le journal lui-même en dépend, donc avant tout le reste.
_LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib')
if _LIB not in sys.path:
    sys.path.append(_LIB)

try:
    from core.journal import journal
    _log = journal('demarrage')
except Exception:                      # sans journal, au moins ne pas lever
    _log = None


def _etape(nom, travail):
    """Lance une étape en gardant sa trace. Ne lève JAMAIS.

    Un volet ancrable en moins vaut mieux qu'une extension qui ne démarre
    pas : c'est la différence entre une fonction absente et un code non nul
    qui emporte les routes avec lui.
    """
    try:
        resultat = travail()
    except Exception as e:
        if _log is not None:
            _log.exception('%s — échec', nom)
        else:
            # Dernier recours, et lui-même sous garde : un script de
            # démarrage n'a pas forcément de sortie branchée, et un `print`
            # qui lève dans un `except` emporte le script entier — c'est
            # exactement le piège qu'on essaie de désamorcer.
            try:
                print('418: {0} a échoué : {1}'.format(nom, e))
            except Exception:
                pass
        return None
    if _log is not None:
        _log.info('%s : %s', nom, resultat)
    return resultat


def _beta():
    """« Load Beta Tools » est-il coché dans les réglages pyRevit ?"""
    from pyrevit.userconfig import user_config
    return bool(user_config.core.load_beta)


def _volet():
    """Volet ancrable OpenArchi.

    C'est l'étape fragile : elle est la seule à toucher WPF, et elle exige
    un moteur IronPython — sous CPython, ``pyrevit.forms`` n'est qu'une
    doublure qui lève sur ``WPFPanel``.
    """
    from pyrevit import forms
    from ui.OpenArchiPanel import OpenArchiPanel
    if forms.is_registered_dockable_panel(OpenArchiPanel):
        return 'déjà enregistré'
    # Un « Reload » pyRevit rejoue ce script hors OnStartup : Revit refuse
    # alors l'enregistrement. Un redémarrage de Revit suffit.
    forms.register_dockable_panel(OpenArchiPanel, default_visible=False)
    return 'enregistré'


def _routes():
    """Les outils Revit de 418, servis sur ``routes.API('418')``.

    418 ne DÉMARRE aucun serveur : le chat se branche sur celui de pyRevit
    (port découvert, cf. lib/core/routes418.py). L'essai d'en lancer un a
    coûté deux plantages de Revit. Ne rien relancer ici sans relire ce
    module. Enregistrer une route ne fait qu'inscrire une fonction dans le
    routeur — aucune socket, aucun fil, aucun WPF.
    """
    from rvt import enregistrer
    return 'en place' if enregistrer() is not None else 'hors Revit'


if _log is not None:
    # La première ligne dit quel moteur exécute ce script. Sans elle, un
    # échec d'import de `pyrevit.forms` reste une énigme : la doublure
    # CPython et le vrai module IronPython portent le même nom.
    _log.info('démarrage 418 | %s', sys.version)

if _etape('réglages pyRevit', _beta):
    _etape('volet OpenArchi', _volet)
_etape('routes 418', _routes)
