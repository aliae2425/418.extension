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
    """VM racine « Matériaux » : trois onglets, TROIS sélections.

    Les trois onglets affichent les mêmes `MaterialCardVM` — un seul objet
    par matériau, donc les vignettes et le comptage d'usages ne sont calculés
    qu'une fois — mais chacun a sa `SelectionPageVM` sur SA case
    (`IsSelected`, `IsSelectedRenommer`, `IsSelectedRemplacer`). Cocher dans
    un onglet ne touche pas aux autres, et chaque onglet a sa recherche.

    L'onglet Matériaux garde donc une sélection à lui, pilotée par le menu
    `PRESETS`. Elle n'alimente encore aucune action — c'est voulu, l'usage
    viendra avec la suite (purge).
    """

    #: Menu de sélection de l'onglet Matériaux : (libellé, prédicat sur la
    #: card). Les critères d'usage viennent du comptage fait à l'ouverture
    #: par script.py ; sans comptage, tout est « non utilisé ».
    PRESETS = (
        (u'Tout', lambda carte: True),
        (u'Aucun', lambda carte: False),
        (u'Utilisés', lambda carte: carte.EstUtilise),
        (u'Non utilisés', lambda carte: not carte.EstUtilise),
        (u'Sans instance', lambda carte: carte.SansInstance),
    )

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

        self.SelectionVM = self._nouvelle_page(cartes, u'IsSelected',
                                               u'Matériaux',
                                               presets=self.PRESETS)
        page_renommer = self._nouvelle_page(cartes, u'IsSelectedRenommer',
                                           u'Renommer')
        page_remplacer = self._nouvelle_page(cartes, u'IsSelectedRemplacer',
                                            u'Remplacer')
        self.RenommerVM = RenommerPageVM(self._service, page_renommer,
                                         self._materiaux_par_id)
        self.RemplacerVM = RemplacerPageVM(self._service, page_remplacer,
                                           categories)
        # Le rappel se pose après coup : la page naît avant son VM d'onglet,
        # qui a besoin d'elle. Même geste que le `_on_toggle` des CategorieVM.
        page_renommer._on_selection_changed = self.RenommerVM.set_sources
        page_remplacer._on_selection_changed = self.RemplacerVM.set_sources
        for nom in ('SelectionVM', 'RemplacerVM', 'RenommerVM'):
            self.notify_property(nom)
        self.RenommerVM.set_sources(page_renommer.selected_ids())
        self.RemplacerVM.set_sources(page_remplacer.selected_ids())

    def _nouvelle_page(self, cartes, prop, titre, presets=None):
        """Une page de sélection sur `prop`, cards branchées sur elle."""
        page = SelectionPageVM(
            cartes,
            id_getter=lambda carte: carte.Id,
            filter_getters=[lambda carte: carte.Nom, lambda carte: carte.Classe],
            prop=prop, titre=titre, presets=presets)
        # Une case écrite directement (menu, code) doit prévenir SA page,
        # sinon l'onglet ne voit pas la coche.
        for carte in cartes:
            carte.brancher(prop, page._on_item_toggle)
        return page
