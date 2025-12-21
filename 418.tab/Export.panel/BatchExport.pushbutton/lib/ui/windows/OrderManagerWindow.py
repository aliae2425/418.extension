# -*- coding: utf-8 -*-
from pyrevit import forms
from ..helpers.UIResourceLoader import UIResourceLoader

class OrderManagerWindow(forms.WPFWindow):
    def __init__(self, xaml_path, items, is_dark_mode=False):
        forms.WPFWindow.__init__(self, xaml_path)
        
        # Load resources (styles, colors)
        UIResourceLoader(self).merge_all()
        
        # Apply dark mode if needed
        if is_dark_mode:
            try:
                from ...core.AppPaths import AppPaths
                paths = AppPaths()
                from System.Windows import ResourceDictionary
                from System import Uri, UriKind
                
                dark_colors = paths.resource_path('ColorsDark.xaml')
                dark_styles = paths.resource_path('StylesDark.xaml')
                
                for path in [dark_colors, dark_styles]:
                    rd = ResourceDictionary()
                    rd.Source = Uri(path, UriKind.Absolute)
                    self.Resources.MergedDictionaries.Add(rd)
            except Exception:
                pass
        
        self._items = list(items) # Copy list
        self._update_orders()
        
        self.ItemsList.ItemsSource = self._items
        self.response = None

    def _update_orders(self):
        for i, item in enumerate(self._items):
            item['Order'] = i + 1

    def OnUpClick(self, sender, args):
        idx = self.ItemsList.SelectedIndex
        if idx > 0:
            item = self._items.pop(idx)
            self._items.insert(idx - 1, item)
            self._update_orders()
            self.ItemsList.Items.Refresh()
            self.ItemsList.SelectedIndex = idx - 1

    def OnDownClick(self, sender, args):
        idx = self.ItemsList.SelectedIndex
        if idx < len(self._items) - 1 and idx != -1:
            item = self._items.pop(idx)
            self._items.insert(idx + 1, item)
            self._update_orders()
            self.ItemsList.Items.Refresh()
            self.ItemsList.SelectedIndex = idx + 1

    def OnOkClick(self, sender, args):
        self.response = self._items
        self.Close()

    def OnCancelClick(self, sender, args):
        self.Close()
