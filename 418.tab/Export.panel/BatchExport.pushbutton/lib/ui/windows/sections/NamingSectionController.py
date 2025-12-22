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
                self._win.SheetNamingButton.MouseEnter += self._on_sheet_hover_enter
                self._win.SheetNamingButton.MouseLeave += self._on_sheet_hover_leave
            if hasattr(self._win, 'SetNamingButton'):
                self._win.SetNamingButton.Click += self._on_open_set_naming
                self._win.SetNamingButton.MouseEnter += self._on_set_hover_enter
                self._win.SetNamingButton.MouseLeave += self._on_set_hover_leave
        except Exception:
            pass

    def _set_hover_text(self, text):
        try:
            from ...helpers.HoverOverlay import set_hover_text
            set_hover_text(self._win, text)
        except Exception:
            pass

    def _pattern_from_button(self, btn):
        try:
            model = getattr(btn, 'Tag', None)
            if isinstance(model, dict):
                patt = model.get('pattern', '')
            else:
                patt = ''
        except Exception:
            patt = ''
        return patt or '...'

    def _on_sheet_hover_enter(self, s, a):
        try:
            patt = self._pattern_from_button(s)
            self._set_hover_text(u"Feuilles : {}".format(patt))
        except Exception:
            pass

    def _on_sheet_hover_leave(self, s, a):
        self._set_hover_text('')

    def _on_set_hover_enter(self, s, a):
        try:
            patt = self._pattern_from_button(s)
            self._set_hover_text(u"Carnets : {}".format(patt))
        except Exception:
            pass

    def _on_set_hover_leave(self, s, a):
        self._set_hover_text('')

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
