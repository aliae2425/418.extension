# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.SelectionPageVM import SelectionPageVM as _Base
except Exception:
    from lib.ui.base.SelectionPageVM import SelectionPageVM as _Base

try:
    from lib.viewmodels.ViewItemVM import ViewItemVM
except Exception:
    from viewmodels.ViewItemVM import ViewItemVM


class SelectionPageVM(_Base):
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
