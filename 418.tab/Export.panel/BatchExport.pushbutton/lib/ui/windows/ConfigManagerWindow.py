# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from pyrevit import forms

class ConfigManagerWindow(forms.WPFWindow):
    def __init__(self):
        from ...core.AppPaths import AppPaths
        self._paths = AppPaths()
        xaml_path = self._paths.config_manager_xaml()
        forms.WPFWindow.__init__(self, xaml_path)
        
        # Load resources
        from ..helpers.UIResourceLoader import UIResourceLoader
        UIResourceLoader(self, self._paths).merge_all()
        
        # Apply theme
        self._apply_theme()
        
        # Service
        from ...services.ConfigManagerService import ConfigManagerService
        self._service = ConfigManagerService()
        
        # Init UI
        self._refresh_list()
        
        # Bind events
        if hasattr(self, 'CloseButton'):
            self.CloseButton.Click += self._close_click
        if hasattr(self, 'LoadConfigButton'):
            self.LoadConfigButton.Click += self._on_load
        if hasattr(self, 'SaveConfigButton'):
            self.SaveConfigButton.Click += self._on_save
        if hasattr(self, 'ImportConfigButton'):
            self.ImportConfigButton.Click += self._on_import
        if hasattr(self, 'ExportConfigButton'):
            self.ExportConfigButton.Click += self._on_export
        if hasattr(self, 'ConfigsList'):
            self.ConfigsList.SelectionChanged += self._on_selection_changed

    def _refresh_list(self):
        if hasattr(self, 'ConfigsList'):
            self.ConfigsList.Items.Clear()
            profiles = self._service.get_profiles()
            for name in sorted(profiles.keys()):
                self.ConfigsList.Items.Add(name)

    def _on_selection_changed(self, sender, args):
        sel = self.ConfigsList.SelectedItem
        if sel and hasattr(self, 'ProfileNameBox'):
            self.ProfileNameBox.Text = sel

    def _on_load(self, sender, args):
        sel = self.ConfigsList.SelectedItem
        if sel:
            if self._service.load_profile(sel):
                self.Close()
            else:
                forms.alert("Erreur lors du chargement.", title="Erreur")

    def _on_save(self, sender, args):
        name = None
        if hasattr(self, 'ProfileNameBox'):
            name = self.ProfileNameBox.Text
        
        if not name:
            name = forms.ask_for_string(prompt="Nom de la configuration:", title="Enregistrer sous")
        
        if name:
            self._service.save_profile(name)
            self._refresh_list()
            # Reselect the saved item
            if hasattr(self, 'ConfigsList'):
                self.ConfigsList.SelectedItem = name

    def _on_import(self, sender, args):
        path = forms.pick_file(file_ext='csv')
        if path:
            if self._service.import_config_from_csv(path):
                forms.alert("Configuration chargée avec succès.", title="Succès")
                self.Close()
            else:
                forms.alert("Erreur lors de l'importation.", title="Erreur")

    def _on_export(self, sender, args):
        path = forms.save_file(file_ext='csv', default_name='config_export')
        if path:
            if self._service.export_current_config_to_csv(path):
                forms.alert("Configuration exportée avec succès.", title="Succès")
            else:
                forms.alert("Erreur lors de l'exportation.", title="Erreur")

    def _apply_theme(self):
        try:
            from Autodesk.Revit.UI import UIThemeManager, UITheme
            theme = UIThemeManager.CurrentTheme
            if theme == UITheme.Dark:
                from System.Windows import ResourceDictionary
                from System import Uri, UriKind
                
                dark_colors = self._paths.resource_path('ColorsDark.xaml')
                dark_styles = self._paths.resource_path('StylesDark.xaml')
                
                for path in [dark_colors, dark_styles]:
                    rd = ResourceDictionary()
                    rd.Source = Uri(path, UriKind.Absolute)
                    self.Resources.MergedDictionaries.Add(rd)
        except Exception:
            pass

    def _close_click(self, sender, args):
        self.Close()

    def show(self, owner=None):
        # If owner is provided, center on owner
        if owner:
            self.Owner = owner
            self.WindowStartupLocation = System.Windows.WindowStartupLocation.CenterOwner
        self.ShowDialog()

import System.Windows
