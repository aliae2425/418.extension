# -*- coding: utf-8 -*-
from pyrevit import forms
import os

class TutorialWindow(forms.WPFWindow):
    def __init__(self):
        xaml_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'GUI', 'Modals', 'Tutorial.xaml')
        forms.WPFWindow.__init__(self, xaml_path)
        try:
            from System import Uri, UriKind
            from System.Windows import ResourceDictionary
            from Autodesk.Revit.UI import UIThemeManager, UITheme
            from ...core.AppPaths import AppPaths
            paths = AppPaths()
            theme = UIThemeManager.CurrentTheme
            if theme == UITheme.Dark:
                files = ['ColorsDark.xaml', 'StylesDark.xaml']
            else:
                files = ['Colors.xaml', 'Styles.xaml']
            for filename in files:
                path = paths.resource_path(filename)
                if os.path.exists(path):
                    rd = ResourceDictionary()
                    rd.Source = Uri(path, UriKind.Absolute)
                    self.Resources.MergedDictionaries.Add(rd)
        except Exception as e:
            print('TutorialWindow [001]: Error loading resources: {}'.format(e))
        if hasattr(self, 'CloseButton'):
            self.CloseButton.Click += self._on_close
        if hasattr(self, 'OkButton'):
            self.OkButton.Click += self._on_close

    def _on_close(self, sender, args):
        self.Close()

def show_tutorial():
    win = TutorialWindow()
    win.ShowDialog()
