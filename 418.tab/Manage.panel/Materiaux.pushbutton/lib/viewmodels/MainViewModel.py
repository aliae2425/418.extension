# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    from lib.ui.base.BaseViewModel import BaseViewModel

try:
    from ui.base.SelectionPageVM import SelectionPageVM
except Exception:
    from lib.ui.base.SelectionPageVM import SelectionPageVM

try:
    from lib.viewmodels.RemplacerPageVM import RemplacerPageVM
except Exception:
    from viewmodels.RemplacerPageVM import RemplacerPageVM

try:
    from lib.viewmodels.RenommerPageVM import RenommerPageVM
except Exception:
    from viewmodels.RenommerPageVM import RenommerPageVM


class MainViewModel(BaseViewModel):
    """VM racine « Matériaux » : trois onglets sur une seule sélection.

    L'onglet Matériaux EST la page de sélection — ses cards sont des items
    de `SelectionPageVM`, ce qui donne recherche, Tout/Aucun et clic
    simple/Ctrl/Shift sans code propre à cet outil. Cocher une card
    réalimente les deux autres onglets.
    """

    def __init__(self, service=None):
        super(MainViewModel, self).__init__()
        self._service = service
        self._materiaux_par_id = {}
        self._mode = u'selection'
        self.SelectionVM = None
        self.RemplacerVM = None
        self.RenommerVM = None

    @property
    def Titre(self):
        return u'418 · Matériaux'

    @property
    def Mode(self):
        return self._mode

    def set_mode(self, mode):
        if mode != self._mode:
            self._mode = mode
            self.notify_property('Mode')

    def charger(self, cartes, materiaux_par_id, categories=None):
        """`cartes` : `MaterialCardVM` construites par script.py.
        `materiaux_par_id` : id -> `Material` Revit, pour le renommage.
        `categories` : `CategorieVM` présentes dans le modèle, pour le menu
        déroulant de portée de l'onglet Remplacer."""
        cartes = list(cartes or [])
        self._materiaux_par_id = dict(materiaux_par_id or {})
        self.SelectionVM = SelectionPageVM(
            cartes,
            id_getter=lambda carte: carte.Id,
            filter_getters=[lambda carte: carte.Nom, lambda carte: carte.Classe],
            on_selection_changed=self._on_selection_changed,
            titre=u'Matériaux')
        self.RemplacerVM = RemplacerPageVM(self._service, self.SelectionVM,
                                           categories)
        self.RenommerVM = RenommerPageVM(self._service)
        for nom in ('SelectionVM', 'RemplacerVM', 'RenommerVM'):
            self.notify_property(nom)
        self._on_selection_changed(self.SelectionVM.selected_ids())

    def _on_selection_changed(self, ids):
        ids = list(ids or [])
        if self.RemplacerVM is not None:
            self.RemplacerVM.set_sources(ids)
        if self.RenommerVM is not None:
            self.RenommerVM.set_sources(
                [self._materiaux_par_id[i] for i in ids
                 if i in self._materiaux_par_id])
