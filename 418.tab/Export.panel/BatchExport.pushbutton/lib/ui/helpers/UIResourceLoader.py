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
        except Exception as e:
            print('[error] Failed to import WPF types:', e)
            return False
        if self._paths is None:
            print('[error] AppPaths is None')
            return False
        # windows.xaml
        win_path = self._paths.windows_xaml()
        print('[debug] Loading windows.xaml from:', win_path)
        if not os.path.exists(win_path):
            print('[error] windows.xaml not found at:', win_path)
        try:
            d0 = WResourceDictionary()
            u0 = Uri('file:///' + win_path.replace('\\', '/').replace(':', ':/'), UriKind.Absolute)
            d0.Source = u0
            self._win.Resources.MergedDictionaries.Add(d0)
            print('[debug] windows.xaml loaded successfully')
        except Exception as e:
            print('[error] Failed to load windows.xaml:', e)
            pass
        # Controls
        ctrl_dir = self._paths.controls_dir()
        print('[debug] Loading controls from:', ctrl_dir)
        names = ['ParameterSelector.xaml','ExportOptions.xaml','DestinationPicker.xaml','NamingConfig.xaml','CollectionPreview.xaml']
        for n in names:
            path = os.path.join(ctrl_dir, n)
            if not os.path.exists(path):
                print('[warning] Control file not found:', path)
                continue
            try:
                d = WResourceDictionary()
                u = Uri('file:///' + path.replace('\\', '/').replace(':', ':/'), UriKind.Absolute)
                d.Source = u
                self._win.Resources.MergedDictionaries.Add(d)
                print('[debug] Loaded control:', n)
            except Exception as e:
                print('[error] Failed to load {}: {}'.format(n, e))
                pass
        return True
