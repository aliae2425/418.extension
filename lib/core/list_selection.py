# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class ListSelectionService(object):
    """Gère la sélection multi-items avec shift-click et ctrl-click.

    Aucune dépendance Revit ou WPF — testable en Python pur.
    Items = tout objet dont la propriété de sélection (``prop``, ``IsSelected``
    par défaut) est accessible via getattr/setattr.
    """

    def __init__(self, prop=u'IsSelected'):
        self._prop = prop
        self._anchor = -1   # indice de la dernière sélection « simple »

    def reset(self):
        """Réinitialise l'ancre (à appeler lors d'un rechargement de liste)."""
        self._anchor = -1

    def _set(self, item, value):
        try:
            setattr(item, self._prop, value)
        except Exception:
            pass

    def handle_click(self, items, index, shift=False, ctrl=False):
        """Modifie la sélection en réponse à un clic sur l'item ``index``.

        Règles :
        - Sans modificateur : désélectionne tout, sélectionne uniquement
          ``index``, déplace l'ancre sur ``index``.
        - Ctrl  : bascule ``index`` uniquement, déplace l'ancre.
        - Shift : sélectionne la plage [ancre, index] inclusive, sans effacer
                  les sélections hors de la plage, sans déplacer l'ancre.
        """
        items = list(items or [])
        if not items or index < 0 or index >= len(items):
            return

        if shift and self._anchor >= 0:
            lo = min(self._anchor, index)
            hi = max(self._anchor, index)
            for i, item in enumerate(items):
                self._set(item, lo <= i <= hi)
            # ancre inchangée pour des shift consécutifs
        elif ctrl:
            self._set(items[index], not bool(getattr(items[index], self._prop, False)))
            self._anchor = index
        else:
            for i, item in enumerate(items):
                self._set(item, i == index)
            self._anchor = index
