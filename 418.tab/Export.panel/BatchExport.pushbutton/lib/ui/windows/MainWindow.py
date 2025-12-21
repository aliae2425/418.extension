# -*- coding: utf-8 -*-

import os
from pyrevit import forms

from ..helpers.RelayCommand import RelayCommand


class MainWindow(forms.WPFWindow):
    def __init__(self, xaml_path):
        forms.WPFWindow.__init__(self, xaml_path)
        self.ManageOrderCommand = RelayCommand(self.OnManageOrder)

    def OnManageOrder(self, collection_name):
        if not hasattr(self, '_preview_items') or not self._preview_items:
            return

        indices = []
        coll_items = []
        for i, item in enumerate(self._preview_items):
            if item['CollectionName'] == collection_name:
                indices.append(i)
                coll_items.append(item)

        if not coll_items:
            return

        is_dark = False
        if hasattr(self, 'DarkModeToggle'):
            is_dark = self.DarkModeToggle.IsChecked == True

        from ...core.AppPaths import AppPaths
        paths = AppPaths()
        xaml_path = os.path.join(paths.gui_root(), 'Modals', 'OrderManager.xaml')

        from .OrderManagerWindow import OrderManagerWindow
        wm = OrderManagerWindow(xaml_path, coll_items, is_dark_mode=is_dark)
        wm.ShowDialog()

        if wm.response:
            start_idx = indices[0]
            for k, new_item in enumerate(wm.response):
                self._preview_items[start_idx + k] = new_item

            if hasattr(self, 'CollectionGrid') and self.CollectionGrid.ItemsSource:
                self.CollectionGrid.ItemsSource.Refresh()
