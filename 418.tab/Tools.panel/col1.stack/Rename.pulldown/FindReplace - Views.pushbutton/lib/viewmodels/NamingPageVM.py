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
    from lib.services.RenameOptions import RenameViewOptions
except Exception:
    from services.RenameOptions import RenameViewOptions

try:
    from lib.services.RenameService import RenameService
except Exception:
    from services.RenameService import RenameService

try:
    from lib.viewmodels.ViewPreviewVM import ViewPreviewVM
except Exception:
    from viewmodels.ViewPreviewVM import ViewPreviewVM


class NamingPageVM(BaseViewModel):
    """VM de la page Nommage : champs préfixe/rechercher/remplacer/suffixe
    pour le nom de vue, avec aperçu temps réel."""

    def __init__(self):
        super(NamingPageVM, self).__init__()
        self._ViewFind = u''
        self._ViewReplace = u''
        self._ViewPrefix = u''
        self._ViewSuffix = u''
        self._source_items = []
        self._PreviewGroups = []
        self._RegexError = u''

    # -- Nommage vue -------------------------------------------------------

    @property
    def ViewFind(self):
        return self._ViewFind

    @ViewFind.setter
    def ViewFind(self, value):
        if value != self._ViewFind:
            self._ViewFind = value
            self.notify_property('ViewFind')
            self._recompute_preview()

    @property
    def ViewReplace(self):
        return self._ViewReplace

    @ViewReplace.setter
    def ViewReplace(self, value):
        if value != self._ViewReplace:
            self._ViewReplace = value
            self.notify_property('ViewReplace')
            self._recompute_preview()

    @property
    def ViewPrefix(self):
        return self._ViewPrefix

    @ViewPrefix.setter
    def ViewPrefix(self, value):
        if value != self._ViewPrefix:
            self._ViewPrefix = value
            self.notify_property('ViewPrefix')
            self._recompute_preview()

    @property
    def ViewSuffix(self):
        return self._ViewSuffix

    @ViewSuffix.setter
    def ViewSuffix(self, value):
        if value != self._ViewSuffix:
            self._ViewSuffix = value
            self.notify_property('ViewSuffix')
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
        """items : liste de tuples (nom, type_label)."""
        self._source_items = list(items or [])
        self._recompute_preview()

    def _build_svc(self):
        return RenameService(
            prefixe=self._ViewPrefix, rechercher=self._ViewFind,
            remplacer=self._ViewReplace, suffixe=self._ViewSuffix,
            use_regex=True)

    def _recompute_preview(self):
        svc = self._build_svc()
        new_error = svc.regex_error
        if new_error != self._RegexError:
            self._RegexError = new_error
            self.notify_property('RegexError')
            self.notify_property('HasRegexError')
        self._PreviewGroups = [
            ViewPreviewVM(nom, type_label, svc.apply(nom))
            for (nom, type_label) in self._source_items
        ]
        self.notify_property('PreviewGroups')
        self.notify_property('HasPreview')

    # -- Production de l'objet de données ---------------------------------

    def build_options(self):
        return RenameViewOptions(
            view_find=self._ViewFind,
            view_replace=self._ViewReplace,
            view_prefix=self._ViewPrefix,
            view_suffix=self._ViewSuffix,
        )
