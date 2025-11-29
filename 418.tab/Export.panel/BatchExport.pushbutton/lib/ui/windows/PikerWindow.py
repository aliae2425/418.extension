# -*- coding: utf-8 -*-
# Fenêtre modale Piker re-localisée sous ui/windows, sans dépendre des facades lib/*.

from __future__ import unicode_literals

import os
from pyrevit import forms


def _naming_store():
    from ...data.naming.NamingPatternStore import NamingPatternStore
    return NamingPatternStore()


def _naming_resolver():
    from ...data.naming.NamingResolver import NamingResolver
    return NamingResolver()


def _sheet_repo():
    from ...data.sheets.SheetParameterRepository import SheetParameterRepository
    from ...core.UserConfig import UserConfig
    return SheetParameterRepository(UserConfig('batch_export'))


def _get_naming_xaml_path():
    try:
        from ...core.AppPaths import AppPaths
        paths = AppPaths()
        return os.path.join(paths.gui_root(), 'Views', 'naming.xaml')
    except Exception:
        # Fallback: compute from this file
        here = os.path.dirname(__file__)
        return os.path.normpath(os.path.join(here, '..', '..', 'GUI', 'Views', 'naming.xaml'))


class PikerWindow(forms.WPFWindow):
    def __init__(self, kind='sheet', title=u"Piker"):
        forms.WPFWindow.__init__(self, _get_naming_xaml_path())
        self._kind = kind  # 'sheet' | 'set'
        try:
            self.Title = title
        except Exception:
            pass
        
        # Update Title Text
        try:
            if hasattr(self, 'TitleText'):
                if self._kind == 'set':
                    self.TitleText.Text = "Configuration nom pour : Carnet ( PDF compiler )"
                else:
                    self.TitleText.Text = "Configuration nom pour : feuille ( PDF DWG )"
        except Exception:
            pass

        self._available_all = []
        self._available_filtered = []
        self._available_project = []
        self._available_collection = []
        self._available_sheet = []
        self._selected_rows = []
        # Buttons
        try:
            if hasattr(self, 'OkButton'):
                self.OkButton.Click += self._on_ok
            if hasattr(self, 'CancelButton'):
                self.CancelButton.Click += self._on_cancel
            if hasattr(self, 'AddParamButton'):
                self.AddParamButton.Click += self._on_add_param
            if hasattr(self, 'RemoveParamButton'):
                self.RemoveParamButton.Click += self._on_remove_param
            if hasattr(self, 'ScopeCombo'):
                self.ScopeCombo.SelectionChanged += self._on_scope_changed
            if hasattr(self, 'SearchBox'):
                self.SearchBox.TextChanged += self._on_search_changed
        except Exception:
            pass
        # Load existing rows
        try:
            patt, rows = _naming_store().load(self._kind)
        except Exception:
            patt, rows = '', []
        self._selected_rows = rows or []
        self._reload_selected_list()
        self._refresh_preview()

    def load_params(self):
        try:
            doc = __revit__.ActiveUIDocument.Document  # type: ignore
        except Exception:
            doc = None
        repo = _sheet_repo()
        if doc is not None:
            try:
                self._available_collection = repo.collect_for_collections(doc, only_boolean=False)
            except Exception:
                self._available_collection = []
            try:
                self._available_project = repo.collect_project_params(doc)
            except Exception:
                self._available_project = []
            try:
                self._available_sheet = repo.collect_sheet_instance_params(doc)
            except Exception:
                self._available_sheet = []
        else:
            self._available_collection = []
            self._available_project = []
            self._available_sheet = []
        # Union
        all_union = set()
        for lst in (self._available_project, self._available_collection, self._available_sheet):
            for n in lst:
                if n:
                    try:
                        all_union.add(n)
                    except Exception:
                        pass
        try:
            self._available_all = sorted(list(all_union), key=lambda s: s.lower())
        except Exception:
            self._available_all = list(all_union)
        self._apply_scope_filter()
        self._refresh_preview()

    # XAML events hooks
    def ParamCell_LostFocus(self, sender, args):
        self._refresh_preview()

    def ParamCell_TextChanged(self, sender, args):
        self._refresh_preview()

    def AvailableParamsList_DoubleClick(self, sender, args):
        try:
            sel = getattr(self.AvailableParamsList, 'SelectedItem', None)
            if sel and not any(r.get('Name') == sel for r in self._selected_rows):
                self._selected_rows.append({'Name': sel, 'Prefix': '', 'Suffix': ''})
                self._reload_selected_list()
        except Exception:
            pass
        self._refresh_preview()

    def SelectedParamsList_DoubleClick(self, sender, args):
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
            idx = next((i for i,r in enumerate(self._selected_rows) if r.get('Name')==name), None)
            if idx is None or idx <= 0:
                return
            self._selected_rows[idx-1], self._selected_rows[idx] = self._selected_rows[idx], self._selected_rows[idx-1]
            self._reload_selected_list()
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
            idx = next((i for i,r in enumerate(self._selected_rows) if r.get('Name')==name), None)
            if idx is None or idx >= len(self._selected_rows)-1:
                return
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
            idx = next((i for i,r in enumerate(self._selected_rows) if r.get('Name')==name), None)
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
            idx = next((i for i,r in enumerate(self._selected_rows) if r.get('Name')==name), None)
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
        patt = self._build_pattern_from_rows(self._selected_rows)
        _naming_store().save(self._kind, patt, self._selected_rows)
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
        else:
            filtered = list(self._available_all or [])

        # Apply search filter
        search_text = ''
        try:
            if hasattr(self, 'SearchBox'):
                search_text = self.SearchBox.Text
        except Exception:
            pass
        
        if search_text:
            search_text = search_text.lower()
            filtered = [n for n in filtered if search_text in n.lower()]

        try:
            self._available_filtered = sorted(filtered, key=lambda s: s.lower())
        except Exception:
            self._available_filtered = filtered
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

    def _on_search_changed(self, sender, args):
        self._apply_scope_filter()

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

    def _build_pattern_from_rows(self, rows):
        try:
            return _naming_resolver().build_pattern(rows)
        except Exception:
            return ''

    def _refresh_preview(self):
        patt = self._build_pattern_from_rows(self._selected_rows)
        try:
            if hasattr(self, 'PatternPreviewText'):
                self.PatternPreviewText.Text = patt or '(vide)'
        except Exception:
            pass


def open_modal(kind='sheet', title=u"Piker"):
    try:
        win = PikerWindow(kind=kind, title=title)
        try:
            win.load_params()
        except Exception:
            pass
        try:
            win.ShowDialog()
        except Exception:
            win.show()
        return True
    except Exception as e:
        print('[info] Erreur PikerWindow:', e)
        return False
