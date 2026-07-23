# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    BaseViewModel = object

_MODES = (u'auto', u'manual', u'settings')
_SURFACE_TITRES = {
    u'auto': u'Jeux qualifiés à l\'export',
    u'manual': u'Sélection manuelle',
    u'settings': u'Paramètres',
}


class MainViewModel(BaseViewModel):
    def __init__(self, doc=None):
        super(MainViewModel, self).__init__()
        self._doc = doc
        self._titre = u'Exportation'
        self._mode = u'auto'

    @property
    def Titre(self):
        return self._titre

    @property
    def ActiveMode(self):
        return self._mode

    @ActiveMode.setter
    def ActiveMode(self, value):
        if value not in _MODES:
            return
        self._mode = value
        for name in (u'ActiveMode', u'IsAuto', u'IsManual',
                     u'IsSettings', u'SurfaceTitre'):
            self.notify_property(name)

    def set_mode(self, mode):
        self.ActiveMode = mode

    @property
    def IsAuto(self):
        return self._mode == u'auto'

    @property
    def IsManual(self):
        return self._mode == u'manual'

    @property
    def IsSettings(self):
        return self._mode == u'settings'

    @property
    def SurfaceTitre(self):
        return _SURFACE_TITRES.get(self._mode, u'')
