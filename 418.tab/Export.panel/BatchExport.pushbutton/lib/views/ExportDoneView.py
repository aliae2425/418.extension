# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

try:
    from ui.base.BaseWindow import BaseWindow
except Exception:
    BaseWindow = object  # type: ignore


def _xaml_path():
    here = os.path.dirname(os.path.abspath(__file__))
    button = os.path.abspath(os.path.join(here, '..', '..'))
    return os.path.join(button, 'GUI', 'Modals', 'ExportDone.xaml')


class ExportDoneView(BaseWindow):
    def __init__(self, destination_path):
        super(ExportDoneView, self).__init__(_xaml_path(), view_model=None)
        self._destination = destination_path or u''

    def _load(self):
        super(ExportDoneView, self)._load()
        if self._window is None:
            return

        dest_block = self._window.FindName(u'DestinationBlock')
        if dest_block is not None:
            try:
                dest_block.Text = u'Les fichiers ont été exportés vers :\n{}'.format(
                    self._destination)
            except Exception:
                pass

        open_btn = self._window.FindName(u'OpenFolderButton')
        if open_btn is not None:
            _dest = self._destination
            def _open(s, e):
                try:
                    if _dest:
                        from System.Diagnostics import Process
                        Process.Start(u'explorer.exe', _dest)
                except Exception:
                    pass
            try:
                open_btn.Click += _open
            except Exception:
                pass

        close_btn = self._window.FindName(u'CloseFermerButton')
        if close_btn is not None:
            _win = self._window
            def _fermer(s, e):
                try:
                    _win.Close()
                except Exception:
                    pass
            try:
                close_btn.Click += _fermer
            except Exception:
                pass
