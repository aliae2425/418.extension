# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Ligne cochable de la page Sélection, commune aux outils feuilles et vues.
# Remplace les 4 exemplaires quasi-identiques (SheetItemVM / ViewItemVM) qui
# ne différaient que par le nom de l'identifiant et celui de la colonne de
# gauche.

from ui.base.BaseViewModel import BaseViewModel


class SelectionItemVM(BaseViewModel):
    """Une ligne de la liste de sélection.

    `colonne_gauche` : identifiant (numéro de feuille) ou métadonnée (type de
    vue) selon l'outil. `est_identifiant` pilote uniquement le rendu — un
    numéro de feuille s'affiche en gras, un type de vue en texte secondaire
    plus petit (cf. le DataTrigger de SelectionPage.xaml).
    """

    def __init__(self, item_id, colonne_gauche, nom, is_selected=False,
                 on_toggle=None, est_identifiant=True):
        super(SelectionItemVM, self).__init__()
        self.Id = item_id
        self._colonne_gauche = colonne_gauche
        self._nom = nom
        self._is_selected = bool(is_selected)
        self._on_toggle = on_toggle
        self._est_identifiant = bool(est_identifiant)

    @property
    def ColonneGauche(self):
        return self._colonne_gauche

    @property
    def Nom(self):
        return self._nom

    @property
    def EstIdentifiant(self):
        return self._est_identifiant

    @property
    def IsSelected(self):
        return self._is_selected

    @IsSelected.setter
    def IsSelected(self, value):
        value = bool(value)
        if value != self._is_selected:
            self._is_selected = value
            self.notify_property('IsSelected')
            if self._on_toggle is not None:
                self._on_toggle(self)
