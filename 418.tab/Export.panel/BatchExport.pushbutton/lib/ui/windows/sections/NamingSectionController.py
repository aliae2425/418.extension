# -*- coding: utf-8 -*-


class NamingSectionController(object):
    def __init__(self, win, naming_component, on_preview_update=None):
        self._win = win
        self._name_comp = naming_component
        self._on_preview_update = on_preview_update

    def initialize(self):
        self.refresh_buttons()

    def refresh_buttons(self):
        try:
            self._name_comp.refresh_buttons(self._win)
        except Exception:
            pass

    def wire_buttons(self):
        try:
            if hasattr(self._win, 'SheetNamingButton'):
                self._win.SheetNamingButton.Click += self._on_open_sheet_naming
            if hasattr(self._win, 'SetNamingButton'):
                self._win.SetNamingButton.Click += self._on_open_set_naming
        except Exception:
            pass

    def _refresh(self, sender=None, args=None):
        try:
            self.refresh_buttons()
        except Exception:
            pass

        if self._on_preview_update is not None:
            try:
                self._on_preview_update()
            except Exception:
                pass

    def _on_open_sheet_naming(self, s, a):
        try:
            from ..PikerWindow import open_modal
            open_modal(kind='sheet', title=u"Nommage des feuilles", on_close=self._refresh)
            self._refresh()
        except Exception:
            pass

    def _on_open_set_naming(self, s, a):
        try:
            from ..PikerWindow import open_modal
            open_modal(kind='set', title=u"Nommage des carnets", on_close=self._refresh)
            self._refresh()
        except Exception:
            pass
