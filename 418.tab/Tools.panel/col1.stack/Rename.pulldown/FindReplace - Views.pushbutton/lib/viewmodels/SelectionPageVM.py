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


class SelectionPageVM(BaseViewModel):
    """VM de la page Sélection : liste toutes les vues, pré-cochées selon
    la sélection courante, et répercute les changements via callback."""

    def __init__(self, descripteurs, ids_selectionnes, on_selection_changed=None):
        super(SelectionPageVM, self).__init__()
        self._on_selection_changed = on_selection_changed
        selset = set(ids_selectionnes or [])
        self._items = [ViewItemVM(vid, nom, type_label, vid in selset, self._on_item_toggle)
                       for (vid, nom, type_label) in descripteurs]

    @property
    def Items(self):
        return self._items

    def selected_ids(self):
        return [it.ViewId for it in self._items if it.IsSelected]

    @property
    def HasSelection(self):
        return any(it.IsSelected for it in self._items)

    def _on_item_toggle(self, item):
        self.notify_property('HasSelection')
        if self._on_selection_changed is not None:
            self._on_selection_changed(self.selected_ids())
