# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.SelectionPageVMBase import SelectionPageVMBase
except Exception:
    from lib.ui.base.SelectionPageVMBase import SelectionPageVMBase

try:
    from lib.viewmodels.ViewItemVM import ViewItemVM
except Exception:
    from viewmodels.ViewItemVM import ViewItemVM


class SelectionPageVM(SelectionPageVMBase):
    """VM de la page Sélection : liste les vues."""

    def __init__(self, descripteurs, ids_selectionnes, on_selection_changed=None):
        selset = set(ids_selectionnes or [])
        items = [ViewItemVM(vid, nom, type_label, vid in selset, self._on_item_toggle)
                 for (vid, nom, type_label) in descripteurs]
        super(SelectionPageVM, self).__init__(
            items,
            id_getter=lambda it: it.ViewId,
            filter_getters=[lambda it: it.TypeLabel, lambda it: it.Nom],
            on_selection_changed=on_selection_changed)
