# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from ui.helpers.wpf_runtime import ensure_wpf as _ensure_wpf
_ensure_wpf()

try:
    from System.Windows.Markup import XamlReader
    from System.IO import FileStream, FileMode, FileAccess
    _has_wpf = True
except Exception:
    XamlReader = None
    FileStream = None
    _has_wpf = False

try:
    from System.Windows import WindowState
except Exception:
    WindowState = None

from ui.helpers.UIResourceLoader import UIResourceLoader
from ui.helpers.DarkMode import is_dark as _is_dark


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
        UIResourceLoader(self._window, dark=_is_dark()).merge_theme()
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
        # Câblage opt-in des boutons de la barre commune. Chaque bouton est
        # optionnel : FindName peut renvoyer None (ex. modal About). Tout est
        # protégé afin qu'une fenêtre sans ces boutons charge sans erreur.
        try:
            btn_min = self._window.FindName('MinimizeButton')
            if btn_min is not None and WindowState is not None:
                def _on_minimize(sender, args):
                    try:
                        self._window.WindowState = WindowState.Minimized
                    except Exception:
                        pass
                btn_min.Click += _on_minimize
        except Exception:
            pass
        try:
            btn_maxr = self._window.FindName('MaximizeRestoreButton')
            if btn_maxr is not None and WindowState is not None:
                def _on_maximize_restore(sender, args):
                    try:
                        if self._window.WindowState == WindowState.Maximized:
                            self._window.WindowState = WindowState.Normal
                        else:
                            self._window.WindowState = WindowState.Maximized
                    except Exception:
                        pass
                btn_maxr.Click += _on_maximize_restore
        except Exception:
            pass
        try:
            btn_close = self._window.FindName('CloseButton')
            if btn_close is not None:
                def _on_close(sender, args):
                    try:
                        self._window.Close()
                    except Exception:
                        pass
                btn_close.Click += _on_close
        except Exception:
            pass

    def show(self):
        if self._window is None:
            self._load()
        if self._window is not None:
            self._window.ShowDialog()
