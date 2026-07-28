# -*- coding: utf-8 -*-
from __future__ import unicode_literals

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
    from services.RenameService import RenameService


class RenameSheetsService(object):
    """Renomme des feuilles Revit (numéro et/ou nom) en une transaction."""

    def __init__(self, doc):
        self._doc = doc

    def rename(self, sheets, options):
        """Renomme chaque feuille de `sheets` selon `options`
        (RenameSheetOptions). Retourne le nombre de feuilles traitées."""
        svc_number = RenameService(
            prefixe=options.number_prefix, rechercher=options.number_find,
            remplacer=options.number_replace, suffixe=options.number_suffix,
            use_regex=True)
        svc_name = RenameService(
            prefixe=options.name_prefix, rechercher=options.name_find,
            remplacer=options.name_replace, suffixe=options.name_suffix,
            use_regex=True)
        count = 0
        with revit_transaction(self._doc, u'Renommer les feuilles'):
            for index, sheet in enumerate(sheets, start=1):
                self._rename_number(sheet, svc_number, index)
                self._rename_name(sheet, svc_name, index)
                count += 1
        return count

    def _rename_number(self, sheet, svc, index=1):
        new_val = sanitize_revit_name(svc.apply(sheet.SheetNumber, index=index))
        if new_val == sheet.SheetNumber:
            return
        fail = 0
        candidate = new_val
        while fail < 5:
            try:
                sheet.SheetNumber = candidate
                return
            except Exception:
                candidate += u'*'
                fail += 1

    def _rename_name(self, sheet, svc, index=1):
        new_val = sanitize_revit_name(svc.apply(sheet.Name, index=index))
        if new_val == sheet.Name:
            return
        fail = 0
        candidate = new_val
        while fail < 5:
            try:
                sheet.Name = candidate
                return
            except Exception:
                candidate += u'*'
                fail += 1
