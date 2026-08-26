# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    from lib.ui.base.BaseViewModel import BaseViewModel

try:
    from lib.services.RenameOptions import RenameSheetOptions
except Exception:
    from services.RenameOptions import RenameSheetOptions

try:
    from core.rename_service import RenameService
except Exception:
    from lib.core.rename_service import RenameService

try:
    from ui.base.SheetPreviewGroupVM import SheetPreviewGroupVM
except Exception:
    from lib.ui.base.SheetPreviewGroupVM import SheetPreviewGroupVM


class NamingPageVM(BaseViewModel):
    """VM de la page Nommage : champs préfixe/rechercher/remplacer/suffixe
    pour le numéro et le nom de feuille, avec aperçu temps réel."""

    def __init__(self):
        super(NamingPageVM, self).__init__()
        self._NumberFind = u''
        self._NumberReplace = u''
        self._NumberPrefix = u''
        self._NumberSuffix = u''
        self._NameFind = u''
        self._NameReplace = u''
        self._NamePrefix = u''
        self._NameSuffix = u''
        self._source_items = []
        self._PreviewGroups = []
        self._RegexError = u''

    # -- Nommage numéros --------------------------------------------------

    @property
    def NumberFind(self):
        return self._NumberFind

    @NumberFind.setter
    def NumberFind(self, value):
        if value != self._NumberFind:
            self._NumberFind = value
            self.notify_property('NumberFind')
            self._recompute_preview()

    @property
    def NumberReplace(self):
        return self._NumberReplace

    @NumberReplace.setter
    def NumberReplace(self, value):
        if value != self._NumberReplace:
            self._NumberReplace = value
            self.notify_property('NumberReplace')
            self._recompute_preview()

    @property
    def NumberPrefix(self):
        return self._NumberPrefix

    @NumberPrefix.setter
    def NumberPrefix(self, value):
        if value != self._NumberPrefix:
            self._NumberPrefix = value
            self.notify_property('NumberPrefix')
            self._recompute_preview()

    @property
    def NumberSuffix(self):
        return self._NumberSuffix

    @NumberSuffix.setter
    def NumberSuffix(self, value):
        if value != self._NumberSuffix:
            self._NumberSuffix = value
            self.notify_property('NumberSuffix')
            self._recompute_preview()

    # -- Nommage nom feuille ----------------------------------------------

    @property
    def NameFind(self):
        return self._NameFind

    @NameFind.setter
    def NameFind(self, value):
        if value != self._NameFind:
            self._NameFind = value
            self.notify_property('NameFind')
            self._recompute_preview()

    @property
    def NameReplace(self):
        return self._NameReplace

    @NameReplace.setter
    def NameReplace(self, value):
        if value != self._NameReplace:
            self._NameReplace = value
            self.notify_property('NameReplace')
            self._recompute_preview()

    @property
    def NamePrefix(self):
        return self._NamePrefix

    @NamePrefix.setter
    def NamePrefix(self, value):
        if value != self._NamePrefix:
            self._NamePrefix = value
            self.notify_property('NamePrefix')
            self._recompute_preview()

    @property
    def NameSuffix(self):
        return self._NameSuffix

    @NameSuffix.setter
    def NameSuffix(self, value):
        if value != self._NameSuffix:
            self._NameSuffix = value
            self.notify_property('NameSuffix')
            self._recompute_preview()

    # -- Aperçu -----------------------------------------------------------

    @property
    def PreviewGroups(self):
        return self._PreviewGroups

    @property
    def HasPreview(self):
        return bool(self._PreviewGroups)

    @property
    def RegexError(self):
        return self._RegexError

    @property
    def HasRegexError(self):
        return bool(self._RegexError)

    def set_source_items(self, items):
        """items : liste de tuples (numero, nom)."""
        self._source_items = list(items or [])
        self._recompute_preview()

    def _build_svc_number(self):
        return RenameService(
            prefixe=self._NumberPrefix, rechercher=self._NumberFind,
            remplacer=self._NumberReplace, suffixe=self._NumberSuffix,
            use_regex=True)

    def _build_svc_name(self):
        return RenameService(
            prefixe=self._NamePrefix, rechercher=self._NameFind,
            remplacer=self._NameReplace, suffixe=self._NameSuffix,
            use_regex=True)

    def _recompute_preview(self):
        svc_n = self._build_svc_number()
        svc_nm = self._build_svc_name()
        errors = [e for e in (svc_n.regex_error, svc_nm.regex_error) if e]
        new_error = u' | '.join(errors)
        if new_error != self._RegexError:
            self._RegexError = new_error
            self.notify_property('RegexError')
            self.notify_property('HasRegexError')
        self._PreviewGroups = [
            SheetPreviewGroupVM(num, nom,
                                svc_n.apply(num, index=i), svc_nm.apply(nom, index=i))
            for i, (num, nom) in enumerate(self._source_items, start=1)
        ]
        self.notify_property('PreviewGroups')
        self.notify_property('HasPreview')

    # -- Production de l'objet de données ---------------------------------

    def build_options(self):
        return RenameSheetOptions(
            number_find=self._NumberFind,
            number_replace=self._NumberReplace,
            number_prefix=self._NumberPrefix,
            number_suffix=self._NumberSuffix,
            name_find=self._NameFind,
            name_replace=self._NameReplace,
            name_prefix=self._NamePrefix,
            name_suffix=self._NameSuffix,
        )
