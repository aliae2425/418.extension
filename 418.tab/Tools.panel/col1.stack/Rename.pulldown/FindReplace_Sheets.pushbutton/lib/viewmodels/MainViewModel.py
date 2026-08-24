# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from ui.base.BaseViewModel import BaseViewModel
from ui.base.SelectionPageVM import SelectionPageVM
from viewmodels.NamingPageVM import NamingPageVM


class MainViewModel(BaseViewModel):
    """VM racine : gère l'état de sélection, la navigation entre Sélection
    et Nommage, et orchestre l'appel au service de renommage."""

    def __init__(self, doc=None, uidoc=None, service=None):
        super(MainViewModel, self).__init__()
        self._doc = doc
        self._uidoc = uidoc
        self._service = service
        self._mode = u'selection'
        self.SelectedSheetIds = []
        self.SelectionVM = None
        self.NamingVM = None

    @property
    def Titre(self):
        return u'418 · Renommer les feuilles'

    @property
    def Mode(self):
        return self._mode

    @property
    def IsSelection(self):
        return self._mode == u'selection'

    @property
    def IsNommage(self):
        return self._mode == u'nommage'

    @staticmethod
    def decide_initial_mode(has_selection):
        return u'nommage' if has_selection else u'selection'

    def set_mode(self, mode):
        if mode != self._mode:
            self._mode = mode
            self.notify_property('Mode')
            self.notify_property('IsSelection')
            self.notify_property('IsNommage')

    def charger(self, descripteurs, ids_courants):
        ids_courants = list(ids_courants or [])
        self._id_to_item = {vid: (num, nom) for (vid, num, nom) in descripteurs}
        self.SelectedSheetIds = list(ids_courants)
        self.SelectionVM = SelectionPageVM.depuis_descripteurs(
            descripteurs, ids_courants,
            titre=u'Feuilles à renommer', est_identifiant=True,
            on_selection_changed=self._on_selection_changed)
        self.NamingVM = NamingPageVM()
        items_initiaux = [self._id_to_item[i] for i in ids_courants if i in self._id_to_item]
        self.NamingVM.set_source_items(items_initiaux)
        self.notify_property('SelectionVM')
        self.notify_property('NamingVM')
        self.set_mode(self.decide_initial_mode(bool(ids_courants)))

    def _on_selection_changed(self, ids):
        self.SelectedSheetIds = list(ids)
        if self.NamingVM is not None:
            items = [self._id_to_item[i] for i in ids if i in self._id_to_item]
            self.NamingVM.set_source_items(items)

    def lancer(self, sheets_par_id):
        if not self.SelectedSheetIds or self._service is None:
            return 0
        sheets = [sheets_par_id[i] for i in self.SelectedSheetIds if i in sheets_par_id]
        return self._service.rename(sheets, self.NamingVM.build_options())
