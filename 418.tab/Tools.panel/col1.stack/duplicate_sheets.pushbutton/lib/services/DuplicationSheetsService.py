# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from Autodesk.Revit.DB import (FilteredElementCollector, BuiltInCategory,
                                    ElementId, ViewSheet, ViewType,
                                    ViewDuplicateOption, Viewport,
                                    ScheduleSheetInstance, ImportInstance,
                                    ElementTransformUtils, CopyPasteOptions,
                                    ElementMulticategoryFilter)
    from System.Collections.Generic import List
except Exception:
    FilteredElementCollector = None
    BuiltInCategory = None
    ElementId = None
    ViewSheet = None
    ViewType = None
    ViewDuplicateOption = None
    Viewport = None
    ScheduleSheetInstance = None
    ImportInstance = None
    ElementTransformUtils = None
    CopyPasteOptions = None
    ElementMulticategoryFilter = None
    List = None

try:
    from core.transaction import revit_transaction
except Exception:
    revit_transaction = None

try:
    from core.sanitize import sanitize_revit_name
except Exception:
    def sanitize_revit_name(x):
        return x or u'SansNom'

try:
    from lib.services.RenameService import RenameService
except Exception:
    try:
        from services.RenameService import RenameService
    except Exception:
        RenameService = None


_VIEW_DUP_MAP = {
    u'duplicate': 'Duplicate',
    u'with_detailing': 'WithDetailing',
    u'as_dependent': 'AsDependent',
}


