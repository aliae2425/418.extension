# -*- coding: utf-8 -*-
# Composant UI: configuration du nommage (boutons d'ouverture, labels)

class NamingConfigComponent(object):
    def __init__(self, pattern_store):
        self._store = pattern_store

    def refresh_buttons(self, win):
        try:
            sheet_patt, _ = self._store.load('sheet')
        except Exception:
            sheet_patt = ''
        try:
            set_patt, _ = self._store.load('set')
        except Exception:
            set_patt = ''
        try:
            if hasattr(win, 'SheetNamingButton'):
                win.SheetNamingButton.Content = sheet_patt or '...'
        except Exception:
            pass
        try:
            if hasattr(win, 'SetNamingButton'):
                win.SetNamingButton.Content = set_patt or '...'
        except Exception:
            pass
