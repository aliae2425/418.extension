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

try:
    from views.ExportDoneView import ExportDoneView
except Exception:
    try:
        from lib.views.ExportDoneView import ExportDoneView
    except Exception:
        ExportDoneView = None  # type: ignore

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
        # VM de la page « par jeu » hébergée (fixé au montage) : conservé pour
        # pouvoir re-synchroniser ses collections après chaque refresh_par_jeu.
        self._auto_page_vm = None

    def _load(self):
        super(MainWindowView, self)._load()
        self.wire_navigation()
        self.wire_export()
        self.wire_destination()
        self.wire_naming_editors()
        self.wire_bulk_selection()
        self._vm._on_export_done_cb = self._show_export_done
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
            # Conserver le VM de la page et brancher le pont de re-synchro :
            # refresh_par_jeu (setters de mapping, édition du nommage, etc.)
            # invoquera _sync_auto_page pour pousser les nouvelles collections.
            self._auto_page_vm = page_vm
            self._vm._on_collections_changed_cb = self._sync_auto_page
        except Exception:
            pass

    def _sync_auto_page(self):
        """Pousse les collections courantes du MainViewModel vers l'AutoPageVM
        hébergé (DataContext distinct). Best-effort, ne lève jamais."""
        try:
            if self._auto_page_vm is not None:
                self._auto_page_vm.set_collections(getattr(self._vm, 'Collections', None) or [])
        except Exception:
            pass

    def _show_export_done(self, destination):
        if ExportDoneView is None:
            return
        try:
            view = ExportDoneView(destination)
            view._load()
            if view._window is not None and self._window is not None:
                try:
                    view._window.Owner = self._window
                except Exception:
                    pass
            view.show()
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
        # Le motif a pu changer -> recalculer les aperçus par collection de la
        # page « par jeu » (NomProjete des feuilles pour 'sheet', titre de
        # carnet pour 'set'). refresh_par_jeu re-synchronise l'AutoPage via
        # _on_collections_changed_cb.
        try:
            if hasattr(self._vm, 'refresh_par_jeu'):
                self._vm.refresh_par_jeu()
        except Exception:
            pass

    def wire_bulk_selection(self):
        """Câble la toolbar multi-sélection et les boutons de colonne PDF/DWG.

        - Toolbar existante (BulkSelectAll/Deselect, BulkPdf/DwgOn/Off) →
          méthodes correspondantes du VM.
        - Nouveaux boutons ToggleAllPdf/Dwg (en-tête colonnes) →
          vm.toggle_all_pdf() / toggle_all_dwg().
        - SheetListControl.PreviewMouseLeftButtonDown →
          sélection shift/ctrl via vm.handle_row_click().
        """
        if self._window is None:
            return
        vm = self._vm

        bulk_bindings = (
            (u'ToggleAllPdfButton', lambda: vm.toggle_all_pdf()),
            (u'ToggleAllDwgButton', lambda: vm.toggle_all_dwg()),
        )
        for btn_name, action in bulk_bindings:
            btn = self._window.FindName(btn_name)
            if btn is None:
                continue
            self._bind_bulk_button(btn, action)

        sheet_list = self._window.FindName(u'SheetListControl')
        if sheet_list is None:
            return

        def _on_row_click(sender, args):
            try:
                _handle_sheet_row_click(vm, args)
            except Exception:
                pass
        try:
            sheet_list.PreviewMouseLeftButtonDown += _on_row_click
        except Exception:
            pass

    @staticmethod
    def _bind_bulk_button(btn, action):
        def _handler(sender, args):
            try:
                action()
            except Exception:
                pass
        try:
            btn.Click += _handler
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


def _handle_sheet_row_click(vm, args):
    """Interprète un PreviewMouseLeftButtonDown sur le SheetListControl.

    Remonte l'arbre visuel depuis la source du clic jusqu'à trouver un
    DataContext de type ManualSheetVM (détection duck-type : présence de
    l'attribut ``ExportPdf``).  Si le clic est dans un CheckBox (toggles
    PDF/DWG), on sort sans modifier la sélection.  Sinon, on délègue à
    ``vm.handle_row_click(index, shift, ctrl)``.
    """
    try:
        from System.Windows.Media import VisualTreeHelper
        from System.Windows.Controls import CheckBox
        from System.Windows.Input import Keyboard, ModifierKeys
    except Exception:
        return

    source = args.OriginalSource
    row_vm = None
    current = source
    while current is not None:
        try:
            if isinstance(current, CheckBox):
                return   # clic dans un toggle PDF/DWG → ne pas interférer
        except Exception:
            pass
        try:
            dc = current.DataContext
            if dc is not None and hasattr(dc, u'ExportPdf'):
                row_vm = dc
                break
        except Exception:
            pass
        try:
            current = VisualTreeHelper.GetParent(current)
        except Exception:
            break

    if row_vm is None:
        return

    sheets = list(vm.SheetsManuelFiltrees)
    try:
        index = sheets.index(row_vm)
    except ValueError:
        return

    shift_down = int(Keyboard.Modifiers & ModifierKeys.Shift) != 0
    ctrl_down = int(Keyboard.Modifiers & ModifierKeys.Control) != 0

    vm.handle_row_click(index, shift=shift_down, ctrl=ctrl_down)
