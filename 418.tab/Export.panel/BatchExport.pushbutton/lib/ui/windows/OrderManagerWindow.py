# -*- coding: utf-8 -*-
from pyrevit import forms
from ..helpers.UIResourceLoader import UIResourceLoader

class OrderManagerWindow(forms.WPFWindow):
    def __init__(self, xaml_path, items, is_dark_mode=False):
        forms.WPFWindow.__init__(self, xaml_path)

        # Fusionne windows.xaml (qui inclut toutes les ressources de couleurs/styles, y compris darkmode)
        try:
            from ...core.AppPaths import AppPaths
            from System.Windows import ResourceDictionary
            from System import Uri, UriKind
            paths = AppPaths()
            
            # Load windows.xaml (Light theme base)
            winres = ResourceDictionary()
            winres.Source = Uri('file:///' + paths.windows_xaml().replace('\\', '/').replace(':', ':/'), UriKind.Absolute)
            self.Resources.MergedDictionaries.Add(winres)

            # If dark mode, load dark resources
            if is_dark_mode:
                dark_colors_path = paths.resource_path('ColorsDark.xaml')
                dark_styles_path = paths.resource_path('StylesDark.xaml')
                
                d_colors = ResourceDictionary()
                d_colors.Source = Uri('file:///' + dark_colors_path.replace('\\', '/').replace(':', ':/'), UriKind.Absolute)
                self.Resources.MergedDictionaries.Add(d_colors)
                
                d_styles = ResourceDictionary()
                d_styles.Source = Uri('file:///' + dark_styles_path.replace('\\', '/').replace(':', ':/'), UriKind.Absolute)
                self.Resources.MergedDictionaries.Add(d_styles)

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

    def OnTopClick(self, sender, args):
        idx = self.ItemsList.SelectedIndex
        if idx > 0:
            item = self._items.pop(idx)
            self._items.insert(0, item)
            self._update_orders()
            self.ItemsList.Items.Refresh()
            self.ItemsList.SelectedIndex = 0

    def OnBottomClick(self, sender, args):
        idx = self.ItemsList.SelectedIndex
        if idx < len(self._items) - 1 and idx != -1:
            item = self._items.pop(idx)
            self._items.append(item)
            self._update_orders()
            self.ItemsList.Items.Refresh()
            self.ItemsList.SelectedIndex = len(self._items) - 1
