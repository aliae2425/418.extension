# -*- coding: utf-8 -*-
import os
from pyrevit import forms
from pyrevit.forms import WPFWindow

import clr
clr.AddReference('PresentationFramework')
from System.Windows.Controls import WebBrowser

class MainWindow(WPFWindow):
    def __init__(self, xaml_path):
        WPFWindow.__init__(self, xaml_path)

class MainWindowController(object):
    def __init__(self):
        gui_path = os.path.join(os.path.dirname(__file__), '..', 'GUI', 'windows.xaml')
        self._win = MainWindow(gui_path)
        self.sheet_id = None
        self.folder_path = None
        self.views = []
        self.selected_view = None

    def show(self):
        self._win.OpenMapButton.Click += self._on_open_map
        self._win.SheetIdBox.TextChanged += self._on_sheet_id_changed
        self._win.ImportButton.Click += self._on_import
        self._win.PickFolderButton.Click += self._on_pick_folder
        self._win.ViewComboBox.SelectionChanged += self._on_view_selected
        self._win.ShowDialog()

    def _on_open_map(self, sender, args):
        import webbrowser
        webbrowser.open('https://cadastre.data.gouv.fr/map?style=ortho')

    def _on_sheet_id_changed(self, sender, args):
        self.sheet_id = self._win.SheetIdBox.Text.strip()
        self._update_import_button_state()

    def _on_pick_folder(self, sender, args):
        folder = forms.pick_folder(title='Choisir le dossier de téléchargement DXF')
        if folder:
            self.folder_path = folder
            self._win.FolderPathBox.Text = folder
            self._update_import_button_state()

    def _on_view_selected(self, sender, args):
        idx = self._win.ViewComboBox.SelectedIndex
        if idx >= 0 and idx < len(self.views):
            self.selected_view = self.views[idx]
            self._update_import_button_state()

    def _update_import_button_state(self):
        self._win.ImportButton.IsEnabled = bool(self.sheet_id and self.folder_path and self.selected_view)

    def _on_import(self, sender, args):
        # TODO: Download DXF and import into Revit
        forms.alert('Importation DXF non encore implémentée.')
