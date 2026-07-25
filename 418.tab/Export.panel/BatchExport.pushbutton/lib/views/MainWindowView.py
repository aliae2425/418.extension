# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

try:
    from ui.base.BaseWindow import BaseWindow
except Exception:
    BaseWindow = object

# Modale d'édition de la convention de nommage (feuilles/carnets). Double
# forme d'import (régime pyRevit vs régime tests standalone), cf. convention
# du projet (voir MainViewModel.py).
try:
    from viewmodels.NamingEditorViewModel import NamingEditorViewModel
except Exception:
    try:
        from lib.viewmodels.NamingEditorViewModel import NamingEditorViewModel
    except Exception:
        NamingEditorViewModel = None  # type: ignore

try:
    from views.NamingEditorView import NamingEditorView
except Exception:
    try:
        from lib.views.NamingEditorView import NamingEditorView
    except Exception:
        NamingEditorView = None  # type: ignore

# SPIKE (étape 0 découpage main window) : sous-VM de la page « par jeu ».
try:
    from viewmodels.AutoPageVM import AutoPageVM
except Exception:
    try:
        from lib.viewmodels.AutoPageVM import AutoPageVM
    except Exception:
        AutoPageVM = None  # type: ignore


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
        self.wire_naming_editors()
        self.wire_bulk_edit()
        try:
            self._vm.refresh_par_jeu()
        except Exception:
            pass
        try:
            self._vm.refresh_manuel()
        except Exception:
            pass
        self._mount_auto_page_spike()

    # ------------------------------------------------------------------
    # Charge GUI/Views/pages/AutoPage.xaml comme arbre séparé, lui pose son
    # PROPRE DataContext (AutoPageVM) et l'insère dans le ContentControl
    # AutoPageHost du shell. Best-effort (silencieux) comme le reste du
    # câblage : hors Revit / si l'hôte manque, ne lève pas.
    # ------------------------------------------------------------------
    def _load_page(self, filename):
        from System.Windows.Markup import XamlReader
        from System.IO import FileStream, FileMode, FileAccess
        here = os.path.dirname(os.path.abspath(__file__))
        button = os.path.abspath(os.path.join(here, '..', '..'))
        path = os.path.join(button, 'GUI', 'Views', 'pages', filename)
        stream = FileStream(path, FileMode.Open, FileAccess.Read)
        try:
            return XamlReader.Load(stream)
        finally:
            try:
                stream.Close()
            except Exception:
                pass

    def _mount_auto_page_spike(self):
        if self._window is None or AutoPageVM is None:
            return
        host = self._window.FindName('AutoPageHost')
        if host is None:
            return
        try:
            collections = getattr(self._vm, 'Collections', None) or []
            page_vm = AutoPageVM(collections)
            page = self._load_page('AutoPage.xaml')
            page.DataContext = page_vm
            host.Content = page
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

    def wire_naming_editors(self):
        """Câble les 2 boutons de la carte « Nommage des fichiers » (page
        Paramètres) : chacun ouvre la modale NamingEditorView pour la
        convention correspondante ('sheet' ou 'set').

        Chaque bouton est optionnel (FindName peut renvoyer None) et le
        câblage entier est best-effort : si les classes modales n'ont pas pu
        être importées (hors Revit/WPF), les boutons restent simplement
        sans effet plutôt que de lever au chargement de la fenêtre.
        """
        if self._window is None:
            return
        mapping = (('EditSheetNamingButton', u'sheet'),
                   ('EditSetNamingButton', u'set'))
        for name, kind in mapping:
            btn = self._window.FindName(name)
            if btn is None:
                continue
            self._bind_naming_editor(btn, kind)

    def _bind_naming_editor(self, btn, kind):
        def _on_click(sender, args):
            try:
                self._open_naming_editor(kind)
            except Exception:
                pass
        try:
            btn.Click += _on_click
        except Exception:
            pass

    def _open_naming_editor(self, kind):
        """Instancie et affiche la modale NamingEditorView pour `kind`
        ('sheet' ou 'set'), câblée sur le même `naming_service` que le VM
        principal (mode jetons : plus besoin d'injecter une liste de
        paramètres disponibles, `NamingEditorViewModel` les tire directement
        de `naming_service.available_tokens()`).
        """
        if NamingEditorViewModel is None or NamingEditorView is None:
            return
        vm = self._vm

        ned_vm = NamingEditorViewModel(
            kind,
            naming_service=getattr(vm, '_naming_service', None),
        )
        view = NamingEditorView(ned_vm)

        # Forcer le chargement immédiat (plutôt que le chargement paresseux
        # de `show()`) afin de pouvoir fixer `Owner` avant l'affichage --
        # `show()` ne recharge pas si `_window` est déjà défini, donc cet
        # appel anticipé n'entraîne aucun double chargement.
        try:
            view._load()
            if view._window is not None and self._window is not None:
                view._window.Owner = self._window
        except Exception:
            pass

        view.show()

        # La modale est modale (ShowDialog) : au retour, rafraîchir l'aperçu
        # de la convention dans la page Réglages (le motif a pu changer).
        try:
            if hasattr(self._vm, 'refresh_patterns_apercu'):
                self._vm.refresh_patterns_apercu()
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

    def wire_bulk_edit(self):
        """Câble les 6 boutons de la toolbar multi-sélection (mode manuel)."""
        if self._window is None:
            return
        vm = self._vm
        mapping = (
            ('BulkSelectAllButton',  lambda: vm.select_all_manuel()),
            ('BulkDeselectAllButton', lambda: vm.deselect_all_manuel()),
            ('BulkPdfOnButton',      lambda: vm.bulk_set_pdf(True)),
            ('BulkPdfOffButton',     lambda: vm.bulk_set_pdf(False)),
            ('BulkDwgOnButton',      lambda: vm.bulk_set_dwg(True)),
            ('BulkDwgOffButton',     lambda: vm.bulk_set_dwg(False)),
        )
        for name, action in mapping:
            btn = self._window.FindName(name)
            if btn is None:
                continue
            def _make_handler(fn):
                def _on_click(sender, args):
                    try:
                        fn()
                    except Exception:
                        pass
                return _on_click
            try:
                btn.Click += _make_handler(action)
            except Exception:
                pass
