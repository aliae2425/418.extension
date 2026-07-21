# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from System.Windows.Markup import XamlReader
    from System.IO import FileStream, FileMode, FileAccess
    _has_wpf = True
except Exception:
    XamlReader = None
    FileStream = None
    _has_wpf = False

try:
    from ui.helpers.UIResourceLoader import UIResourceLoader
except Exception:
    UIResourceLoader = None

try:
    from ui.helpers.DarkMode import is_dark as _is_dark
except Exception:
    def _is_dark():
        return False


class BaseWindow(object):
    def __init__(self, xaml_path, view_model=None):
        self._xaml_path = xaml_path
        self._vm = view_model
        self._window = None

    def _load(self):
        if not _has_wpf:
            print('BaseWindow: WPF non disponible')
            return
        stream = None
        try:
            stream = FileStream(self._xaml_path, FileMode.Open, FileAccess.Read)
            self._window = XamlReader.Load(stream)
        except Exception as e:
            print('BaseWindow [001]: Impossible de charger le XAML: {}'.format(e))
            return
        finally:
            if stream is not None:
                try:
                    stream.Close()
                except Exception:
                    pass
        if UIResourceLoader is not None:
            loader = UIResourceLoader(self._window, dark=_is_dark())
            loader.merge_theme()
        if self._vm is not None:
            self._window.DataContext = self._vm

    def show(self):
        if self._window is None:
            self._load()
        if self._window is not None:
            self._window.ShowDialog()
