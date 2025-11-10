# -*- coding: utf-8 -*-
"""Fenêtre modale Piker extraite dans un module dédié.

Gère la sélection de paramètres, l'édition de préfix/suffix
et la persistance via le module naming.
"""

import os
from pyrevit import forms
from .naming import *
from .sheets import *
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
        self._reload_selected_list()
        self._refresh_preview()

    # API publique
    def load_params(self, names):
        """Charge la liste initiale (portée Collection)."""
        self._available_collection = list(names or [])
        # Charger aussi projet & feuille
        try:
            doc = __revit__.ActiveUIDocument.Document  # type: ignore
        except Exception:
            doc = None
        if doc is not None:
            try:
                self._available_project = picker_collect_project_parameter_names(doc, UC('batch_export'))
            except Exception:
                self._available_project = []
            try:
                self._available_sheet = picker_collect_sheet_instance_parameter_names(doc, UC('batch_export'))
            except Exception:
                self._available_sheet = []
        else:
            self._available_project = []
            self._available_sheet = []
        # Tout = union dédupliquée
        all_union = set()
        for lst in (self._available_project, self._available_collection, self._available_sheet):
            for n in lst:
                if n:
                    all_union.add(n)
        self._available_all = sorted(list(all_union), key=lambda s: s.lower())
        self._apply_scope_filter()
        self._refresh_preview()

    # XAML events (DataGrid template textboxes hook these)
    def ParamCell_LostFocus(self, sender, args):
        self._refresh_preview()

    def ParamCell_TextChanged(self, sender, args):
        # Optionnel: rafraîchi en live
        self._refresh_preview()

    def AvailableParamsList_DoubleClick(self, sender, args):
        # Ajoute l'item double-cliqué comme si on appuyait sur Ajouter
        try:
            sel = getattr(self.AvailableParamsList, 'SelectedItem', None)
            if sel and not any(r.get('Name') == sel for r in self._selected_rows):
                self._selected_rows.append({'Name': sel, 'Prefix': '', 'Suffix': ''})
                self._reload_selected_list()
        except Exception:
            pass
        self._refresh_preview()

    def SelectedParamsList_DoubleClick(self, sender, args):
        # Retire l'item double-cliqué côté droit
        try:
            lst = self.SelectedParamsList
            sel = getattr(lst, 'SelectedItem', None)
            if sel and isinstance(sel, dict):
                name = sel.get('Name')
                self._selected_rows = [r for r in self._selected_rows if r.get('Name') != name]
                self._reload_selected_list()
        except Exception:
            pass
        self._refresh_preview()

    def MoveUpButton_Click(self, sender, args):
        try:
            lst = self.SelectedParamsList
            sel = getattr(lst, 'SelectedItem', None)
            if not(sel and isinstance(sel, dict)):
                return
            name = sel.get('Name')
            idx = None
            for i, r in enumerate(self._selected_rows):
                if r.get('Name') == name:
                    idx = i
                    break
            if idx is None or idx <= 0:
                return
            # swap positions
            self._selected_rows[idx-1], self._selected_rows[idx] = self._selected_rows[idx], self._selected_rows[idx-1]
            self._reload_selected_list()
            # Reselect moved item
            try:
                lst.SelectedIndex = idx-1
            except Exception:
                pass
        except Exception:
            pass
        self._refresh_preview()

    def MoveDownButton_Click(self, sender, args):
        try:
            lst = self.SelectedParamsList
            sel = getattr(lst, 'SelectedItem', None)
            if not(sel and isinstance(sel, dict)):
                return
            name = sel.get('Name')
            idx = None
            for i, r in enumerate(self._selected_rows):
                if r.get('Name') == name:
                    idx = i
                    break
            if idx is None or idx >= len(self._selected_rows)-1:
                return
            # swap positions
            self._selected_rows[idx+1], self._selected_rows[idx] = self._selected_rows[idx], self._selected_rows[idx+1]
            self._reload_selected_list()
            try:
                lst.SelectedIndex = idx+1
            except Exception:
                pass
        except Exception:
            pass
        self._refresh_preview()

    def MoveTopButton_Click(self, sender, args):
        try:
            lst = self.SelectedParamsList
            sel = getattr(lst, 'SelectedItem', None)
            if not(sel and isinstance(sel, dict)):
                return
            name = sel.get('Name')
            idx = None
            for i, r in enumerate(self._selected_rows):
                if r.get('Name') == name:
                    idx = i
                    break
            if idx is None or idx <= 0:
                return
            row = self._selected_rows.pop(idx)
            self._selected_rows.insert(0, row)
            self._reload_selected_list()
            try:
                lst.SelectedIndex = 0
            except Exception:
                pass
        except Exception:
            pass
        self._refresh_preview()

    def MoveBottomButton_Click(self, sender, args):
        try:
            lst = self.SelectedParamsList
            sel = getattr(lst, 'SelectedItem', None)
            if not(sel and isinstance(sel, dict)):
                return
            name = sel.get('Name')
            idx = None
            for i, r in enumerate(self._selected_rows):
                if r.get('Name') == name:
                    idx = i
                    break
            last_index = len(self._selected_rows)-1
            if idx is None or idx >= last_index:
                return
            row = self._selected_rows.pop(idx)
            self._selected_rows.append(row)
            self._reload_selected_list()
            try:
                lst.SelectedIndex = last_index
            except Exception:
                pass
        except Exception:
            pass
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
        scope = 'Tout'
        try:
            if hasattr(self, 'ScopeCombo'):
                sel = getattr(self.ScopeCombo, 'SelectedItem', None)
                if sel is not None:
                    scope = getattr(sel, 'Content', 'Tout')
        except Exception:
            scope = 'Tout'
        if scope == 'Projet':
            filtered = list(self._available_project or [])
        elif scope == 'Collection':
            filtered = list(self._available_collection or [])
        elif scope == 'Feuille':
            filtered = list(self._available_sheet or [])
        else:  # Tout
            filtered = list(self._available_all or [])
        self._available_filtered = sorted(filtered, key=lambda s: s.lower())
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
                self._reload_selected_list()
        except Exception:
            pass
        self._refresh_preview()

    def _on_remove_param(self, sender, args):
        try:
            lst = self.SelectedParamsList
            sel = getattr(lst, 'SelectedItem', None)
            if sel and isinstance(sel, dict):
                name = sel.get('Name')
                self._selected_rows = [r for r in self._selected_rows if r.get('Name') != name]
                self._reload_selected_list()
        except Exception:
            pass
        self._refresh_preview()

    def _reload_selected_list(self):
        lst = getattr(self, 'SelectedParamsList', None)
        if lst is None:
            return
        try:
            lst.Items.Clear()
        except Exception:
            pass
        for row in self._selected_rows:
            try:
                lst.Items.Add(row)
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
            # collect paramètres Collection (base), puis charge projet & feuille via load_params
            doc = __revit__.ActiveUIDocument.Document  # type: ignore
            names_coll = picker_collect_sheet_parameter_names(doc, UC('batch_export'))
            win.load_params(names_coll)
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
