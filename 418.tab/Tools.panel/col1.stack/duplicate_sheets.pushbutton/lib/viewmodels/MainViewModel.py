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
    from lib.viewmodels.OptionsPageVM import OptionsPageVM
except Exception:
    from viewmodels.OptionsPageVM import OptionsPageVM


class MainViewModel(BaseViewModel):
    """VM racine : détient l'état de sélection partagé entre les pages,
    décide de la page initiale (Sélection ou Options), expose le mode
    courant pour le binding XAML, et orchestre le lancement de la
    duplication via le service."""

    def __init__(self, doc=None, uidoc=None, service=None):
        super(MainViewModel, self).__init__()
        self._doc = doc
        self._uidoc = uidoc
        self._service = service
        self._mode = u'selection'
        self.SelectedSheetIds = []
        self.SelectionVM = None
        self.OptionsVM = None

    @property
    def Titre(self):
        return u'418 · Dupliquer les feuilles'

    @property
    def Mode(self):
        return self._mode

    @property
    def IsSelection(self):
        return self._mode == u'selection'

    @property
    def IsParams(self):
        return self._mode == u'params'

    @property
    def IsOptions(self):
        return self._mode == u'options'

    @staticmethod
    def decide_initial_mode(has_selection):
        return u'params' if has_selection else u'selection'

    def set_mode(self, mode):
        if mode != self._mode:
            self._mode = mode
            self.notify_property('Mode')
            self.notify_property('IsSelection')
            self.notify_property('IsParams')
            self.notify_property('IsOptions')

    def charger(self, descripteurs, ids_courants):
        ids_courants = list(ids_courants or [])
        self._id_to_item = {vid: (num, nom) for (vid, num, nom) in descripteurs}
        self.SelectedSheetIds = list(ids_courants)
        self.SelectionVM = SelectionPageVM.depuis_descripteurs(
            descripteurs, ids_courants,
            titre=u'Feuilles à dupliquer', est_identifiant=True,
            on_selection_changed=self._on_selection_changed)
        self.OptionsVM = OptionsPageVM()
        items_initiaux = [self._id_to_item[i] for i in ids_courants if i in self._id_to_item]
        self.OptionsVM.set_source_items(items_initiaux)
        self.notify_property('SelectionVM')
        self.notify_property('OptionsVM')
        self.set_mode(self.decide_initial_mode(bool(ids_courants)))

    def _on_selection_changed(self, ids):
        self.SelectedSheetIds = list(ids)
        if self.OptionsVM is not None:
            items = [self._id_to_item[i] for i in ids if i in self._id_to_item]
            self.OptionsVM.set_source_items(items)

    def lancer(self, sheets_par_id):
        if not self.SelectedSheetIds or self._service is None:
            return 0
        sheets = [sheets_par_id[i] for i in self.SelectedSheetIds if i in sheets_par_id]
        return self._service.duplicate(sheets, self.OptionsVM.build_options())
