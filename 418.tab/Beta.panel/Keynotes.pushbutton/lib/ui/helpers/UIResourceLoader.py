# -*- coding: utf-8 -*-
import os

class UIResourceLoader(object):
    def __init__(self, window, app_paths=None):
        self._win = window
        if app_paths is None:
            from ...core.AppPaths import AppPaths
            app_paths = AppPaths()
        self._paths = app_paths

    def merge_all(self):
        try:
            from System import Uri, UriKind
            from System.Windows import ResourceDictionary as WResourceDictionary
        except Exception as e:
            print('UIResourceLoader: Failed to import WPF types: {}'.format(e))
            return False

        win_path = self._paths.windows_xaml()
        if not os.path.exists(win_path):
            print('UIResourceLoader: windows.xaml not found at: {}'.format(win_path))
            return False

        try:
            d0 = WResourceDictionary()
            u0 = Uri('file:///' + win_path.replace('\\', '/').replace(':', ':/'), UriKind.Absolute)
            d0.Source = u0
            self._win.Resources.MergedDictionaries.Add(d0)
            return True
        except Exception as e:
            print('UIResourceLoader: Failed to load windows.xaml: {}'.format(e))
            return False
