# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from core.list_selection import ListSelectionService
from core.text_filter import TextFilterService
from core.bulk_edit import BulkEditService


class SelectionListController(object):
    """Orchestre la sélection multi-items (shift/ctrl), le filtrage texte et les
    actions de masse pour une page de sélection. Python pur, testable.

    - clic simple  : bascule l'item (accumulation, pas d'exclusif)
    - Ctrl+clic    : bascule l'item
    - Shift+clic   : plage [ancre, index] sur les items AFFICHÉS (filtrés),
                     uniquement si une ancre valide existe déjà (sinon on
                     retombe sur un simple toggle, cf. reset de l'ancre)
    - select_all / deselect_all : sur la liste COMPLÈTE (y compris masqués)
    """

    def __init__(self, items, id_getter, filter_getters, prop=u'IsSelected'):
        self._all = list(items or [])
        self._id_getter = id_getter
        self._filter_getters = list(filter_getters or [])
        self._prop = prop
        self._selection = ListSelectionService(prop=prop)
        self._filter = TextFilterService()
        self._bulk = BulkEditService()
        self._filter_text = u''
        self._filtered = list(self._all)
        # Suivi local de la validité de l'ancre : ListSelectionService.reset()
        # remet son ancre interne à -1 mais ne l'expose pas publiquement.
        # On duplique l'information ici pour savoir si un Shift doit être
        # traité comme une plage ou comme un toggle simple (repli).
        self._has_anchor = False

    @property
    def all_items(self):
        return self._all

    @property
    def filtered_items(self):
        return self._filtered

    @property
    def filter_text(self):
        return self._filter_text

    @filter_text.setter
    def filter_text(self, value):
        self._filter_text = value or u''
        self._filtered = self._filter.filter(
            self._all, self._filter_text, self._filter_getters)
        self._selection.reset()   # index invalidés -> ancre perdue
        self._has_anchor = False

    def handle_row_click(self, index, shift=False, ctrl=False):
        if shift and self._has_anchor:
            self._selection.handle_click(self._filtered, index, shift=True)
        else:
            # clic simple, Ctrl, OU Shift sans ancre valide -> bascule
            # ponctuelle (case reste le contrôle, pas d'exclusif)
            self._selection.handle_click(self._filtered, index, ctrl=True)
            self._has_anchor = True

    def select_all(self):
        self._bulk.select_all(self._all, self._prop)

    def deselect_all(self):
        self._bulk.deselect_all(self._all, self._prop)

    def selected_ids(self):
        return [self._id_getter(it) for it in self._all
                if getattr(it, self._prop, False)]

    def has_selection(self):
        return any(getattr(it, self._prop, False) for it in self._all)
