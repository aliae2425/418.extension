# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    class BaseViewModel(object):
        def notify_property(self, name):
            pass

try:
    from lib.viewmodels.ViewItemVM import ViewItemVM
except Exception:
    from viewmodels.ViewItemVM import ViewItemVM

try:
    from core.selection_list import SelectionListController
except Exception:
    from lib.core.selection_list import SelectionListController


class SelectionPageVM(BaseViewModel):
    """VM de la page Sélection : liste les vues, recherche + multi-sélection
    (shift/ctrl) déléguées à SelectionListController."""

    def __init__(self, descripteurs, ids_selectionnes, on_selection_changed=None):
        super(SelectionPageVM, self).__init__()
        self._on_selection_changed = on_selection_changed
        selset = set(ids_selectionnes or [])
        items = [ViewItemVM(vid, nom, type_label, vid in selset, self._on_item_toggle)
                 for (vid, nom, type_label) in descripteurs]
        self._ctrl = SelectionListController(
            items,
            id_getter=lambda it: it.ViewId,
            filter_getters=[lambda it: it.TypeLabel, lambda it: it.Nom])

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
