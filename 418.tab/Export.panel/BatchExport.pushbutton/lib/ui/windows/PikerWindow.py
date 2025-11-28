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
        except Exception:
            pass
        # Load existing rows
        try:
            patt, rows = _naming_store().load(self._kind)
        except Exception:
            patt, rows = '', []
        
        # Upgrade rows to include DisplayName if missing
        self._selected_rows = []
        if rows:
            from ...utils.BipTranslator import BipTranslator
            for r in rows:
                nm = r.get('Name', '')
                dn = r.get('DisplayName', '')
                if not dn:
                    if nm.startswith('BIP:'):
                        bip_name = nm[4:]
                        dn = BipTranslator.get_localized_name(bip_name)
                    else:
                        dn = nm
                r['DisplayName'] = dn
                self._selected_rows.append(r)

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
                self._available_collection = repo.collect_params_extended(doc, scope='collection')
            except Exception:
                self._available_collection = []
            try:
                self._available_project = repo.collect_params_extended(doc, scope='project')
            except Exception:
                self._available_project = []
            try:
                self._available_sheet = repo.collect_params_extended(doc, scope='sheet')
            except Exception:
                self._available_sheet = []
        else:
            self._available_collection = []
            self._available_project = []
            self._available_sheet = []
        # Union
        all_union = {}
        for lst in (self._available_project, self._available_collection, self._available_sheet):
            for item in lst:
                if item and item.get('Name'):
                    all_union[item['Name']] = item
        
        try:
            self._available_all = sorted(list(all_union.values()), key=lambda s: s['Name'].lower())
        except Exception:
            self._available_all = list(all_union.values())
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
            # sel is now a dict {'Name':..., 'Id':...}
            if sel:
                p_id = sel.get('Id')
                p_name = sel.get('Name')
                if p_id and not any(r.get('Name') == p_id for r in self._selected_rows):
                    self._selected_rows.append({'Name': p_id, 'DisplayName': p_name, 'Prefix': '', 'Suffix': ''})
                    self._reload_selected_list()
        except Exception:
            pass
        self._refresh_preview()

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
        try:
            self._available_filtered = sorted(filtered, key=lambda s: s['Name'].lower())
        except Exception:
            self._available_filtered = filtered
        if hasattr(self, 'AvailableParamsList'):
            try:
                self.AvailableParamsList.Items.Clear()
                self.AvailableParamsList.DisplayMemberPath = "Name"
                for n in self._available_filtered:
                    self.AvailableParamsList.Items.Add(n)
            except Exception:
                pass

    def _on_add_param(self, sender, args):
        try:
            sel = getattr(self.AvailableParamsList, 'SelectedItem', None)
            if sel:
                p_id = sel.get('Id')
                p_name = sel.get('Name')
                if p_id and not any(r.get('Name') == p_id for r in self._selected_rows):
                    self._selected_rows.append({'Name': p_id, 'DisplayName': p_name, 'Prefix': '', 'Suffix': ''})
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
