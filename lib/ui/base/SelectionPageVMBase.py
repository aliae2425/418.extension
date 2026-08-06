# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Base commune aux pages « Sélection » des outils (feuilles / vues) : recherche
# + multi-sélection shift/ctrl, entièrement déléguées à SelectionListController.
# Chaque outil ne fournit que la construction de ses items et les accesseurs
# d'identité/filtrage.

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    try:
        from lib.ui.base.BaseViewModel import BaseViewModel
    except Exception:
        class BaseViewModel(object):
            def __init__(self):
                pass

            def notify_property(self, name):
                pass

try:
    from core.selection_list import SelectionListController
except Exception:
    from lib.core.selection_list import SelectionListController


class SelectionPageVMBase(BaseViewModel):
    """Recherche + multi-sélection sur une liste d'items.

    `items` : ItemVM déjà construits par la sous-classe.
    `id_getter` : item -> identifiant renvoyé par `selected_ids()`.
    `filter_getters` : liste de item -> texte, testés par la recherche.
    """

    def __init__(self, items, id_getter, filter_getters,
                 on_selection_changed=None):
        super(SelectionPageVMBase, self).__init__()
        self._on_selection_changed = on_selection_changed
        self._ctrl = SelectionListController(
            items, id_getter=id_getter, filter_getters=filter_getters)

    # --- Recherche -----------------------------------------------------------
    @property
    def FilterText(self):
        return self._ctrl.filter_text

    @FilterText.setter
    def FilterText(self, value):
        self._ctrl.filter_text = value
        self.notify_property('FilterText')
        self.notify_property('FilteredItems')

    @property
    def FilteredItems(self):
        return self._ctrl.filtered_items

    # --- Sélection -----------------------------------------------------------
    def handle_row_click(self, index, shift=False, ctrl=False):
        self._ctrl.handle_row_click(index, shift, ctrl)
        self._after_selection_change()

    def select_all(self):
        self._ctrl.select_all()
        self._after_selection_change()

    def deselect_all(self):
        self._ctrl.deselect_all()
        self._after_selection_change()

    def selected_ids(self):
        return self._ctrl.selected_ids()

    @property
    def HasSelection(self):
        return self._ctrl.has_selection()

    # --- Interne -------------------------------------------------------------
    def _on_item_toggle(self, item):
        self._after_selection_change()

    def _after_selection_change(self):
        self.notify_property('HasSelection')
        if self._on_selection_changed is not None:
            self._on_selection_changed(self.selected_ids())
