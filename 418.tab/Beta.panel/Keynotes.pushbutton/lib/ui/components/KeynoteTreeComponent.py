# -*- coding: utf-8 -*-

class KeynoteTreeComponent(object):
    def __init__(self, window, controller):
        self._win = window
        self._controller = controller
        self._bind()

    def _bind(self):
        if hasattr(self._win, 'MainTreeView'):
            self._win.MainTreeView.SelectedItemChanged += self._on_selection_changed

    def _on_selection_changed(self, sender, args):
        try:
            selected_item = self._win.MainTreeView.SelectedItem
            if hasattr(self._controller, 'on_keynote_selected'):
                self._controller.on_keynote_selected(selected_item)
        except Exception:
            pass

    def set_items(self, items):
        if hasattr(self._win, 'MainTreeView'):
            self._win.MainTreeView.ItemsSource = items
