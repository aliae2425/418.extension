# -*- coding: utf-8 -*-
from pyrevit import forms

class OrderManagerWindow(forms.WPFWindow):
    def __init__(self, xaml_path, items):
        forms.WPFWindow.__init__(self, xaml_path)
        self._items = list(items) # Copy list
        self.ItemsList.ItemsSource = self._items
        self.response = None

    def OnUpClick(self, sender, args):
        idx = self.ItemsList.SelectedIndex
        if idx > 0:
            item = self._items.pop(idx)
            self._items.insert(idx - 1, item)
            self.ItemsList.Items.Refresh()
            self.ItemsList.SelectedIndex = idx - 1

    def OnDownClick(self, sender, args):
        idx = self.ItemsList.SelectedIndex
        if idx < len(self._items) - 1 and idx != -1:
            item = self._items.pop(idx)
            self._items.insert(idx + 1, item)
            self.ItemsList.Items.Refresh()
            self.ItemsList.SelectedIndex = idx + 1

    def OnOkClick(self, sender, args):
        self.response = self._items
        self.Close()

    def OnCancelClick(self, sender, args):
        self.Close()
