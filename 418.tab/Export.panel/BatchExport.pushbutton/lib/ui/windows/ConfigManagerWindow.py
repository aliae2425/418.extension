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
        
        # Bind Close button
        if hasattr(self, 'CloseButton'):
            self.CloseButton.Click += self._close_click

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
