# -*- coding: utf-8 -*-
"""Fenêtre modale Piker extraite dans un module dédié.

Gère la sélection de paramètres, l'édition de préfix/suffix
et la persistance via le module naming.
"""

import os
from pyrevit import forms
from .naming import load_pattern, save_pattern, build_pattern_from_rows
from .config import UserConfigStore as UC

# Feuille de style XAML
GUI_FILE = os.path.join('GUI', 'Piker.xaml')


def _get_piker_xaml_path():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(base_dir, GUI_FILE)


class PikerWindow(forms.WPFWindow):
    def __init__(self, kind='sheet', title=u"Piker"):
        forms.WPFWindow.__init__(self, _get_piker_xaml_path())
        self._kind = kind  # 'sheet' | 'set'
        try:
            self.Title = title
        except Exception:
            pass
        # Etat interne
        self._available_all = []
        self._available_filtered = []
        self._selected_rows = []  # dict rows
        # Boutons OK/Annuler
        try:
            if hasattr(self, 'OkButton'):
                self.OkButton.Click += self._on_ok
            if hasattr(self, 'CancelButton'):
                self.CancelButton.Click += self._on_cancel
        except Exception:
            pass
        # Handlers
        try:
            if hasattr(self, 'AddParamButton'):
                self.AddParamButton.Click += self._on_add_param
            if hasattr(self, 'RemoveParamButton'):
                self.RemoveParamButton.Click += self._on_remove_param
            if hasattr(self, 'ScopeCombo'):
                self.ScopeCombo.SelectionChanged += self._on_scope_changed
        except Exception:
            pass
        # Charger l'existant
        patt, rows = load_pattern(self._kind)
        self._selected_rows = rows or []
        self._reload_selected_grid()
        self._refresh_preview()

    # API publique
    def load_params(self, names):
        self._available_all = list(names or [])
        self._apply_scope_filter()
        self._refresh_preview()

    # XAML events (DataGrid template textboxes hook these)
    def ParamCell_LostFocus(self, sender, args):
        self._refresh_preview()

    def ParamCell_TextChanged(self, sender, args):
        # Optionnel: rafraîchi en live
        self._refresh_preview()

    # Internals
    def _on_ok(self, sender, args):
        patt = build_pattern_from_rows(self._selected_rows)
        save_pattern(self._kind, patt, self._selected_rows)
        try:
            self.Close()
        except Exception:
            pass

    def _on_cancel(self, sender, args):
        try:
            self.Close()
        except Exception:
            pass

    def _apply_scope_filter(self):
        # Pour l'instant: pas de filtre spécifique
        self._available_filtered = list(self._available_all)
        if hasattr(self, 'AvailableParamsList'):
            try:
                self.AvailableParamsList.Items.Clear()
                for n in self._available_filtered:
                    self.AvailableParamsList.Items.Add(n)
            except Exception:
                pass

    def _on_scope_changed(self, sender, args):
        self._apply_scope_filter()
        self._refresh_preview()

    def _on_add_param(self, sender, args):
        try:
            sel = getattr(self.AvailableParamsList, 'SelectedItem', None)
            if sel and not any(r.get('Name') == sel for r in self._selected_rows):
                self._selected_rows.append({'Name': sel, 'Prefix': '', 'Suffix': ''})
                self._reload_selected_grid()
        except Exception:
            pass
        self._refresh_preview()

    def _on_remove_param(self, sender, args):
        try:
            grid = self.SelectedParamsGrid
            sel = getattr(grid, 'SelectedItem', None)
            if sel and isinstance(sel, dict):
                name = sel.get('Name')
                self._selected_rows = [r for r in self._selected_rows if r.get('Name') != name]
                self._reload_selected_grid()
        except Exception:
            pass
        self._refresh_preview()

    def _reload_selected_grid(self):
        grid = getattr(self, 'SelectedParamsGrid', None)
        if grid is None:
            return
        try:
            grid.Items.Clear()
        except Exception:
            pass
        for row in self._selected_rows:
            try:
                grid.Items.Add(row)
            except Exception:
                continue

    def _refresh_preview(self):
        patt = build_pattern_from_rows(self._selected_rows)
        try:
            if hasattr(self, 'PatternPreviewText'):
                self.PatternPreviewText.Text = patt or '(vide)'
        except Exception:
            pass


# Helpers

def open_modal(kind='sheet', title=u"Piker"):
    """Ouvre la fenêtre en modal et tente de charger les paramètres disponibles.
    Retourne True si affichée; la persistance est faite sur OK.
    """
    try:
        win = PikerWindow(kind=kind, title=title)
        # Charger paramètres disponibles
        try:
            # collect depuis l'API si dispo
            doc = __revit__.ActiveUIDocument.Document  # type: ignore
            from .sheets import collect_sheet_parameter_names
            names = collect_sheet_parameter_names(doc, UC('batch_export'))
            win.load_params(names)
        except Exception:
            pass
        try:
            win.ShowDialog()
        except Exception:
            win.show()
        return True
    except Exception as e:
        print('[info] Erreur ouverture Piker:', e)
        return False
