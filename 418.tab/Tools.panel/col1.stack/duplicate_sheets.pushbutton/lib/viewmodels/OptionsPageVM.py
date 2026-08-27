# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    from lib.ui.base.BaseViewModel import BaseViewModel

try:
    from lib.services.DuplicationOptions import DuplicationOptions
except Exception:
    from services.DuplicationOptions import DuplicationOptions

try:
    from core.rename_service import RenameService
except Exception:
    from lib.core.rename_service import RenameService

try:
    from ui.base.SheetPreviewGroupVM import SheetPreviewGroupVM
except Exception:
    from lib.ui.base.SheetPreviewGroupVM import SheetPreviewGroupVM


class OptionsPageVM(BaseViewModel):
    """VM de la page Options : nommage + inclusions + option de duplication.

    Chaque propriété PascalCase est bindable en WPF (TwoWay) et correspond
    1:1 à un champ snake_case de `DuplicationOptions`. Les propriétés sont
    écrites en `@property` inline (getter/setter notifiant), plutôt qu'avec
    une fabrique dynamique attachée après coup à la classe : le binding WPF
    TwoWay en IronPython ne voit pas de façon fiable des descripteurs
    `property` attachés dynamiquement via `setattr(Classe, nom, property(...))`
    après la définition de la classe. Le patron `@property` inline est le
    patron du projet dont la fiabilité de binding est éprouvée (cf.
    `SheetItemVM.IsSelected`).
    """

    def __init__(self):
        super(OptionsPageVM, self).__init__()
        defaults = DuplicationOptions()
        self._ViewFind = defaults.view_find
        self._ViewReplace = defaults.view_replace
        self._ViewPrefix = defaults.view_prefix
        self._ViewSuffix = defaults.view_suffix
        self._NumberFind = defaults.number_find
        self._NumberReplace = defaults.number_replace
        self._NumberPrefix = defaults.number_prefix
        self._NumberSuffix = defaults.number_suffix
        self._NameFind = defaults.name_find
        self._NameReplace = defaults.name_replace
        self._NamePrefix = defaults.name_prefix
        self._NameSuffix = defaults.name_suffix
        self._IncludeViews = defaults.include_views
        self._IncludeLegends = defaults.include_legends
        self._IncludeSchedules = defaults.include_schedules
        self._IncludeImages = defaults.include_images
        self._IncludeLines = defaults.include_lines
        self._IncludeText = defaults.include_text
        self._IncludeClouds = defaults.include_clouds
        self._IncludeDwgs = defaults.include_dwgs
        self._IncludeSymbols = defaults.include_symbols
        self._IncludeDimensions = defaults.include_dimensions
        self._IncludeAdditionalRevisions = defaults.include_additional_revisions
        self._UseExistingLegends = defaults.use_existing_legends
        self._UseExistingSchedules = defaults.use_existing_schedules
        self._ViewDuplicateOption = defaults.view_duplicate_option
        self._source_items = []   # list of (numero, nom)
        self._PreviewGroups = []
        self._RegexError = u''

    # -- Nommage vues ---------------------------------------------------

    @property
    def ViewFind(self):
        return self._ViewFind

    @ViewFind.setter
    def ViewFind(self, value):
        if value != self._ViewFind:
            self._ViewFind = value
            self.notify_property('ViewFind')

    @property
    def ViewReplace(self):
        return self._ViewReplace

    @ViewReplace.setter
    def ViewReplace(self, value):
        if value != self._ViewReplace:
            self._ViewReplace = value
            self.notify_property('ViewReplace')

    @property
    def ViewPrefix(self):
        return self._ViewPrefix

    @ViewPrefix.setter
    def ViewPrefix(self, value):
        if value != self._ViewPrefix:
            self._ViewPrefix = value
            self.notify_property('ViewPrefix')

    @property
    def ViewSuffix(self):
        return self._ViewSuffix

    @ViewSuffix.setter
    def ViewSuffix(self, value):
        if value != self._ViewSuffix:
            self._ViewSuffix = value
            self.notify_property('ViewSuffix')

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

    # -- Nommage feuille (nom) --------------------------------------------

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

    # -- Inclusions ---------------------------------------------------------

    @property
    def IncludeViews(self):
        return self._IncludeViews

    @IncludeViews.setter
    def IncludeViews(self, value):
        value = bool(value)
        if value != self._IncludeViews:
            self._IncludeViews = value
            self.notify_property('IncludeViews')

    @property
    def IncludeLegends(self):
        return self._IncludeLegends

    @IncludeLegends.setter
    def IncludeLegends(self, value):
        value = bool(value)
        if value != self._IncludeLegends:
            self._IncludeLegends = value
            self.notify_property('IncludeLegends')

    @property
    def IncludeSchedules(self):
        return self._IncludeSchedules

    @IncludeSchedules.setter
    def IncludeSchedules(self, value):
        value = bool(value)
        if value != self._IncludeSchedules:
            self._IncludeSchedules = value
            self.notify_property('IncludeSchedules')

    @property
    def IncludeImages(self):
        return self._IncludeImages

    @IncludeImages.setter
    def IncludeImages(self, value):
        value = bool(value)
        if value != self._IncludeImages:
            self._IncludeImages = value
            self.notify_property('IncludeImages')

    @property
    def IncludeLines(self):
        return self._IncludeLines

    @IncludeLines.setter
    def IncludeLines(self, value):
        value = bool(value)
        if value != self._IncludeLines:
            self._IncludeLines = value
            self.notify_property('IncludeLines')

    @property
    def IncludeText(self):
        return self._IncludeText

    @IncludeText.setter
    def IncludeText(self, value):
        value = bool(value)
        if value != self._IncludeText:
            self._IncludeText = value
            self.notify_property('IncludeText')

    @property
    def IncludeClouds(self):
        return self._IncludeClouds

    @IncludeClouds.setter
    def IncludeClouds(self, value):
        value = bool(value)
        if value != self._IncludeClouds:
            self._IncludeClouds = value
            self.notify_property('IncludeClouds')

    @property
    def IncludeDwgs(self):
        return self._IncludeDwgs

    @IncludeDwgs.setter
    def IncludeDwgs(self, value):
        value = bool(value)
        if value != self._IncludeDwgs:
            self._IncludeDwgs = value
            self.notify_property('IncludeDwgs')

    @property
    def IncludeSymbols(self):
        return self._IncludeSymbols

    @IncludeSymbols.setter
    def IncludeSymbols(self, value):
        value = bool(value)
        if value != self._IncludeSymbols:
            self._IncludeSymbols = value
            self.notify_property('IncludeSymbols')

    @property
    def IncludeDimensions(self):
        return self._IncludeDimensions

    @IncludeDimensions.setter
    def IncludeDimensions(self, value):
        value = bool(value)
        if value != self._IncludeDimensions:
            self._IncludeDimensions = value
            self.notify_property('IncludeDimensions')

    @property
    def IncludeAdditionalRevisions(self):
        return self._IncludeAdditionalRevisions

    @IncludeAdditionalRevisions.setter
    def IncludeAdditionalRevisions(self, value):
        value = bool(value)
        if value != self._IncludeAdditionalRevisions:
            self._IncludeAdditionalRevisions = value
            self.notify_property('IncludeAdditionalRevisions')

    # -- Réutilisation d'éléments existants ----------------------------------

    @property
    def UseExistingLegends(self):
        return self._UseExistingLegends

    @UseExistingLegends.setter
    def UseExistingLegends(self, value):
        value = bool(value)
        if value != self._UseExistingLegends:
            self._UseExistingLegends = value
            self.notify_property('UseExistingLegends')

    @property
    def UseExistingSchedules(self):
        return self._UseExistingSchedules

    @UseExistingSchedules.setter
    def UseExistingSchedules(self, value):
        value = bool(value)
        if value != self._UseExistingSchedules:
            self._UseExistingSchedules = value
            self.notify_property('UseExistingSchedules')

    # -- Option de duplication des vues --------------------------------------

    @property
    def ViewDuplicateOption(self):
        return self._ViewDuplicateOption

    @ViewDuplicateOption.setter
    def ViewDuplicateOption(self, value):
        if value != self._ViewDuplicateOption:
            self._ViewDuplicateOption = value
            self.notify_property('ViewDuplicateOption')

    # -- Preview en temps réel ----------------------------------------------

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
            remplacer=self._NumberReplace, suffixe=self._NumberSuffix, use_regex=True)

    def _build_svc_name(self):
        return RenameService(
            prefixe=self._NamePrefix, rechercher=self._NameFind,
            remplacer=self._NameReplace, suffixe=self._NameSuffix, use_regex=True)

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
            SheetPreviewGroupVM(num, nom, svc_n.apply(num), svc_nm.apply(nom))
            for (num, nom) in self._source_items
        ]
        self.notify_property('PreviewGroups')
        self.notify_property('HasPreview')

    # -- Production de l'objet de données ------------------------------------

    def build_options(self):
        """Construit un `DuplicationOptions` peuplé depuis l'état courant."""
        return DuplicationOptions(
            view_find=self._ViewFind,
            view_replace=self._ViewReplace,
            view_prefix=self._ViewPrefix,
            view_suffix=self._ViewSuffix,
            number_find=self._NumberFind,
            number_replace=self._NumberReplace,
            number_prefix=self._NumberPrefix,
            number_suffix=self._NumberSuffix,
            name_find=self._NameFind,
            name_replace=self._NameReplace,
            name_prefix=self._NamePrefix,
            name_suffix=self._NameSuffix,
            include_views=self._IncludeViews,
            include_legends=self._IncludeLegends,
            include_schedules=self._IncludeSchedules,
            include_images=self._IncludeImages,
            include_lines=self._IncludeLines,
            include_text=self._IncludeText,
            include_clouds=self._IncludeClouds,
            include_dwgs=self._IncludeDwgs,
            include_symbols=self._IncludeSymbols,
            include_dimensions=self._IncludeDimensions,
            include_additional_revisions=self._IncludeAdditionalRevisions,
            use_existing_legends=self._UseExistingLegends,
            use_existing_schedules=self._UseExistingSchedules,
            view_duplicate_option=self._ViewDuplicateOption,
        )
