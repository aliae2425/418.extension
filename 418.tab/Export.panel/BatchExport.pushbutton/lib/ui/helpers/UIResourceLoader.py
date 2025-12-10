# -*- coding: utf-8 -*-
# Chargement des ResourceDictionaries WPF (windows.xaml + Controls)

import os

try:
    from pyrevit import EXEC_PARAMS
    _verbose = EXEC_PARAMS.debug_mode
except Exception:
    _verbose = False

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
        except Exception as e:
            print('UIResourceLoader [001]: Failed to import WPF types: {}'.format(e))
            return False
        if self._paths is None:
            print('UIResourceLoader [002]: AppPaths is None')
            return False
        # windows.xaml
        win_path = self._paths.windows_xaml()
        if _verbose:
            pass
        if not os.path.exists(win_path):
            print('UIResourceLoader [003]: windows.xaml not found at: {}'.format(win_path))
        try:
            d0 = WResourceDictionary()
            u0 = Uri('file:///' + win_path.replace('\\', '/').replace(':', ':/'), UriKind.Absolute)
            d0.Source = u0
            self._win.Resources.MergedDictionaries.Add(d0)
            if _verbose:
                pass
        except Exception as e:
            print('UIResourceLoader [004]: Failed to load windows.xaml: {}'.format(e))
            pass
        # Controls
        ctrl_dir = self._paths.controls_dir()
        if _verbose:
            pass
        names = ['ParameterSelector.xaml','ExportOptions.xaml','DestinationPicker.xaml','NamingConfig.xaml','CollectionPreview.xaml']
        for n in names:
            path = os.path.join(ctrl_dir, n)
            if not os.path.exists(path):
                if _verbose:
                    print('UIResourceLoader [005]: Control file not found: {}'.format(path))
                continue
            try:
                d = WResourceDictionary()
                u = Uri('file:///' + path.replace('\\', '/').replace(':', ':/'), UriKind.Absolute)
                d.Source = u
                self._win.Resources.MergedDictionaries.Add(d)
                if _verbose:
                    pass
            except Exception as e:
                print('UIResourceLoader [006]: Failed to load {}: {}'.format(n, e))
                pass
        return True
