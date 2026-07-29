# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import contextlib

try:
    from Autodesk.Revit.DB import ViewSchedule, ViewType, ViewDuplicateOption, Transaction
except Exception:
    ViewSchedule = None
    ViewType = None
    ViewDuplicateOption = None
    Transaction = None

try:
    from core.transaction import revit_transaction
except Exception:
    revit_transaction = None

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


@contextlib.contextmanager
def _null_transaction(*args, **kwargs):
    """Context manager nul : permet d'exécuter le service hors Revit."""
    yield


def _type_label(view):
    """Étiquette de type de vue, robuste Py2/Py3 (cf. script.py)."""
    try:
        return unicode(view.ViewType)
    except Exception:
        try:
            return str(view.ViewType)
        except Exception:
            return u''


class ViewsDuplicationService(object):
    """Duplique des vues Revit selon un mode, un nombre de copies et un nommage."""

    def __init__(self, doc):
        self._doc = doc

    def _view_dup_option(self, key):
        """Retourne l'énum ViewDuplicateOption, ou la chaîne du nom hors Revit."""
        name = _VIEW_DUP_MAP.get(key, 'Duplicate')
        if ViewDuplicateOption is None:
            return name
        return getattr(ViewDuplicateOption, name)

    def _build_rename_service(self, options):
        if RenameService is None:
            return None
        return RenameService(
            prefixe=getattr(options, 'prefixe', u''),
            rechercher=getattr(options, 'rechercher', u''),
            remplacer=getattr(options, 'remplacer', u''),
            suffixe=getattr(options, 'suffixe', u''),
            use_regex=getattr(options, 'use_regex', False),
        )

    def _apply_name_unique(self, view, target):
        """Assigne `target` à `view` en gérant les collisions de noms.

        Tente d'abord `target`, puis `target (2)`, `target (3)`… jusqu'au
        succès. Garde-fou : abandonne après ~999 essais (nom par défaut
        conservé). Retourne le nom effectivement retenu.
        """
        try:
            view.Name = target
            return target
        except Exception:
            pass
        for n in range(2, 1000):
            candidate = u'{0} ({1})'.format(target, n)
            try:
                view.Name = candidate
                return candidate
            except Exception:
                continue
        return view.Name

    def _process_copy(self, view, opt, rename, index, new_view_ids):
        """Duplique `view` une fois avec `opt`, renomme si nécessaire,
        capture l'id. `index` alimente le token {n}."""
        nom_source = view.Name
        new_id = view.Duplicate(opt)
        new_view_ids.append(new_id)
        copie = self._doc.GetElement(new_id)
        if copie is None or rename is None:
            return
        ctx = {u'type': _type_label(view)}
        target = rename.apply(nom_source, index=index, context=ctx)
        # Renommer uniquement si le nom cible diffère du nom source :
        # évite de renommer quand l'utilisateur n'a rien saisi et reste
        # cohérent avec PreviewGroupVM.IsRenamed.
        if target and target != nom_source:
            self._apply_name_unique(copie, target)

    def duplicate(self, views, options):
        """Duplique `views` `options.count` fois chacune, applique le
        renommage, et retourne les ElementId créés (schedules & legends inclus)."""
        new_view_ids = []
        rename = self._build_rename_service(options)
        opt_default = self._view_dup_option(options.view_duplicate_option)
        opt_schedule = self._view_dup_option(u'duplicate')
        opt_legend = self._view_dup_option(u'with_detailing')

        # Transaction réelle seulement si l'API Revit est disponible ;
        # sinon context manager nul pour permettre l'exécution hors Revit.
        if revit_transaction is not None and Transaction is not None:
            cm = revit_transaction
        else:
            cm = _null_transaction

        with cm(self._doc, u'Dupliquer les vues'):
            for view in views:
                if ViewSchedule is not None and isinstance(view, ViewSchedule):
                    opt = opt_schedule
                elif ViewType is not None and view.ViewType == ViewType.Legend:
                    opt = opt_legend
                else:
                    opt = opt_default
                for i in range(1, options.count + 1):
                    self._process_copy(view, opt, rename, i, new_view_ids)
        return new_view_ids
