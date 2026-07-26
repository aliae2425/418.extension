# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from Autodesk.Revit.DB import ViewSchedule, ViewType, ViewDuplicateOption
except Exception:
    ViewSchedule = None
    ViewType = None
    ViewDuplicateOption = None

try:
    from core.transaction import revit_transaction
except Exception:
    revit_transaction = None

_VIEW_DUP_MAP = {
    u'duplicate': 'Duplicate',
    u'with_detailing': 'WithDetailing',
    u'as_dependent': 'AsDependent',
}


class ViewsDuplicationService(object):
    """Duplique des vues Revit selon un mode et un nombre de copies."""

    def __init__(self, doc):
        self._doc = doc

    def _view_dup_option(self, key):
        return getattr(ViewDuplicateOption, _VIEW_DUP_MAP.get(key, 'Duplicate'))

    def duplicate(self, views, options):
        """Duplique `views` `options.count` fois chacune. Retourne les ElementId créés."""
        new_view_ids = []
        opt = self._view_dup_option(options.view_duplicate_option)
        with revit_transaction(self._doc, u'Dupliquer les vues'):
            for view in views:
                if ViewSchedule is not None and isinstance(view, ViewSchedule):
                    for _ in range(options.count):
                        view.Duplicate(getattr(ViewDuplicateOption, 'Duplicate'))
                elif ViewType is not None and view.ViewType == ViewType.Legend:
                    for _ in range(options.count):
                        view.Duplicate(getattr(ViewDuplicateOption, 'WithDetailing'))
                else:
                    for _ in range(options.count):
                        new_view_ids.append(view.Duplicate(opt))
        return new_view_ids
