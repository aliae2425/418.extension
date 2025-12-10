# -*- coding: utf-8 -*-
from pyrevit import forms
import os

def _get_help_xaml_path():
    try:
        from ...core.AppPaths import AppPaths
        paths = AppPaths()
        return os.path.join(paths.gui_root(), 'Modals', 'HelpModal.xaml')
    except Exception:
        here = os.path.dirname(__file__)
        return os.path.normpath(os.path.join(here, '..', '..', 'GUI', 'Modals', 'HelpModal.xaml'))

class HelpWindow(forms.WPFWindow):
    def __init__(self, content=None):
        forms.WPFWindow.__init__(self, _get_help_xaml_path())
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
            print('HelpWindow [001]: Error loading resources: {}'.format(e))

        if content and hasattr(self, 'HelpContentText'):
            self.HelpContentText.Text = content
        if hasattr(self, 'CloseButton'):
            self.CloseButton.Click += self._on_close
        if hasattr(self, 'OkButton'):
            self.OkButton.Click += self._on_close
        if hasattr(self, 'TitleBar'):
            self.TitleBar.MouseLeftButtonDown += self._on_title_bar_mouse_down

    def _on_close(self, sender, args):
        self.Close()
        
    def _on_title_bar_mouse_down(self, sender, args):
        try:
            self.DragMove()
        except Exception:
            pass

def show_help(content=None):
    win = HelpWindow(content)
    win.ShowDialog()
