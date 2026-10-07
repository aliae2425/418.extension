# -*- coding: utf-8 -*-
"""L'arborescence d'un dossier d'urbanisme : la calculer, puis l'écrire.

Deux fonctions, et c'est volontaire : ``chemins()`` est PURE — elle rend une
liste de chemins sans toucher au disque, donc elle se teste et surtout elle
s'affiche. C'est l'aperçu avant validation que l'outil doit à l'architecte.
``creer()`` écrit, et ne fait rien d'autre que ce que l'aperçu annonçait.

Jamais d'écrasement : un dossier déjà là est laissé tel quel et compté
comme tel. Relancer l'outil sur un dossier en cours ne doit rien perdre.

Logique pure côté calcul (aucun Revit, aucun WPF) : testable hors Revit.
"""
from __future__ import unicode_literals
import os

try:
    from core.sanitize import sanitize
except Exception:
    from lib.core.sanitize import sanitize


# Le nom d'un dossier de pièce : « PC3 - Plan en coupe du terrain ». Le code
# en tête, parce que c'est lui que l'instructeur lit en premier et qu'il
# donne l'ordre du CERFA au tri alphabétique du disque.
SEPARATEUR = ' - '


def nom_dossier(piece):
    """Nom du dossier d'une pièce, assaini pour le système de fichiers."""
    return sanitize(u'{0}{1}{2}'.format(piece.code, SEPARATEUR, piece.libelle))


def chemins(racine, pieces):
    """``(racine, pièces) -> [chemins]``. Ne touche à rien.

    La racine vient en tête : c'est elle qu'il faudra créer d'abord, et son
    absence de la liste la rendrait invisible dans l'aperçu.
    """
    if not racine:
        return []
    sortie = [racine]
    for piece in pieces or ():
        sortie.append(os.path.join(racine, nom_dossier(piece)))
    return sortie


def creer(racine, pieces):
    """Écrit l'arborescence. Rend ``(créés, déjà là, échecs)``.

    ``échecs`` porte des couples ``(chemin, message)`` — un droit refusé, un
    lecteur réseau tombé. On ne lève pas : l'architecte doit savoir ce qui est
    passé ET ce qui a manqué, pas perdre les deux sur la première erreur.
    """
    crees, existants, echecs = [], [], []
    for chemin in chemins(racine, pieces):
        if os.path.isdir(chemin):
            existants.append(chemin)
            continue
        try:
            os.makedirs(chemin)
            crees.append(chemin)
        except OSError as e:
            # Course bénigne : un autre processus vient de le créer.
            if os.path.isdir(chemin):
                existants.append(chemin)
            else:
                echecs.append((chemin, u'{0}'.format(e)))
    return crees, existants, echecs


def resume(crees, existants, echecs):
    """Une phrase pour la barre d'état. Dit ce qui a manqué, jamais « OK »."""
    morceaux = []
    if crees:
        morceaux.append(u'{0} dossier(s) créé(s)'.format(len(crees)))
    if existants:
        morceaux.append(u'{0} déjà là'.format(len(existants)))
    if echecs:
        morceaux.append(u'{0} en échec — {1}'.format(
            len(echecs), echecs[0][1]))
    return u', '.join(morceaux) if morceaux else u'Rien à créer.'
