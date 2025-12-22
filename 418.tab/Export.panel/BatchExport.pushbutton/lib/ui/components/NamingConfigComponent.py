# -*- coding: utf-8 -*-
# Composant UI: configuration du nommage (boutons d'ouverture, labels)

class NamingConfigComponent(object):
    def __init__(self, pattern_store):
        self._store = pattern_store

    def load_naming_model(self, kind):
        """Charge le modèle de nommage pour un type donné.

        Retourne un dict stable (future-compatible) sans toucher à l'UI.
        """
        try:
            pattern, rows = self._store.load(kind)
        except Exception:
            pattern, rows = '', []
        return {
            'kind': kind,
            'pattern': pattern or '',
            'rows': rows or [],
        }

    def refresh_buttons(self, win):
        sheet_model = self.load_naming_model('sheet')
        set_model = self.load_naming_model('set')
        try:
            if hasattr(win, 'SheetNamingButton'):
                # Ne pas modifier Content: il doit rester "Feuilles" (UI stable).
                # On stocke le modèle dans Tag pour des usages futurs (ex: hover), sans UX additionnelle.
                win.SheetNamingButton.Tag = sheet_model
        except Exception:
            pass
        try:
            if hasattr(win, 'SetNamingButton'):
                # Ne pas modifier Content: il doit rester "Carnets" (UI stable).
                win.SetNamingButton.Tag = set_model
        except Exception:
            pass
