# -*- coding: utf-8 -*-
"""Page « Aperçu » : l'arborescence telle qu'elle sera écrite, avant de l'écrire.

L'aperçu n'est pas une courtoisie. C'est la règle du dépôt : un export doit
donner deux fois le même résultat, un renommage doit se relire avant d'être
appliqué. Ici, ce qui s'affiche est exactement ce que ``ArborescenceService``
va créer — même fonction, mêmes chemins.
"""
from __future__ import unicode_literals
import os

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    from lib.ui.base.BaseViewModel import BaseViewModel

try:
    from lib.services import ArborescenceService as arbo
except Exception:
    from services import ArborescenceService as arbo


class LigneVM(BaseViewModel):
    """Une ligne de l'arbre : son dessin, son nom, et ce qui l'alimente."""

    def __init__(self, dessin, nom, jeu=u'', existe=False):
        super(LigneVM, self).__init__()
        self.Dessin = dessin
        self.Nom = nom
        self.Jeu = jeu
        self.JeuVisible = bool(jeu)
        # Un dossier déjà là n'est pas une erreur : on le dit, et on n'y
        # touchera pas. C'est ce qui rend l'outil rejouable sur un dossier
        # en cours de montage.
        self.Existe = bool(existe)


class ApercuPageVM(BaseViewModel):
    def __init__(self):
        super(ApercuPageVM, self).__init__()
        self.Lignes = []
        self._racine = u''
        self._retenues = []

    def rafraichir(self, racine, retenues):
        """Recalcule l'arbre. ``retenues`` : des ``PieceVM`` cochés."""
        self._racine = racine or u''
        self._retenues = list(retenues or [])
        self.Lignes = list(self._lignes())
        self.notify_property('Lignes')
        self.notify_property('Resume')
        self.NotifierEtat()

    def NotifierEtat(self):
        self.notify_property('PeutGenerer')
        self.notify_property('Avertissement')
        self.notify_property('AvertissementVisible')

    def _lignes(self):
        if not self._racine:
            return
        yield LigneVM(u'', self._racine, existe=os.path.isdir(self._racine))
        dernier = len(self._retenues) - 1
        for index, vm in enumerate(self._retenues):
            dessin = u'└──' if index == dernier else u'├──'
            chemin = os.path.join(self._racine,
                                  arbo.nom_dossier(vm.piece()))
            yield LigneVM(dessin, arbo.nom_dossier(vm.piece()),
                          jeu=vm.JeuRetenu, existe=os.path.isdir(chemin))

    def chemins(self):
        return arbo.chemins(self._racine,
                            [vm.piece() for vm in self._retenues])

    @property
    def Resume(self):
        if not self._racine:
            return u'Choisir un dossier de destination.'
        if not self._retenues:
            return u'Aucune pièce retenue.'
        return u'{0} dossier(s) à créer dans {1}'.format(
            len(self._retenues), os.path.dirname(self._racine) or u'…')

    @property
    def PeutGenerer(self):
        return bool(self._racine and self._retenues)

    @property
    def Avertissement(self):
        """Ce qui empêche de générer, dit avant le clic plutôt qu'après."""
        if not self._racine:
            return u'Pas de dossier de destination : onglet Dossier.'
        if not self._retenues:
            return u'Aucune pièce cochée : onglet Pièces.'
        return u''

    @property
    def AvertissementVisible(self):
        return bool(self.Avertissement)
