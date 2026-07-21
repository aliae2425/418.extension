# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

try:
    from System import Uri, UriKind
    from System.Windows import ResourceDictionary
    _has_wpf = True
except Exception:
    _has_wpf = False

try:
    from core.AppPaths import AppPaths as _AppPaths
except Exception:
    _AppPaths = None


class UIResourceLoader(object):
    def __init__(self, window, dark=False):
        self._win = window
        self._dark = dark
        self._paths = _AppPaths() if _AppPaths is not None else None

    def merge_theme(self):
        if not _has_wpf:
            print('UIResourceLoader: WPF non disponible')
            return False
        if self._paths is None:
            print('UIResourceLoader: AppPaths non disponible')
            return False
        suffix = 'Dark' if self._dark else ''
        for name in ('Colors{}.xaml'.format(suffix), 'Styles{}.xaml'.format(suffix)):
            path = self._paths.resource_path(name)
            if not os.path.exists(path):
                print('UIResourceLoader: ressource introuvable: {}'.format(path))
                continue
            try:
                rd = ResourceDictionary()
                uri_str = 'file:///' + path.replace('\\', '/').replace(':', ':/')
                rd.Source = Uri(uri_str, UriKind.Absolute)
                self._win.Resources.MergedDictionaries.Add(rd)
            except Exception as e:
                print('UIResourceLoader: Erreur chargement {}: {}'.format(name, e))
        return True

    def merge_resource(self, xaml_path):
        if not _has_wpf or not os.path.exists(xaml_path):
            return False
        try:
            rd = ResourceDictionary()
            uri_str = 'file:///' + xaml_path.replace('\\', '/').replace(':', ':/')
            rd.Source = Uri(uri_str, UriKind.Absolute)
            self._win.Resources.MergedDictionaries.Add(rd)
            return True
        except Exception as e:
            print('UIResourceLoader: Erreur merge_resource {}: {}'.format(xaml_path, e))
            return False
