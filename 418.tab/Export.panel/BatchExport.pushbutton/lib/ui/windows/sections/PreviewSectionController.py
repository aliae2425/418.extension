# -*- coding: utf-8 -*-


class PreviewSectionController(object):
    def __init__(self, win, grid_component, selected_values_provider):
        self._win = win
        self._grid_comp = grid_component
        self._selected_values_provider = selected_values_provider

    def populate(self):
        try:
            self._grid_comp.populate(self._win, self._selected_values_provider())
        except Exception:
            pass

    def wire_grid_click(self):
        try:
            if hasattr(self._win, 'CollectionGrid') and self._win.CollectionGrid is not None:
                self._win.CollectionGrid.PreviewMouseLeftButtonDown += self._on_grid_click
        except Exception:
            pass

    def _on_grid_click(self, sender, e):
        try:
            from ...helpers.GridRowToggle import unselect_row_on_preview_left_click
            unselect_row_on_preview_left_click(e)
        except Exception:
            pass
