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
    from lib.services.RenameService import RenameService
except Exception:
    from services.RenameService import RenameService

try:
    from lib.viewmodels.PreviewGroupVM import PreviewGroupVM, PreviewCopyVM
except Exception:
    from viewmodels.PreviewGroupVM import PreviewGroupVM, PreviewCopyVM


class OptionsPageVM(BaseViewModel):
    """VM de la page Options : mode de duplication, nombre de copies,
    nommage (littéral ou regex + tokens) et aperçu temps-réel."""

    def __init__(self):
        super(OptionsPageVM, self).__init__()
        self._ViewDuplicateOption = u'duplicate'
        self._Count = u'1'
        self._Prefixe = u''
        self._Rechercher = u''
        self._Remplacer = u''
        self._Suffixe = u''
        self._UseRegex = False
        self._source_items = []   # list of (nom, type_label)
        self._PreviewGroups = []
        self._RegexError = u''

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
    def UseRegex(self):
        return self._UseRegex

    @UseRegex.setter
    def UseRegex(self, value):
        value = bool(value)
        if value != self._UseRegex:
            self._UseRegex = value
            self.notify_property('UseRegex')
            self._recompute_preview()

    @property
    def RegexError(self):
        return self._RegexError

    @property
    def HasRegexError(self):
        return bool(self._RegexError)

    @property
    def PreviewGroups(self):
        return self._PreviewGroups

    @property
    def HasPreview(self):
        return bool(self._PreviewGroups)

    # ------------------------------------------------------------------
    # Alimentation des sources
    # ------------------------------------------------------------------

    def set_source_items(self, items):
        """items : liste de tuples (nom, type_label)."""
        self._source_items = list(items or [])
        self._recompute_preview()

    def set_source_names(self, names):
        """Compatibilité : convertit une liste de noms en items sans type."""
        self._source_items = [(nom, u'') for nom in (names or [])]
        self._recompute_preview()

    # ------------------------------------------------------------------
    # Logique de preview
    # ------------------------------------------------------------------

    def _build_rename_service(self):
        return RenameService(
            prefixe=self._Prefixe,
            rechercher=self._Rechercher,
            remplacer=self._Remplacer,
            suffixe=self._Suffixe,
            use_regex=self._UseRegex,
        )

    def _recompute_preview(self):
        try:
            count = max(1, int(self._Count))
        except (ValueError, TypeError):
            count = 1

        svc = self._build_rename_service()

        new_error = svc.regex_error if self._UseRegex else u''
        if new_error != self._RegexError:
            self._RegexError = new_error
            self.notify_property('RegexError')
            self.notify_property('HasRegexError')

        groups = []
        for nom, type_label in self._source_items:
            ctx = {u'type': type_label} if type_label else {}
            copies = [
                PreviewCopyVM(i + 1, svc.apply(nom, index=i + 1, context=ctx))
                for i in range(count)
            ]
            groups.append(PreviewGroupVM(nom, copies))
        self._PreviewGroups = groups
        self.notify_property('PreviewGroups')
        self.notify_property('HasPreview')

    # ------------------------------------------------------------------

    def build_options(self):
        """Construit un `ViewsDuplicationOptions` peuplé depuis l'état courant."""
        return ViewsDuplicationOptions(
            view_duplicate_option=self._ViewDuplicateOption,
            count=self._Count,
        )
