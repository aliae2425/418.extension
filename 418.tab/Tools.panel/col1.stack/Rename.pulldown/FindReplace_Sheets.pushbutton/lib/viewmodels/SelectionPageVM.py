# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.SelectionPageVM import SelectionPageVM as _Base
except Exception:
    from lib.ui.base.SelectionPageVM import SelectionPageVM as _Base

try:
    from lib.viewmodels.SheetItemVM import SheetItemVM
except Exception:
    from viewmodels.SheetItemVM import SheetItemVM


class SelectionPageVM(_Base):
    """VM de la page Sélection : liste les feuilles."""

    def __init__(self, descripteurs, ids_selectionnes, on_selection_changed=None):
        selset = set(ids_selectionnes or [])
        items = [SheetItemVM(sid, numero, nom, sid in selset, self._on_item_toggle)
                 for (sid, numero, nom) in descripteurs]
        super(SelectionPageVM, self).__init__(
            items,
            id_getter=lambda it: it.SheetId,
            filter_getters=[lambda it: it.Numero, lambda it: it.Nom],
            on_selection_changed=on_selection_changed)
