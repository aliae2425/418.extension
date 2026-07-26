# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import contextlib

try:
    from Autodesk.Revit.DB import Transaction
except Exception:
    Transaction = None


@contextlib.contextmanager
def revit_transaction(doc, name):
    """Context manager de transaction Revit.

    Ouvre une `Transaction`, la valide (`Commit`) en sortie normale, ou
    l'annule (`RollBack`) puis ré-émet si une exception traverse le bloc.

        with revit_transaction(doc, u'Dupliquer les feuilles'):
            ...  # modifications du document
    """
    if Transaction is None:
        raise RuntimeError(u'API Revit indisponible : Transaction introuvable.')
    t = Transaction(doc, name)
    t.Start()
    try:
        yield t
    except Exception:
        t.RollBack()
        raise
    else:
        t.Commit()
