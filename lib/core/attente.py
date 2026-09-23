# -*- coding: utf-8 -*-
"""Ce que dit la bulle pendant que le modèle réfléchit.

Une boucle d'outils enchaîne deux ou trois allers-retours de vingt secondes :
« réflexion… » figé pendant une minute donne l'impression que c'est planté.
D'où des phrases qui tournent, et un chronomètre qui prouve que ça avance.

Logique pure (aucun WPF, aucun Revit) : le VM n'en fait qu'assembler le texte.
"""
from __future__ import unicode_literals
import random

# Toutes du même moule : première personne, présent, points de suspension.
# Elles doivent rester courtes — la bulle fait 340 px, et une blague qu'on
# doit lire sur deux lignes n'en est plus une.
PHRASES = (
    'je cherche le nord…',
    'je compte les niveaux sur mes doigts…',
    'je convertis les pieds en mètres…',
    'je déplie les plans…',
    'je cherche la vue qui n\'est pas une feuille…',
    'je contourne un mur-rideau…',
    'je débusque une pièce non placée…',
    'je relis la légende…',
    'je demande à la maquette, poliment…',
    'je regarde qui a oublié de synchroniser…',
    'je cherche le paramètre partagé…',
    'je referme les avertissements un par un…',
    'je remets le gabarit de vue…',
    'je pense en unités internes…',
    'je retrouve le calque du fond de plan…',
    'je purge les familles que personne n\'utilise…',
)

# Une seule phrase pendant deux minutes lasse ; en changer chaque seconde
# donne le tournis. Cinq secondes, c'est le temps de la lire une fois.
TOURNE = 5


def autre(precedente=None):
    """Une phrase au hasard, jamais celle qu'on vient d'afficher."""
    choix = [phrase for phrase in PHRASES if phrase != precedente]
    return random.choice(choix or list(PHRASES))


def duree(secondes):
    """Durée lisible : « 8 s », « 1 min 12 s »."""
    secondes = int(secondes or 0)
    if secondes < 60:
        return '{0} s'.format(secondes)
    return '{0} min {1:02d} s'.format(secondes // 60, secondes % 60)


def libelle(phrase, secondes=0):
    """Phrase + chronomètre. Avant la première seconde, la phrase seule."""
    if not secondes or secondes <= 0:
        return phrase
    return '{0}  ·  {1}'.format(phrase, duree(secondes))
