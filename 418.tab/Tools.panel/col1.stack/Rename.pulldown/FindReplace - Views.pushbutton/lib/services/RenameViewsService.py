# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from core.transaction import revit_transaction
from core.sanitize import sanitize_revit_name
from core.rename_service import RenameService


class RenameViewsService(object):
    """Renomme des vues Revit en une transaction."""

    def __init__(self, doc):
        self._doc = doc

    def rename(self, views, options):
        """Renomme chaque vue de `views` selon `options` (RenameViewOptions).
        Retourne le nombre de vues traitées."""
        svc = RenameService(
            prefixe=options.view_prefix, rechercher=options.view_find,
            remplacer=options.view_replace, suffixe=options.view_suffix,
            use_regex=True)
        count = 0
        with revit_transaction(self._doc, u'Renommer les vues'):
            for index, view in enumerate(views, start=1):
                new_name = sanitize_revit_name(svc.apply(view.Name, index=index))
                if new_name == view.Name:
                    count += 1
                    continue
                fail = 0
                candidate = new_name
                while fail < 5:
                    try:
                        view.Name = candidate
                        break
                    except Exception:
                        candidate += u'*'
                        fail += 1
                count += 1
        return count
