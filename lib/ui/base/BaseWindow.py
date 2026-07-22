# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.helpers.wpf_runtime import ensure_wpf as _ensure_wpf
    _ensure_wpf()
except Exception:
    pass

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
        # Câblage du glisser-déposer par une barre de titre nommée « TitleBar ».
        # Gardé : les fenêtres sans « TitleBar » continuent de charger sans erreur.
        try:
            tb = self._window.FindName('TitleBar')
            if tb is not None:
                def _on_title_bar_down(sender, args):
                    try:
                        self._window.DragMove()
                    except Exception:
                        pass
                tb.MouseLeftButtonDown += _on_title_bar_down
        except Exception:
            pass

    def show(self):
        if self._window is None:
            self._load()
        if self._window is not None:
            self._window.ShowDialog()
