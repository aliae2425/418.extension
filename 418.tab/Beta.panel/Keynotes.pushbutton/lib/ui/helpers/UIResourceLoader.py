# -*- coding: utf-8 -*-
# Load WPF ResourceDictionaries (windows.xaml + view/modals resources)

import os


class UIResourceLoader(object):
    def __init__(self, window, app_paths):
        self._win = window
        self._paths = app_paths

    def _add_dict(self, abs_path):
        try:
            from System import Uri, UriKind
            from System.Windows import ResourceDictionary as WResourceDictionary
        except Exception:
            return False
        if not abs_path or not os.path.exists(abs_path):
            return False
        try:
            d = WResourceDictionary()
            u = Uri('file:///' + abs_path.replace('\\', '/').replace(':', ':/'), UriKind.Absolute)
            d.Source = u
            self._win.Resources.MergedDictionaries.Add(d)
            return True
        except Exception:
            return False

    def merge_windows(self):
        return self._add_dict(self._paths.windows_xaml())

    def merge_keynotes_main(self):
        return self._add_dict(self._paths.resource_path('KeynotesManager.Resources.xaml'))

    def merge_edit_record(self):
        return self._add_dict(self._paths.resource_path('EditRecord.Resources.xaml'))

    def merge_all_for_main(self):
        self.merge_windows()
        self.merge_keynotes_main()
        return True

    def merge_all_for_edit_record(self):
        self.merge_windows()
        self.merge_edit_record()
        return True