class DuplicationSheetsService(object):
    """Service de duplication de feuilles Revit (vues, légendes, nomenclatures,
    lignes, cartouches de révision, images, texte, cotes, symboles, DWG).

    Portage de la logique de l'ancien outil `duplicate_sheets` monolithique
    vers un service découplé de l'UI."""

    def __init__(self, doc):
        self._doc = doc

    def _view_dup_option(self, key):
        """Traduit la clé d'option (str) en ViewDuplicateOption."""
        name = _VIEW_DUP_MAP.get(key, 'Duplicate')
        return getattr(ViewDuplicateOption, name)

    def _resolve_name(self, source, prefixe, rechercher, remplacer, suffixe):
        """Calcule le nom cible à partir de la valeur SOURCE.

        Utilise RenameService (regex + tokens, use_regex=True) comme le fait
        l'aperçu — appel sans index ni context. Fallback str.replace si
        RenameService indisponible (import-guard). Applique sanitize_revit_name
        sur le résultat."""
        if RenameService is not None:
            rename = RenameService(prefixe=prefixe, rechercher=rechercher,
                                   remplacer=remplacer, suffixe=suffixe,
                                   use_regex=True)
            new_name = rename.apply(source)
        else:
            new_name = prefixe + source.replace(rechercher, remplacer) + suffixe
        return sanitize_revit_name(new_name)

    def _apply_unique(self, get_current, set_value, target):
        """Assigne `target` en gérant les collisions de noms/numéros.

        No-op si `target` == valeur courante du nouvel élément. Sinon tente
        `target`, puis `target (2)`, `target (3)`… (candidat toujours basé sur
        le target original) jusqu'au premier succès. Garde-fou : abandonne
        après ~999 essais (valeur courante conservée)."""
        if target == get_current():
            return
        try:
            set_value(target)
            return
        except Exception:
            pass
        for n in range(2, 1000):
            candidate = u'{0} ({1})'.format(target, n)
            try:
                set_value(candidate)
                return
            except Exception:
                continue

    def duplicate(self, sheets, options):
        """Duplique chaque feuille de `sheets` (list de ViewSheet) selon
        `options` (DuplicationOptions). Retourne le nombre de feuilles créées."""
        created = 0
        with revit_transaction(self._doc, u'Dupliquer les feuilles'):
            for sheet in sheets:
                self._duplicate_one(sheet, options)
                created += 1
        return created

    # ====================================================================
    # MISE A JOUR DU NOMMAGE
    # ====================================================================

    def update_view_name(self, view, new_view, options):
        # type:(ViewSheet, ViewSheet, object) -> None
        """
        :param view:       Vue en cours de duplication
        :param new_view:   Nouvelle vue créée.
        :param options:    DuplicationOptions
        :return:
        """
        # NOM CIBLE DERIVE DE LA VUE SOURCE (regex + tokens via RenameService)
        new_name = self._resolve_name(view.Name, options.view_prefix,
                                      options.view_find, options.view_replace,
                                      options.view_suffix)

        def _get():
            return new_view.Name

        def _set(value):
            new_view.Name = value

        self._apply_unique(_get, _set, new_name)

    def update_sheet_name(self, sheet, new_sheet, options):
        # type:(ViewSheet, ViewSheet, object) -> None
        """
        :param sheet:       Feuille en cours de duplication
        :param new_sheet:   Nouvelle feuille créée.
        :param options:     DuplicationOptions
        :return:
        """
        # NOM CIBLE DERIVE DU NOM DE FEUILLE SOURCE (regex + tokens)
        new_name = self._resolve_name(sheet.Name, options.name_prefix,
                                      options.name_find, options.name_replace,
                                      options.name_suffix)

        def _get():
            return new_sheet.Name

        def _set(value):
            new_sheet.Name = value

        self._apply_unique(_get, _set, new_name)

    def update_sheet_number(self, sheet, new_sheet, options):
        # type:(ViewSheet, ViewSheet, object) -> None
        """
        :param sheet:       Feuille en cours de duplication
        :param new_sheet:   Nouvelle feuille créée.
        :param options:     DuplicationOptions
        :return:
        """
        # NUMERO CIBLE DERIVE DU NUMERO DE FEUILLE SOURCE (regex + tokens)
        new_name = self._resolve_name(sheet.SheetNumber, options.number_prefix,
                                      options.number_find, options.number_replace,
                                      options.number_suffix)

        def _get():
            return new_sheet.SheetNumber

        def _set(value):
            new_sheet.SheetNumber = value

        self._apply_unique(_get, _set, new_name)

    # ====================================================================
    # FONCTIONS DE DUPLICATION
    # ====================================================================

    def duplicate_schedules(self, sheet, new_sheet, options):
        # type:(ViewSheet, ViewSheet, object) -> None
        """Duplique les <Nomenclatures> de la feuille d'origine vers la nouvelle."""

        schedules_on_sheet = []
        schedules = FilteredElementCollector(self._doc).OfCategory(BuiltInCategory.OST_ScheduleGraphics).ToElements()

        # Loop schedules s=scheduleSheetInstance
        for s in schedules:
            if s.OwnerViewId == sheet.Id:
                if not s.IsTitleblockRevisionSchedule:
                    origin = s.Point

                    # USE EXISTING
                    if options.use_existing_schedules:
                        schedule_view_id = s.ScheduleId

                    # DUPLICATE
                    else:
                        scheduleId = s.ScheduleId  # s= scheduleSheetInstance
                        if scheduleId == ElementId.InvalidElementId:
                            continue

                        viewSchedule = self._doc.GetElement(scheduleId)
                        schedule_view_id = viewSchedule.Duplicate(ViewDuplicateOption.Duplicate)
                        # NAMING?

                    ScheduleSheetInstance.Create(self._doc, new_sheet.Id, schedule_view_id, origin)

    def duplicate_legends(self, sheet, new_sheet, options):
        # type:(ViewSheet, ViewSheet, object) -> None
        """Duplique les <Légendes> de la feuille d'origine vers la nouvelle."""

        viewports_ids = sheet.GetAllViewports()
        for viewport_id in viewports_ids:

            viewport = self._doc.GetElement(viewport_id)
            viewport_type_id = viewport.GetTypeId()
            viewport_origin = viewport.GetBoxCenter()
            view_id = viewport.ViewId
            view = self._doc.GetElement(view_id)
            new_view = None

            # Legends
            if view.ViewType == ViewType.Legend:
                legend_view = view

                if not options.use_existing_legends:
                    # DUPLICATE LEGEND
                    legend_view_id = view.Duplicate(ViewDuplicateOption.WithDetailing)  # Duplique la légende avec détails
                    legend_view = self._doc.GetElement(legend_view_id)

                # PLACE NEW VIEWS ON A NEW SHEET
                new_viewport = Viewport.Create(self._doc, new_sheet.Id, legend_view.Id, viewport_origin)
                if new_viewport:
                    new_viewport_type_id = new_viewport.GetTypeId()

                    # SET SAME VIEWPORT TYPE
                    if viewport_type_id != new_viewport_type_id:
                        new_viewport.ChangeTypeId(viewport_type_id)

    def duplicate_views(self, sheet, new_sheet, options):
        # type:(ViewSheet, ViewSheet, object) -> None
        """Duplique les <Vues (ViewPlan, ViewSection, View3D...)> de la feuille d'origine vers la nouvelle."""
        viewports_ids = sheet.GetAllViewports()
        for viewport_id in viewports_ids:
            viewport = self._doc.GetElement(viewport_id)
            viewport_type_id = viewport.GetTypeId()
            viewport_origin = viewport.GetBoxCenter()
            view_id = viewport.ViewId
            view = self._doc.GetElement(view_id)
            new_view = None

            # Legends
            if view.ViewType == ViewType.Legend:
                # IGNORE LEGENDS (they have their own method)
                continue

            elif view.ViewType == ViewType.ThreeD and self._view_dup_option(options.view_duplicate_option) == ViewDuplicateOption.AsDependent:
                new_view_id = view.Duplicate(ViewDuplicateOption.Duplicate)
                new_view = self._doc.GetElement(new_view_id)

            # else (ViewPlan,ViewSection,View3D, ViewDrafting, View)
            else:
                new_view_id = view.Duplicate(self._view_dup_option(options.view_duplicate_option))
                new_view = self._doc.GetElement(new_view_id)

            if new_view:
                # RENAME
                self.update_view_name(view, new_view, options)
                try:
                    # PLACE NEW VIEWS ON A NEW SHEET
                    new_viewport = Viewport.Create(self._doc, new_sheet.Id, new_view.Id, viewport_origin)
                    new_viewport_type_id = new_viewport.GetTypeId()

                    # SET SAME VIEWPORT TYPE
                    if viewport_type_id != new_viewport_type_id:
                        new_viewport.ChangeTypeId(viewport_type_id)
                except:
                    pass

    def duplicate_elements(self, sourceView, elements_ids, destinationView):
        # type:(View, list, View) -> None
        """Fonction répétée pour dupliquer les éléments donnés d'une View/ViewSheet vers une autre.
        :param sourceView:      Vue où se trouvent les éléments.
        :param elements_ids:    Liste des ids d'éléments à copier
        :param destinationView: Vue vers laquelle les éléments seront copiés.
        :return: None"""

        # Prepare parameters
        elementsToCopy = List[ElementId](elements_ids)
        additionalTransform = None
        copy_options = CopyPasteOptions()

        # COPY ELEMENTS
        if elementsToCopy:
            ElementTransformUtils.CopyElements(sourceView,
                                                elementsToCopy,
                                                destinationView,
                                                additionalTransform,
                                                copy_options)

    def duplicate_lines(self, sheet, new_sheet):
        # type:(ViewSheet, ViewSheet) -> None
        """Duplique les <Lignes> de la feuille d'origine vers la nouvelle."""
        lines_on_sheet = FilteredElementCollector(self._doc, sheet.Id).OfCategory(BuiltInCategory.OST_Lines).ToElementIds()
        self.duplicate_elements(sheet, lines_on_sheet, new_sheet)

    def duplicate_clouds(self, sheet, new_sheet):
        # type:(ViewSheet, ViewSheet) -> None
        """Duplique les <Cartouches de révision> de la feuille d'origine vers la nouvelle."""
        categories = [BuiltInCategory.OST_RevisionClouds,
                      BuiltInCategory.OST_RevisionCloudTags]
        categories_list = List[BuiltInCategory](categories)
        filter = ElementMulticategoryFilter(categories_list)
        cloud_and_tags_ids = FilteredElementCollector(self._doc, sheet.Id).WherePasses(filter).ToElementIds()
        self.duplicate_elements(sheet, cloud_and_tags_ids, new_sheet)

    def duplicate_images(self, sheet, new_sheet):
        # type:(ViewSheet, ViewSheet) -> None
        """Duplique les <Images> de la feuille d'origine vers la nouvelle."""
        images_on_sheet = FilteredElementCollector(self._doc, sheet.Id).OfCategory(BuiltInCategory.OST_RasterImages).ToElementIds()
        self.duplicate_elements(sheet, images_on_sheet, new_sheet)

    def duplicate_text(self, sheet, new_sheet):
        # type:(ViewSheet, ViewSheet) -> None
        """Duplique les <Notes de texte> de la feuille d'origine vers la nouvelle."""
        text_on_sheet = FilteredElementCollector(self._doc, sheet.Id).OfCategory(BuiltInCategory.OST_TextNotes).ToElementIds()
        self.duplicate_elements(sheet, text_on_sheet, new_sheet)

    def duplicate_dimensons(self, sheet, new_sheet):
        # type:(ViewSheet, ViewSheet) -> None
        """Duplique les <Cotes> de la feuille d'origine vers la nouvelle."""
        dimensions_on_sheet = FilteredElementCollector(self._doc, sheet.Id).OfCategory(BuiltInCategory.OST_Dimensions).ToElementIds()
        self.duplicate_elements(sheet, dimensions_on_sheet, new_sheet)

    def duplicate_symbols(self, sheet, new_sheet):
        # type:(ViewSheet, ViewSheet) -> None
        """Duplique les <Symboles> de la feuille d'origine vers la nouvelle."""
        symbols_on_sheet = FilteredElementCollector(self._doc, sheet.Id).OfCategory(BuiltInCategory.OST_GenericAnnotation).ToElementIds()
        self.duplicate_elements(sheet, symbols_on_sheet, new_sheet)

    def duplicate_dwgs(self, sheet, new_sheet):
        # type:(ViewSheet, ViewSheet) -> None
        """Duplique les <DWG> de la feuille d'origine vers la nouvelle."""
        dwgs = FilteredElementCollector(self._doc, sheet.Id).OfClass(ImportInstance).ToElementIds()
        self.duplicate_elements(sheet, dwgs, new_sheet)

    def _duplicate_one(self, sheet, options):
        """Corps par feuille de l'ancienne `duplicate_selected_sheets` (sans
        transaction, gérée par `duplicate()`)."""

        # TITLE BLOCK
        title_block = self.get_sheet_title_block(sheet)
        title_block_id = title_block.GetTypeId() if title_block else ElementId.InvalidElementId

        # CREATE SHEET
        if title_block:
            new_sheet = ViewSheet.Create(self._doc, title_block.GetTypeId())
        else:
            new_sheet = ViewSheet.Create(self._doc, ElementId.InvalidElementId)

        # SHEET NUMBER
        self.update_sheet_number(sheet, new_sheet, options)

        # SHEET NAME
        self.update_sheet_name(sheet, new_sheet, options)

        # DUPLICATE VIEWPORTS  [Legends / ViewPlan,ViewSection,View3D]
        if options.include_views:
            self.duplicate_views(sheet, new_sheet, options)

        # DUPLICATE LEGENDS
        if options.include_legends:
            self.duplicate_legends(sheet, new_sheet, options)

        # DUPLICATE SCHEDULE
        if options.include_schedules:
            self.duplicate_schedules(sheet, new_sheet, options)

        # DUPLICATE IMAGES
        if options.include_images:
            self.duplicate_images(sheet, new_sheet)

        # DUPLICATE LINES
        if options.include_lines:
            self.duplicate_lines(sheet, new_sheet)

        # DUPLICATE CLOUDS
        if options.include_clouds:
            self.duplicate_clouds(sheet, new_sheet)

        # DUPLICATE Text
        if options.include_text:
            self.duplicate_text(sheet, new_sheet)

        # DUPLICATE DWGs
        if options.include_dwgs:
            self.duplicate_dwgs(sheet, new_sheet)

        # DUPLICATE SYMBOLS
        if options.include_symbols:
            self.duplicate_symbols(sheet, new_sheet)

        # DUPLICATE DIMENSIONS
        if options.include_dimensions:
            self.duplicate_dimensons(sheet, new_sheet)

        # SET ADDITIONAL REVISIONS
        if options.include_additional_revisions:
            self.set_additional_revisions_on_sheet(sheet, new_sheet)

    def set_additional_revisions_on_sheet(self, sheet, new_sheet):
        # type:(ViewSheet, ViewSheet) -> None
        """Récupère les révisions additionnelles et les ajoute à la feuille
        dupliquée si elles existent.
        :param sheet:
        :param new_sheet:
        :return: """
        additional_revisions_ids = sheet.GetAdditionalRevisionIds()
        if additional_revisions_ids:
            new_sheet.SetAdditionalRevisionIds(additional_revisions_ids)

    def get_sheet_title_block(self, sheet):
        """Récupère le cartouche d'une feuille.
        :param sheet:   ViewSheet
        :return:        élément cartouche ou None.
        """
        all_TitleBlocks = FilteredElementCollector(self._doc).OfCategory(BuiltInCategory.OST_TitleBlocks).WhereElementIsNotElementType().ToElements()
        for title_block in all_TitleBlocks:
            if title_block.OwnerViewId == sheet.Id:
                return title_block
        return None
