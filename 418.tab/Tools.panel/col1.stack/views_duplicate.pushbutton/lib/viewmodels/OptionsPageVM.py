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
    from lib.services.ViewsDuplicationOptions import ViewsDuplicationOptions
except Exception:
    from services.ViewsDuplicationOptions import ViewsDuplicationOptions

try:
    from lib.viewmodels.PreviewGroupVM import PreviewGroupVM
except Exception:
    from viewmodels.PreviewGroupVM import PreviewGroupVM


class OptionsPageVM(BaseViewModel):
    """VM de la page Options : mode de duplication, nombre de copies, nommage
    et aperçu temps-réel des noms de vues générés."""

    def __init__(self):
        super(OptionsPageVM, self).__init__()
        self._ViewDuplicateOption = u'duplicate'
        self._Count = u'1'
        self._Prefixe = u''
        self._Rechercher = u''
        self._Remplacer = u''
        self._Suffixe = u''
        self._source_names = []
        self._PreviewGroups = []

    # ------------------------------------------------------------------
    # Propriétés bindables
    # ------------------------------------------------------------------

    @property
    def ViewDuplicateOption(self):
        return self._ViewDuplicateOption

    @ViewDuplicateOption.setter
    def ViewDuplicateOption(self, value):
        if value != self._ViewDuplicateOption:
            self._ViewDuplicateOption = value
            self.notify_property('ViewDuplicateOption')

    @property
    def Count(self):
        return self._Count

    @Count.setter
    def Count(self, value):
        if value != self._Count:
            self._Count = value
            self.notify_property('Count')
            self._recompute_preview()

    @property
    def Prefixe(self):
        return self._Prefixe

    @Prefixe.setter
    def Prefixe(self, value):
        if value != self._Prefixe:
            self._Prefixe = value
            self.notify_property('Prefixe')
            self._recompute_preview()

    @property
    def Rechercher(self):
        return self._Rechercher

    @Rechercher.setter
    def Rechercher(self, value):
        if value != self._Rechercher:
            self._Rechercher = value
            self.notify_property('Rechercher')
            self._recompute_preview()

    @property
    def Remplacer(self):
        return self._Remplacer

    @Remplacer.setter
    def Remplacer(self, value):
        if value != self._Remplacer:
            self._Remplacer = value
            self.notify_property('Remplacer')
            self._recompute_preview()

    @property
    def Suffixe(self):
        return self._Suffixe

    @Suffixe.setter
    def Suffixe(self, value):
        if value != self._Suffixe:
            self._Suffixe = value
            self.notify_property('Suffixe')
            self._recompute_preview()

    @property
    def PreviewGroups(self):
        return self._PreviewGroups

    @property
    def HasPreview(self):
        return bool(self._PreviewGroups)

    # ------------------------------------------------------------------
    # Logique de preview
    # ------------------------------------------------------------------

    def set_source_names(self, names):
        """Met à jour la liste de noms de vues sources et recalcule l'aperçu."""
        self._source_names = list(names or [])
        self._recompute_preview()

    def _compute_name(self, original):
        name = original
        if self._Rechercher:
            name = name.replace(self._Rechercher, self._Remplacer)
        return self._Prefixe + name + self._Suffixe

    def _recompute_preview(self):
        try:
            count = max(1, int(self._Count))
        except (ValueError, TypeError):
            count = 1
        self._PreviewGroups = [
            PreviewGroupVM(nom, self._compute_name(nom), count)
            for nom in self._source_names
        ]
        self.notify_property('PreviewGroups')
        self.notify_property('HasPreview')

    # ------------------------------------------------------------------

    def build_options(self):
        """Construit un `ViewsDuplicationOptions` peuplé depuis l'état courant."""
        return ViewsDuplicationOptions(
            view_duplicate_option=self._ViewDuplicateOption,
            count=self._Count,
        )
