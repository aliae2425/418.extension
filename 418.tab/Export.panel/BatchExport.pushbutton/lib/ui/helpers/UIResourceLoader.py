# -*- coding: utf-8 -*-
# Chargement des ResourceDictionaries WPF (windows.xaml + Controls)

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

    # Merge windows.xaml puis les contrôles
    def merge_all(self):
        try:
            from System import Uri, UriKind
            from System.Windows import ResourceDictionary as WResourceDictionary
        except Exception:
            return False
        if self._paths is None:
            return False
        # windows.xaml
        win_path = self._paths.windows_xaml()
        try:
            d0 = WResourceDictionary()
            u0 = Uri('file:///' + win_path.replace('\\', '/').replace(':', ':/'), UriKind.Absolute)
            d0.Source = u0
            self._win.Resources.MergedDictionaries.Add(d0)
        except Exception:
            pass
        # Controls
        ctrl_dir = self._paths.controls_dir()
        names = ['ParameterSelector.xaml','ExportOptions.xaml','DestinationPicker.xaml','NamingConfig.xaml','CollectionPreview.xaml']
        for n in names:
            path = os.path.join(ctrl_dir, n)
            if not os.path.exists(path):
                continue
            try:
                d = WResourceDictionary()
                u = Uri('file:///' + path.replace('\\', '/').replace(':', ':/'), UriKind.Absolute)
                d.Source = u
                self._win.Resources.MergedDictionaries.Add(d)
            except Exception:
                pass
        return True
