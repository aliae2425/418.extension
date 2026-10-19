# -*- coding: utf-8 -*-
# Ordre d'impression des feuilles : deux fonctions pures, sans Revit ni WPF.
#
# C'est le SEUL endroit où se décide l'ordre. Le ViewModel l'utilise pour
# l'affichage, l'orchestrateur pour l'export : les deux doivent voir le même,
# sinon ce qu'on relit à l'écran n'est pas ce qui sort du PDF.

from __future__ import unicode_literals

# `cle_naturelle` vit dans le socle (lib/core/selection.py) et y est déjà
# éprouvée sur des numéros de feuille. Double forme d'import (régime pyRevit /
# régime tests standalone), cf. convention du projet. Le dernier repli garde
# un tri de chaînes — dégradé mais jamais une exception à l'import.
try:
    from core.selection import cle_naturelle
except Exception:
    try:
        from lib.core.selection import cle_naturelle
    except Exception:
        def cle_naturelle(texte):
            return [texte or u'']


def ordonner(items, reference, cle):
    """Ordonne `items` selon `reference`, une suite de numéros mémorisée.

    Ce qui ne figure pas dans `reference` passe APRÈS, en ordre NATUREL
    (`A9` avant `A10`, là où un tri de chaînes met `A10` devant). Deux
    conséquences voulues :

    - `reference` vide ou `None` -> tri naturel pur, le défaut de l'outil ;
    - une feuille créée depuis la dernière réorganisation arrive à la fin,
      jamais insérée au milieu d'un ordre que l'utilisateur a validé.

    `cle(item)` rend le numéro de feuille.
    """
    rang = {}
    for position, numero in enumerate(reference or ()):
        rang.setdefault(numero, position)
    apres = len(rang)

    def _tri(item):
        numero = cle(item) or u''
        return (rang.get(numero, apres), cle_naturelle(numero))

    return sorted(items, key=_tri)


def reposer(complet, sous_ensemble, cle):
    """Repose `sous_ensemble` (réordonné) sur les places qu'occupaient ses
    éléments dans `complet`, sans déplacer les autres.

    C'est ce qui permet de réorganiser une liste FILTRÉE sans bousculer les
    feuilles masquées : seules les positions déjà occupées par le
    sous-ensemble sont redistribuées, dans son nouvel ordre.
    """
    voulus = set(cle(x) for x in sous_ensemble)
    restants = iter(sous_ensemble)
    sortie = []
    for item in complet:
        if cle(item) in voulus:
            try:
                sortie.append(next(restants))
            except StopIteration:
                # Numéro en double dans `complet` : plus de places que
                # d'éléments à reposer. On garde l'original plutôt que de
                # perdre une ligne.
                sortie.append(item)
        else:
            sortie.append(item)
    return sortie
