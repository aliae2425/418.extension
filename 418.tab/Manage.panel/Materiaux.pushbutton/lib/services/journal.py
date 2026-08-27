# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import io
import os
import time

# Journal de diagnostic de l'outil Matériaux, sur DEUX sorties :
#   - la fenêtre de sortie pyRevit (lecture immédiate)
#   - data/materiaux.log (relisible après coup, y compris par un agent —
#     `filelogging` de pyRevit est à false et n'écrit rien de son côté)
# Hors Revit (tests standalone) : no-op complet.
#
# `info` et pas `debug` : visible sans lancer le bouton en mode debug.
#
# ponytail: réouverture du fichier à chaque ligne et rotation à l'ouverture
# de l'outil. Volume attendu : quelques centaines de lignes par session. Si
# ça devient chaud, garder un handle ouvert.
try:
    from pyrevit import script as _script
    _LOGGER = _script.get_logger()
except Exception:
    _LOGGER = None

try:
    from core.AppPaths import AppPaths
except Exception:
    try:
        from lib.core.AppPaths import AppPaths
    except Exception:
        AppPaths = None


def chemin():
    """`418.extension/data/materiaux.log`, ou None si data/ injoignable."""
    if AppPaths is None:
        return None
    try:
        return os.path.join(AppPaths().data_dir(), 'materiaux.log')
    except Exception:
        return None


# Fichier écrit UNIQUEMENT sous Revit : sinon les tests standalone écrasent
# le journal de la dernière session à déboguer.
_FICHIER = chemin() if _LOGGER is not None else None


def nouvelle_session(titre):
    """Vide le fichier et l'entête. Appelé une fois par ouverture d'outil :
    sans ça, on relit le journal de la session précédente et on débogue un
    symptôme qui n'existe plus."""
    if _FICHIER:
        try:
            with io.open(_FICHIER, 'w', encoding='utf-8') as flux:
                flux.write(u'=== %s · %s ===\n'
                           % (titre, time.strftime('%Y-%m-%d %H:%M:%S')))
        except Exception:
            pass
    log(u'session : {}', titre)


def log(gabarit, *args):
    """`log(u'{} porteurs', n)` -> « [Matériaux] 3 porteurs »."""
    try:
        message = gabarit.format(*args) if args else gabarit
    except Exception:
        message = gabarit
    if _LOGGER is not None:
        try:
            _LOGGER.info(u'[Matériaux] %s', message)
        except Exception:
            pass
    if _FICHIER:
        try:
            with io.open(_FICHIER, 'a', encoding='utf-8') as flux:
                flux.write(u'%s %s\n' % (time.strftime('%H:%M:%S'), message))
        except Exception:
            pass


def nom(element):
    """Nom lisible d'un élément, pour les lignes de log."""
    try:
        return u'%s (%s)' % (element.Name, element.Id)
    except Exception:
        return u'<?>'
