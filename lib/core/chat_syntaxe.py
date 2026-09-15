# -*- coding: utf-8 -*-
"""Syntaxe des messages du chat : commandes /x et références #y.

Logique pure (aucun import Revit ni WPF) pour rester testable hors Revit.
"""
from __future__ import unicode_literals
import re

# Une commande n'est reconnue qu'EN TÊTE de message : une barre oblique au
# milieu d'une phrase (« 1/2 », un chemin, une URL) n'en est pas une.
_RE_COMMANDE = re.compile(r'^/([A-Za-z][\w-]*)\s*(.*)$', re.DOTALL)

# #{Nom avec espaces} pour les noms composés, #Nom pour le cas courant.
_RE_REFERENCE = re.compile(r'#(?:\{([^}]*)\}|([\w.\-]+))')


class Analyse(object):
    """Résultat de l'analyse d'un message saisi."""

    def __init__(self, texte, commande=None, arguments='', references=None):
        self.texte = texte
        self.commande = commande
        self.arguments = arguments
        self.references = references or []

    @property
    def est_commande(self):
        return self.commande is not None


def analyser(texte):
    texte = (texte or '').strip()
    commande = None
    arguments = ''
    trouve = _RE_COMMANDE.match(texte)
    if trouve:
        commande = trouve.group(1).lower()
        arguments = trouve.group(2).strip()

    references = []
    for accolades, nu in _RE_REFERENCE.findall(texte):
        nom = (accolades or nu).strip()
        if nom and nom not in references:
            references.append(nom)

    return Analyse(texte, commande, arguments, references)
