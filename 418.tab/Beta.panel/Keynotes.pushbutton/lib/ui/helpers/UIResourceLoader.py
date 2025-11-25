# -*- coding: utf-8 -*-
# Chargement des ResourceDictionaries WPF

import os

class UIResourceLoader(object):
    def __init__(self, window, app_paths=None):
        self._win = window
        if app_paths is None:
            try:
                from ...core.AppPaths import AppPaths
                app_paths = AppPaths()
            except Exception:
                app_paths = None
        self._paths = app_paths

    def merge_all(self):
        try:
            from System import Uri, UriKind
            from System.Windows import ResourceDictionary as WResourceDictionary
        except Exception:
            return False
        
        if self._paths is None:
            return False

        # Load Styles.xaml
        styles_path = os.path.join(self._paths.gui_root(), 'resources', 'Styles.xaml')
        if os.path.exists(styles_path):
            try:
                d = WResourceDictionary()
                u = Uri('file:///' + styles_path.replace('\\', '/').replace(':', ':/'), UriKind.Absolute)
                d.Source = u
                self._win.Resources.MergedDictionaries.Add(d)
            except Exception:
                pass
        return True
