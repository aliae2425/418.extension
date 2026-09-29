# -*- coding: utf-8 -*-
"""Le registre des outils Revit : une déclaration, trois usages.

Le serveur vendorisé posait un ``@api.route`` par outil, et 418 tenait en
face un catalogue écrit à la main — nom, chemin, schéma, description. Deux
listes à garder d'accord, et elles ont divergé deux fois : une route renommée
sans le catalogue (le chat a perdu TOUS ses outils sur un 404 muet), un
paramètre deviné de travers (``list_families`` filtre sur le nom, pas sur la
catégorie).

Ici un outil se déclare **une fois**, avec son schéma, et cette déclaration
sert à la fois :

- au routage — une seule route ``/418/outil/<nom>`` qui dispatche ;
- au catalogue — ``/418/outils/`` le sert au chat, qui ne l'écrit plus ;
- à la doctrine — ``ecrit`` et ``irreversible`` pilotent les garde-fous.

Logique pure : ce module ne connaît ni Revit ni pyRevit, il ne fait que
tenir le dictionnaire. Testable hors Revit.
"""
from __future__ import unicode_literals

# nom → Outil. Peuplé par le décorateur à l'import des modules d'outils.
OUTILS = {}

# Ce dont un outil a besoin, déduit de sa signature déclarée. pyRevit fournit
# ``doc``, ``uidoc`` et ``request`` selon ce que le gestionnaire demande ; ici
# on l'annonce, c'est le routeur qui sert.
CONTEXTES = ('doc', 'uidoc', 'request')


class Outil(object):
    """Un outil : ce qu'il fait, ce qu'il prend, ce qu'il casse."""

    def __init__(self, nom, description, fonction, proprietes=None,
                 requis=None, ecrit=False, irreversible=False, besoins=()):
        self.nom = nom
        self.description = description
        self.fonction = fonction
        self.proprietes = proprietes or {}
        self.requis = tuple(requis or ())
        # Trois familles, et la différence n'est pas cosmétique : lecture,
        # écriture annulable au Ctrl+Z, et irréversible.
        self.ecrit = bool(ecrit) or bool(irreversible)
        self.irreversible = bool(irreversible)
        self.besoins = tuple(besoins)

    @property
    def schema(self):
        """Schéma JSON des arguments, tel que l'attend un fournisseur."""
        schema = {'type': 'object', 'properties': self.proprietes,
                  'additionalProperties': False}
        if self.requis:
            schema['required'] = list(self.requis)
        return schema

    def json(self):
        """La forme servie par ``/418/outils/`` et relue par le chat."""
        return {'nom': self.nom, 'description': self.description,
                'parametres': self.schema, 'ecrit': self.ecrit,
                'irreversible': self.irreversible}


def outil(nom, description, proprietes=None, requis=None, ecrit=False,
          irreversible=False, besoins=('doc',)):
    """Déclare un outil. ``besoins`` dit ce que le routeur doit lui passer.

    Le nom est celui que le modèle appellera : on le préfixe ``revit_`` une
    seule fois, ici, pour qu'aucun module d'outils n'ait à y penser.
    """
    def decorateur(fonction):
        complet = nom if nom.startswith('revit_') else 'revit_' + nom
        if complet in OUTILS:
            raise ValueError('outil déclaré deux fois : ' + complet)
        for besoin in besoins:
            if besoin not in CONTEXTES:
                raise ValueError('besoin inconnu : {0}'.format(besoin))
        OUTILS[complet] = Outil(complet, description, fonction, proprietes,
                                requis, ecrit, irreversible, besoins)
        return fonction
    return decorateur


def catalogue():
    """Tous les outils, triés — lecture d'abord, irréversible en dernier.

    L'ordre compte : c'est celui que le modèle lit, et il fait office de
    hiérarchie implicite entre « regarde » et « ne touche pas sans qu'on te
    le demande ».
    """
    return [OUTILS[nom].json()
            for nom in sorted(OUTILS, key=lambda n: (OUTILS[n].ecrit,
                                                     OUTILS[n].irreversible,
                                                     n))]


def irreversibles():
    return tuple(sorted(nom for nom, o in OUTILS.items() if o.irreversible))


def vider():
    """Pour les tests seulement : un registre global se pollue d'un test à l'autre."""
    OUTILS.clear()
