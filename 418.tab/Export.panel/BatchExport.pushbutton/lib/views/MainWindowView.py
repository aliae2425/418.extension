# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

try:
    from ui.base.BaseWindow import BaseWindow
except Exception:
    BaseWindow = object


def _xaml_path():
    here = os.path.dirname(os.path.abspath(__file__))
    button = os.path.abspath(os.path.join(here, '..', '..'))
    return os.path.join(button, 'GUI', 'Views', 'MainWindow.xaml')


def _pick_folder():
    """Ouvre un sélecteur de dossier. Retourne le chemin choisi, ou `None`
    (annulation ou sélecteur indisponible hors Revit).

    Ordre de repli : `pyrevit.forms.pick_folder` (intégration Revit), puis
    `System.Windows.Forms.FolderBrowserDialog` (WinForms brut). Chaque
    tentative est protégée : hors Revit/hors WPF, aucune ne doit lever.
    """
    try:
        from pyrevit import forms
        chemin = forms.pick_folder()
        if chemin:
            return chemin
    except Exception:
        pass

    try:
        from System.Windows.Forms import FolderBrowserDialog, DialogResult
        dlg = FolderBrowserDialog()
        if dlg.ShowDialog() == DialogResult.OK:
            return dlg.SelectedPath
    except Exception:
        pass

    return None


class MainWindowView(BaseWindow):
    def __init__(self, view_model):
        super(MainWindowView, self).__init__(_xaml_path(), view_model)
        self._vm = view_model

    def _load(self):
        super(MainWindowView, self)._load()
        self.wire_navigation()
        self.wire_export()
        self.wire_destination()
        try:
            self._vm.refresh_par_jeu()
        except Exception:
            pass

    def wire_export(self):
        if self._window is None:
            return
        btn = self._window.FindName('PrimaryActionButton')
        if btn is None:
            return
        vm = self._vm

        def _on_click(sender, args):
            try:
                vm.lancer_export()
            except Exception:
                pass
        try:
            btn.Click += _on_click
        except Exception:
            pass

    def wire_destination(self):
        if self._window is None:
            return
        btn = self._window.FindName('SecondaryActionButton')
        if btn is None:
            return
        vm = self._vm

        def _on_click(sender, args):
            try:
                chemin = _pick_folder()
            except Exception:
                chemin = None
            if not chemin:
                return
            try:
                vm.definir_destination(chemin)
            except Exception:
                pass
        try:
            btn.Click += _on_click
        except Exception:
            pass

    def wire_navigation(self):
        if self._window is None:
            return
        mapping = (('NavAuto', u'auto'),
                   ('NavManual', u'manual'),
                   ('NavSettings', u'settings'))
        for name, mode in mapping:
            btn = self._window.FindName(name)
            if btn is None:
                continue
            self._bind_nav(btn, mode)

    def _bind_nav(self, btn, mode):
        vm = self._vm

        def _on_checked(sender, args):
            try:
                vm.set_mode(mode)
            except Exception:
                pass
        try:
            btn.Checked += _on_checked
        except Exception:
            pass
