# -*- coding: utf-8 -*-
from pyrevit import forms

class OrderManagerWindow(forms.WPFWindow):
    def __init__(self, xaml_path, items, is_dark_mode=False):
        forms.WPFWindow.__init__(self, xaml_path)

        # Charge les ressources (même base que UIResourceLoader)
        try:
            from ...core.AppPaths import AppPaths
            from System.Windows import ResourceDictionary
            from System import Uri, UriKind
            paths = AppPaths()

            # Base resources (light) via windows.xaml
            winres = ResourceDictionary()
            winres.Source = Uri('file:///' + paths.windows_xaml().replace('\\', '/').replace(':', ':/'), UriKind.Absolute)
            self.Resources.MergedDictionaries.Add(winres)

            # Dark overrides
            if is_dark_mode:
                for filename in ('ColorsDark.xaml', 'StylesDark.xaml'):
                    path = paths.resource_path(filename)
                    rd = ResourceDictionary()
                    rd.Source = Uri('file:///' + path.replace('\\', '/').replace(':', ':/'), UriKind.Absolute)
                    self.Resources.MergedDictionaries.Add(rd)

        except Exception as e:
            print('OrderManagerWindow [001]: Error loading resources: {}'.format(e))

        try:
            if hasattr(self, 'CloseButton'):
                self.CloseButton.Click += self.OnCancelClick
            if hasattr(self, 'TitleBar'):
                self.TitleBar.MouseLeftButtonDown += self._on_title_bar_mouse_down
        except Exception:
            pass

        self._items = list(items) # Copy list
        self._update_orders()

        self.ItemsList.ItemsSource = self._items
        self.response = None

    def _on_title_bar_mouse_down(self, sender, args):
        try:
            self.DragMove()
        except Exception:
            pass

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
