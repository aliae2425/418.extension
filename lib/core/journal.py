# -*- coding: utf-8 -*-
"""Journal de débogage, écrit dans ``data/418.log``.

Le panneau ancrable ne dispose d'aucune fenêtre de sortie pyRevit : un
``print`` s'y perd. Tout ce qu'on veut pouvoir relire après coup passe donc
par ici, et le fichier se donne tel quel.

Logique pure (aucun import Revit ni WPF) pour rester testable hors Revit.
"""
from __future__ import unicode_literals
import logging
import os

try:
    from core.AppPaths import AppPaths
except Exception:
    try:
        from lib.core.AppPaths import AppPaths
    except Exception:
        AppPaths = None

FICHIER = '418.log'
_RACINE = 'openarchi'
_configure = []


def chemin():
    """Chemin du journal, ``''`` si aucun dossier de données n'est joignable."""
    if AppPaths is None:
        return ''
    try:
        return os.path.join(AppPaths().data_dir(), FICHIER)
    except Exception:
        return ''


def journal(nom):
    """Logger nommé ``openarchi.<nom>``, prêt à écrire."""
    _installer()
    return logging.getLogger('{0}.{1}'.format(_RACINE, nom))


def lire(lignes=40):
    """Les dernières lignes du journal, pour les recracher dans le chat."""
    fichier = chemin()
    if not fichier or not os.path.exists(fichier):
        return ''
    try:
        with open(fichier, 'rb') as ouvert:
            contenu = ouvert.read().decode('utf-8', 'replace')
    except Exception as e:
        return 'journal illisible : {0}'.format(e)
    return '\n'.join(contenu.splitlines()[-lignes:])


def vider():
    # Le handler tient le fichier ouvert : sous Windows, le supprimer sans le
    # fermer échoue en silence. FileHandler rouvre de lui-même au prochain
    # enregistrement, il n'y a rien à réinstaller.
    for handler in list(logging.getLogger(_RACINE).handlers):
        try:
            handler.close()
        except Exception:
            pass
    fichier = chemin()
    if fichier and os.path.exists(fichier):
        try:
            os.remove(fichier)
        except Exception:
            pass


def flux():
    """Fichier ouvert en ajout, à donner comme sortie à un sous-processus.

    ``None`` si le journal n'est pas joignable — l'appelant retombe alors sur
    son comportement habituel.
    """
    fichier = chemin()
    if not fichier:
        return None
    try:
        return open(fichier, 'ab')
    except Exception:
        return None


def _installer():
    # ponytail: un seul fichier, jamais tourné. Passer en
    # RotatingFileHandler le jour où il devient gênant.
    if _configure:
        return
    _configure.append(True)
    racine = logging.getLogger(_RACINE)
    racine.setLevel(logging.DEBUG)
    # Le journal se suffit : sans ça, pyRevit reçoit aussi chaque ligne.
    racine.propagate = False
    fichier = chemin()
    if not fichier:
        return
    try:
        sortie = logging.FileHandler(fichier, encoding='utf-8')
    except Exception:
        return
    sortie.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)-5s %(name)s | %(message)s',
        '%H:%M:%S'))
    racine.addHandler(sortie)
