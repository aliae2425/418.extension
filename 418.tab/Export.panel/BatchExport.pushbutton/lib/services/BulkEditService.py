# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class BulkEditService(object):
    """Service générique pour l'édition en masse d'une propriété sur
    une multi-sélection d'items quelconques.

    Aucune dépendance Revit ou WPF — testable en Python pur.
    Items = tout objet dont les propriétés sont accessibles via getattr/setattr.
    """

    def get_selected(self, items, prop=u'Selected'):
        """Retourne les items dont `prop` est truthy."""
        return [it for it in (items or []) if getattr(it, prop, False)]

    def apply(self, items, prop, value):
        """Fixe `prop = value` sur tous les items (silencieux si setattr échoue)."""
        for it in (items or []):
            try:
                setattr(it, prop, value)
            except Exception:
                pass

    def toggle(self, items, prop):
        """Bascule `prop` sur la sélection.

        Règle : si TOUS les items ont `prop=True` → met tout à False.
                sinon                               → met tout à True.
        Idempotent sur une liste vide.
        """
        items = list(items or [])
        if not items:
            return
        all_on = all(getattr(it, prop, False) for it in items)
        self.apply(items, prop, not all_on)

    def select_all(self, items, prop=u'Selected'):
        """Met `prop = True` sur tous les items."""
        self.apply(items, prop, True)

    def deselect_all(self, items, prop=u'Selected'):
        """Met `prop = False` sur tous les items."""
        self.apply(items, prop, False)
