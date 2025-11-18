# -*- coding: utf-8 -*-
# Service de mise à jour du statut (collection et détails) dans la grille
# - Enrobe les fonctions UI existantes pour découpler la logique

class StatusUpdateService(object):
    def __init__(self, ui_window=None):
        self._ui = ui_window
        try:
            from ...GUI import _set_collection_status, _set_detail_status, _refresh_collection_grid
        except Exception:
            _set_collection_status = None  # type: ignore
            _set_detail_status = None  # type: ignore
            _refresh_collection_grid = None  # type: ignore
        self._set_coll = _set_collection_status
        self._set_det = _set_detail_status
        self._refresh = _refresh_collection_grid

    # Met à jour le statut d'une collection
    def collection(self, name, state):
        if self._ui is None or self._set_coll is None:
            return
        try:
            self._set_coll(self._ui, name, state)
            if self._refresh is not None:
                self._refresh(self._ui)
        except Exception:
            pass

    # Met à jour le statut d'une feuille/détail
    def detail(self, collection, name, fmt, state):
        if self._ui is None or self._set_det is None:
            return
        try:
            self._set_det(self._ui, collection, name, fmt, state)
            if self._refresh is not None:
                self._refresh(self._ui)
        except Exception:
            pass
