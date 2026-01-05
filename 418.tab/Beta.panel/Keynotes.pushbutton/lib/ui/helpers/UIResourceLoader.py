# -*- coding: utf-8 -*-
# Load WPF ResourceDictionaries (windows.xaml + view/modals resources)

import os

try:
    from System import Uri, UriKind
    from System.Windows import ResourceDictionary as WResourceDictionary
except ImportError:
    Uri = None
    UriKind = None
    WResourceDictionary = None


class UIResourceLoader(object):
    def __init__(self, window, app_paths):
        self._win = window
        self._paths = app_paths

    def _get_dict(self, abs_path):
        if not WResourceDictionary:
            return None
            
        if not abs_path or not os.path.exists(abs_path):
            return None
            
        try:
            d = WResourceDictionary()
            # Optimized URI creation
            uri_str = 'file:///' + abs_path.replace('\\', '/').replace(':', ':/')
            d.Source = Uri(uri_str, UriKind.Absolute)
            return d
        except Exception:
            return None

    def _batch_add(self, paths):
        if not hasattr(self._win, 'Resources'):
            return False
            
        # Create a local list of dictionaries to minimize property access overhead
        dicts_to_add = []
        for p in paths:
            d = self._get_dict(p)
            if d:
                dicts_to_add.append(d)
        
        # Add to window resources
        for d in dicts_to_add:
            self._win.Resources.MergedDictionaries.Add(d)
            
        return True

    def merge_all_for_main(self):
        paths = [
            self._paths.resource_path('Colors.xaml'),
            self._paths.resource_path('Styles.xaml'),
            self._paths.resource_path('Icons.xaml'),
            self._paths.resource_path('Templates.xaml'),
            self._paths.windows_xaml(),
            self._paths.resource_path('KeynotesManager.Resources.xaml')
        ]

        # Controls (Burger menu sections)
        try:
            ctrl_dir = self._paths.controls_dir()
            names = [
                'BurgerMenu.xaml',
                'WorkArea.xaml',
                'UpdateSection.xaml',
                'ChangeSection.xaml',
                'ExportSection.xaml',
                'CategorySection.xaml',
                'KeynotesSection.xaml',
                'PlaceSection.xaml',
            ]
            paths.extend([os.path.join(ctrl_dir, n) for n in names])
        except Exception:
            pass
            
        return self._batch_add(paths)

    def merge_all_for_edit_record(self):
        paths = [
            self._paths.windows_xaml(),
            self._paths.resource_path('EditRecord.Resources.xaml')
        ]
        return self._batch_add(paths)
