# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    class BaseViewModel(object):
        def __init__(self):
            pass

        def notify_property(self, name):
            pass

try:
    from ui.base.SelectionPageVM import SelectionPageVM
except Exception:
    from lib.ui.base.SelectionPageVM import SelectionPageVM


class MainViewModel(BaseViewModel):
    """VM racine « Matériaux » : contrat RailWindow (`Mode` + `set_mode` + un
    attribut par onglet) et sélection des matériaux à traiter.

    Squelette : `lancer()` ne fait que rendre les matériaux cochés. C'est là
    que viendra l'appel au service quand l'outil aura une action.
    """

    def __init__(self, doc=None, uidoc=None, service=None):
        super(MainViewModel, self).__init__()
        self._doc = doc
        self._uidoc = uidoc
        self._service = service
        self._mode = u'selection'
        self.SelectedMaterialIds = []
        self.SelectionVM = None

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

    def charger(self, descripteurs, ids_courants):
        """`descripteurs` : triplets `(id, classe, nom)`."""
        ids_courants = list(ids_courants or [])
        self.SelectedMaterialIds = list(ids_courants)
        self.SelectionVM = SelectionPageVM.depuis_descripteurs(
            descripteurs, ids_courants,
            titre=u'Matériaux', est_identifiant=False,
            on_selection_changed=self._on_selection_changed)
        self.notify_property('SelectionVM')

    def _on_selection_changed(self, ids):
        self.SelectedMaterialIds = list(ids)

    def lancer(self, materiaux_par_id):
        if not self.SelectedMaterialIds:
            return []
        return [materiaux_par_id[i] for i in self.SelectedMaterialIds
                if i in materiaux_par_id]
