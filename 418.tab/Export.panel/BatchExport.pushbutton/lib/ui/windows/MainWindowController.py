# -*- coding: utf-8 -*-
# Contrôleur de la fenêtre principale: construit la fenêtre et branche la logique UI

from __future__ import unicode_literals

import os
from pyrevit import forms

try:
    from pyrevit import EXEC_PARAMS
    _verbose = EXEC_PARAMS.debug_mode
except Exception:
    _verbose = False

class MainWindow(forms.WPFWindow):
    def __init__(self, xaml_path):
        forms.WPFWindow.__init__(self, xaml_path)

class MainWindowController(object):
    def __init__(self):
        # Paths
        from ...core.AppPaths import AppPaths
        self._paths = AppPaths()
        # Config
        from ...core.UserConfig import UserConfig
        self._cfg = UserConfig('batch_export')
        # Services / Data
        from ...data.sheets.SheetParameterRepository import SheetParameterRepository
        from ...data.destination.DestinationStore import DestinationStore
        from ...data.naming.NamingPatternStore import NamingPatternStore
        from ...services.formats.PdfExporterService import PdfExporterService
        from ...services.formats.DwgExporterService import DwgExporterService
        self._sheet_params = SheetParameterRepository(self._cfg)
        self._dest = DestinationStore()
        self._nstore = NamingPatternStore()
        self._pdf = PdfExporterService()
        self._dwg = DwgExporterService()
        # Components
        from ..helpers.UIResourceLoader import UIResourceLoader
        from ..helpers.UITemplateBinder import UITemplateBinder
        from ..components.ParameterSelectorComponent import ParameterSelectorComponent
        from ..components.DestinationPickerComponent import DestinationPickerComponent
        from ..components.ExportOptionsComponent import ExportOptionsComponent
        from ..components.NamingConfigComponent import NamingConfigComponent
        from ..components.CollectionPreviewComponent import CollectionPreviewComponent
        self._res_loader_cls = UIResourceLoader
        self._binder_cls = UITemplateBinder
        self._param_comp = ParameterSelectorComponent(self._sheet_params)
        self._dest_comp = DestinationPickerComponent(self._dest)
        self._opts_comp = ExportOptionsComponent(self._pdf, self._dwg)
        self._name_comp = NamingConfigComponent(self._nstore)
        self._grid_comp = CollectionPreviewComponent()

        # Window instance
        self._win = MainWindow(self._paths.main_xaml())
        # Initialize window state attributes
        self._win._available_param_names = []
        self._win._dest_valid = False
        try:
            self._win.Title = u"418 • Exportation"
        except Exception:
            pass

    def _merge_and_bind(self):
        # Merge resources
        merge_ok = self._res_loader_cls(self._win, self._paths).merge_all()
        if not merge_ok and _verbose:
            pass
        # Bind template children
        hosts = {
            'ParameterSelectorHost': [
                'CollectionExpander', 'ParamWarningText', 'UniqueErrorText',
                'ExportationCombo', 'CarnetCombo', 'DWGCombo', 'HelpButton', 'DarkModeToggle'
            ],
            'ExportOptionsHost': [
                'PDFExpander', 'PDFSetupCombo', 'PDFSeparateCheck', 'PDFCreateButton',
                'DWGExpander', 'DWGSetupCombo', 'DWGSeparateCheck', 'DWGCreateButton'
            ],
            'DestinationPickerHost': [
                'BrowseButton', 'PathTextBox', 'CreateSubfoldersCheck', 'SeparateByFormatCheck'
            ],
            'NamingConfigHost': [
                'SheetNamingButton', 'SetNamingButton'
            ],
            'CollectionPreviewHost': [
                'ExportProgressBar', 'PreviewCounterText', 'CollectionGrid', 'ExportStatusText', 'ExportButton'
            ],
        }
        self._binder_cls(self._win).bind(hosts)
        # Debug: verify ParameterSelectorHost is bound
        if _verbose:
            if not hasattr(self._win, 'CollectionExpander'):
                pass
            if not hasattr(self._win, 'ExportationCombo'):
                pass

    def _load_param_combos(self):
        # Collect available parameters
        try:
            doc = __revit__.ActiveUIDocument.Document  # type: ignore
        except Exception:
            doc = None
        try:
            self._win._available_param_names = self._sheet_params.collect_for_collections(doc) if doc else []
        except Exception:
            self._win._available_param_names = []
        # Populate combos
        self._param_comp.populate(self._win)
        # Apply saved selections
        self._apply_saved_selection()
        # Check warnings and export button
        self._check_and_warn_insufficient()
        self._update_export_button_state()

    def _apply_saved_selection(self):
        saved_map = {}
        for cname in ("ExportationCombo","CarnetCombo","DWGCombo"):
            try:
                saved_map[cname] = self._cfg.get('sheet_param_' + cname)
            except Exception:
                saved_map[cname] = None
        for cname in ("ExportationCombo","CarnetCombo","DWGCombo"):
            ctrl = getattr(self._win, cname, None)
            if ctrl is None:
                continue
            saved = saved_map.get(cname)
            if not saved:
                continue
            try:
                idx = -1
                for i in range(ctrl.Items.Count):
                    if str(ctrl.Items[i]) == str(saved):
                        idx = i
                        break
                if idx >= 0:
                    ctrl.SelectedIndex = idx
            except Exception:
                pass

    def _get_selected_values(self):
        out = {}
        for cname in ("ExportationCombo","CarnetCombo","DWGCombo"):
            ctrl = getattr(self._win, cname, None)
            if ctrl is None:
                continue
            try:
                val = getattr(ctrl, 'SelectedItem', None)
                out[cname] = None if val is None else str(val)
            except Exception:
                out[cname] = None
        return out

    def _are_three_unique(self):
        selected = self._get_selected_values()
        vals = [v for v in selected.values() if v]
        if len(vals) != 3:
            return False
        return len(set(vals)) == 3

    def _check_and_warn_insufficient(self):
        try:
            from System.Windows import Visibility
        except Exception:
            class _V: Visible=0; Collapsed=2
            Visibility = _V()
        warn = getattr(self._win, 'ParamWarningText', None)
        unique_err = getattr(self._win, 'UniqueErrorText', None)
        expander = getattr(self._win, 'CollectionExpander', None)
        avail = getattr(self._win, '_available_param_names', None)
        count = len(avail) if isinstance(avail, list) else 0
        if warn is not None:
            try:
                warn.Visibility = Visibility.Visible if count < 3 else Visibility.Collapsed
            except Exception:
                pass
        if unique_err is not None:
            try:
                if count >= 3 and not self._are_three_unique():
                    unique_err.Visibility = Visibility.Visible
                else:
                    unique_err.Visibility = Visibility.Collapsed
            except Exception:
                pass
        if expander is not None:
            try:
                expander.Visibility = Visibility.Collapsed if count == 0 else Visibility.Visible
            except Exception:
                pass

    def _update_export_button_state(self):
        try:
            from System.Windows.Media import Brushes
        except Exception:
            Brushes = None
        btn = getattr(self._win, 'ExportButton', None)
        status = getattr(self._win, 'ExportStatusText', None)
        if btn is None:
            return
        avail = getattr(self._win, '_available_param_names', None)
        count = len(avail) if isinstance(avail, list) else 0
        dest_ok = bool(getattr(self._win, '_dest_valid', False))
        messages = []
        if not dest_ok:
            messages.append(u"Sélectionnez un dossier de destination valide.")
        if count < 1:
            messages.append(u"Aucun paramètre de feuille disponible.")
        enabled = (len(messages) == 0)
        try:
            btn.IsEnabled = enabled
        except Exception:
            pass
        if status is not None:
            try:
                if enabled:
                    status.Text = u"Prêt à exporter."
                    if Brushes is not None and hasattr(Brushes, 'Green'):
                        status.Foreground = Brushes.Green
                else:
                    status.Text = u" • ".join(messages)
                    if Brushes is not None and hasattr(Brushes, 'Red'):
                        status.Foreground = Brushes.Red
            except Exception:
                pass

    def _init_destination(self):
        try:
            from System.Windows.Media import Brushes
            from System.Windows.Controls import Control
        except Exception:
            Brushes = None
            Control = None
        # Set initial
        self._dest_comp.init_controls(self._win)
        # Validate & create
        ok, err = self._dest_comp.validate(self._win, create=True)
        self._win._dest_valid = bool(ok)
        try:
            if hasattr(self._win, 'PathTextBox'):
                if ok:
                    if Control:
                        self._win.PathTextBox.ClearValue(Control.BorderBrushProperty)
                        self._win.PathTextBox.ClearValue(Control.BackgroundProperty)
                else:
                    if Brushes:
                        self._win.PathTextBox.BorderBrush = Brushes.Red
        except Exception:
            pass
        # Wire events
        try:
            if hasattr(self._win, 'BrowseButton'):
                self._win.BrowseButton.Click += self._on_browse
            if hasattr(self._win, 'PathTextBox'):
                self._win.PathTextBox.TextChanged += self._on_path_changed
        except Exception:
            pass
        # Toggles
        try:
            def getv(k, d=False):
                try:
                    return self._cfg.get(k, '') == '1'
                except Exception:
                    return d
            def setv(k, v):
                try:
                    self._cfg.set(k, '1' if v else '0')
                except Exception:
                    pass
            if hasattr(self._win, 'CreateSubfoldersCheck'):
                self._win.CreateSubfoldersCheck.IsChecked = getv('create_subfolders', False)
                self._win.CreateSubfoldersCheck.Checked += lambda s,a: setv('create_subfolders', True)
                self._win.CreateSubfoldersCheck.Unchecked += lambda s,a: setv('create_subfolders', False)
            if hasattr(self._win, 'SeparateByFormatCheck'):
                self._win.SeparateByFormatCheck.IsChecked = getv('separate_format_folders', False)
                self._win.SeparateByFormatCheck.Checked += lambda s,a: setv('separate_format_folders', True)
                self._win.SeparateByFormatCheck.Unchecked += lambda s,a: setv('separate_format_folders', False)
        except Exception:
            pass

    def _on_browse(self, sender, args):
        try:
            chosen = self._dest.choose_destination_explorer(save=True)
        except Exception:
            chosen = None
        if chosen:
            try:
                self._win.PathTextBox.Text = chosen
            except Exception:
                pass
            self._on_path_changed(None, None)

    def _on_path_changed(self, sender, args):
        try:
            from System.Windows.Media import Brushes
            from System.Windows.Controls import Control
        except Exception:
            Brushes = None
            Control = None

        ok, err = self._dest_comp.validate(self._win, create=False)
        self._win._dest_valid = bool(ok)

        try:
            if hasattr(self._win, 'PathTextBox'):
                if ok:
                    if Control:
                        self._win.PathTextBox.ClearValue(Control.BorderBrushProperty)
                        self._win.PathTextBox.ClearValue(Control.BackgroundProperty)
                else:
                    if Brushes:
                        self._win.PathTextBox.BorderBrush = Brushes.Red
        except Exception:
            pass

        self._update_export_button_state()

    def _init_pdf_dwg(self):
        self._opts_comp.populate_pdf(self._win)
        self._opts_comp.populate_dwg(self._win)
        # Hook create buttons
        try:
            if hasattr(self._win, 'PDFCreateButton'):
                self._win.PDFCreateButton.Click += self._on_create_pdf
        except Exception:
            pass
        try:
            if hasattr(self._win, 'DWGCreateButton'):
                self._win.DWGCreateButton.Click += self._on_create_dwg
        except Exception:
            pass

    def _on_create_pdf(self, sender, args):
        try:
            from .SetupEditorWindow import open_setup_editor
            if open_setup_editor(kind='pdf'):
                self._opts_comp.populate_pdf(self._win)
        except Exception:
            pass

    def _on_create_dwg(self, sender, args):
        try:
            from .SetupEditorWindow import open_setup_editor
            if open_setup_editor(kind='dwg'):
                self._opts_comp.populate_dwg(self._win)
        except Exception:
            pass

    def _wire_param_events(self):
        for cname in ("ExportationCombo","CarnetCombo","DWGCombo"):
            ctrl = getattr(self._win, cname, None)
            if ctrl is None:
                continue
            try:
                ctrl.SelectionChanged += self._on_param_changed
            except Exception:
                pass

    def _on_param_changed(self, sender, args):
        name = getattr(sender, 'Name', None) or ''
        val = getattr(sender, 'SelectedItem', None)
        if val:
            try:
                self._cfg.set('sheet_param_' + name, str(val))
            except Exception:
                pass
        self._check_and_warn_insufficient()
        self._update_export_button_state()
        self._grid_comp.populate(self._win, self._get_selected_values())

    def _wire_naming_buttons(self):
        try:
            if hasattr(self._win, 'SheetNamingButton'):
                self._win.SheetNamingButton.Click += self._on_open_sheet_naming
            if hasattr(self._win, 'SetNamingButton'):
                self._win.SetNamingButton.Click += self._on_open_set_naming
        except Exception:
            pass

    def _on_open_sheet_naming(self, s,a):
        try:
            from ..windows.PikerWindow import open_modal
            def _refresh(sender, args):
                try:
                    self._name_comp.refresh_buttons(self._win)
                    self._grid_comp.populate(self._win, self._get_selected_values())
                except Exception:
                    pass

            open_modal(kind='sheet', title=u"Nommage des feuilles", on_close=_refresh)
            _refresh(None, None)
        except Exception:
            pass

    def _on_open_set_naming(self, s,a):
        try:
            from ..windows.PikerWindow import open_modal
            def _refresh(sender, args):
                try:
                    self._name_comp.refresh_buttons(self._win)
                    self._grid_comp.populate(self._win, self._get_selected_values())
                except Exception:
                    pass

            open_modal(kind='set', title=u"Nommage des carnets", on_close=_refresh)
            _refresh(None, None)
        except Exception:
            pass

    def _wire_grid_click(self):
        try:
            if hasattr(self._win, 'CollectionGrid') and self._win.CollectionGrid is not None:
                self._win.CollectionGrid.PreviewMouseLeftButtonDown += self._on_grid_click
        except Exception:
            pass

    def _on_grid_click(self, sender, e):
        try:
            from System.Windows import DependencyObject
            from System.Windows.Media import VisualTreeHelper
            from System.Windows.Controls import DataGridRow
        except Exception:
            return
        try:
            src = getattr(e, 'OriginalSource', None)
            obj = src if isinstance(src, DependencyObject) else None
            row = None
            while obj is not None:
                try:
                    if isinstance(obj, DataGridRow):
                        row = obj
                        break
                except Exception:
                    pass
                try:
                    obj = VisualTreeHelper.GetParent(obj)
                except Exception:
                    obj = None
            if row is None:
                return
            if getattr(row, 'IsSelected', False):
                try:
                    row.IsSelected = False
                    e.Handled = True
                except Exception:
                    pass
        except Exception:
            pass

    def _wire_export(self):
        try:
            if hasattr(self._win, 'ExportButton'):
                self._win.ExportButton.Click += self._on_export
        except Exception:
            pass

    def _wire_help_button(self):
        try:
            if hasattr(self._win, 'HelpButton'):
                self._win.HelpButton.Click += self._on_help_click
        except Exception:
            pass

    def _on_help_click(self, sender, args):
        try:
            from .HelpWindow import show_help
            content = (
                "Les paramètres de feuille permettent de contrôler quels jeux de feuilles sont exportés et comment.\n\n"
                "• Exportation : Paramètre Oui/Non pour activer l'export de la feuille.\n"
                "• Export PDF compilé : Paramètre Oui/Non pour inclure la feuille dans un carnet PDF unique.\n"
                "• Export en DWG : Paramètre Oui/Non pour générer également un fichier DWG pour cette feuille.\n\n"
                "Ces paramètres doivent être créés dans votre projet Revit en tant que paramètres de projet ou partagés, "
                "appliqués à la catégorie 'Feuilles'."
            )
            show_help(content)
        except Exception:
            pass

    def _wire_dark_mode_toggle(self):
        try:
            if hasattr(self._win, 'DarkModeToggle'):
                self._win.DarkModeToggle.Checked += self._on_dark_mode
                self._win.DarkModeToggle.Unchecked += self._on_light_mode
        except Exception:
            pass

    def _on_dark_mode(self, sender, args):
        try:
            from System.Windows import ResourceDictionary
            from System import Uri, UriKind
            # Load dark theme resources
            dark_colors = self._paths.resource_path('ColorsDark.xaml')
            dark_styles = self._paths.resource_path('StylesDark.xaml')
            for path in [dark_colors, dark_styles]:
                rd = ResourceDictionary()
                rd.Source = Uri(path, UriKind.Absolute)
                self._win.Resources.MergedDictionaries.Add(rd)
        except Exception as e:
            print('MainWindowController [001]: Dark mode error: {}'.format(e))

    def _on_light_mode(self, sender, args):
        try:
            # Remove dark theme resources (assume last two dictionaries are dark)
            md = self._win.Resources.MergedDictionaries
            if len(md) >= 2:
                md.RemoveAt(md.Count-1)
                md.RemoveAt(md.Count-1)
        except Exception as e:
            print('MainWindowController [002]: Light mode error: {}'.format(e))

    def _wire_burger_menu(self):
        """Configure le menu burger"""
        try:
            if hasattr(self._win, 'BurgerButton'):
                self._win.BurgerButton.Click += self._toggle_burger_menu
            if hasattr(self._win, 'CloseBurgerButton'):
                self._win.CloseBurgerButton.Click += self._close_burger_menu
            if hasattr(self._win, 'BurgerMenuOverlay'):
                self._win.BurgerMenuOverlay.MouseLeftButtonDown += self._close_burger_menu
            
            # Window Chrome
            if hasattr(self._win, 'CloseWindowButton'):
                self._win.CloseWindowButton.Click += self._on_close_window
            if hasattr(self._win, 'TitleBar'):
                self._win.TitleBar.MouseLeftButtonDown += self._on_title_bar_mouse_down
            
            # Accordion behavior
            self._wire_accordion()
        except Exception:
            pass

    def _wire_profile_settings(self):
        try:
            if hasattr(self._win, 'ProfileSettingsButton'):
                self._win.ProfileSettingsButton.Click += self._on_profile_settings_click
        except Exception:
            pass

    def _on_profile_settings_click(self, sender, args):
        try:
            from .ConfigManagerWindow import ConfigManagerWindow
            win = ConfigManagerWindow()
            win.show(owner=self._win)
        except Exception as e:
            print('MainWindowController [004]: Profile settings error: {}'.format(e))

    def _wire_accordion(self):
        """Wire expanders to behave like an accordion (one open at a time)"""
        expanders = []
        for name in ['CollectionExpander', 'PDFExpander', 'DWGExpander']:
            if hasattr(self._win, name):
                expanders.append(getattr(self._win, name))
        
        def _on_expanded(sender, args):
            for exp in expanders:
                if exp != sender and exp.IsExpanded:
                    exp.IsExpanded = False
        
        for exp in expanders:
            try:
                exp.Expanded += _on_expanded
            except Exception:
                pass

    def _on_close_window(self, sender, args):
        try:
            self._win.Close()
        except Exception:
            pass

    def _on_title_bar_mouse_down(self, sender, args):
        try:
            self._win.DragMove()
        except Exception:
            pass

    def _toggle_burger_menu(self, sender, args):
        """Ouvre/ferme le menu burger"""
        try:
            from System.Windows import Visibility
        except Exception:
            return
        try:
            menu = getattr(self._win, 'BurgerMenu', None)
            overlay = getattr(self._win, 'BurgerMenuOverlay', None)
            
            if menu is not None:
                if menu.Visibility == Visibility.Visible:
                    menu.Visibility = Visibility.Collapsed
                    if overlay: overlay.Visibility = Visibility.Collapsed
                else:
                    menu.Visibility = Visibility.Visible
                    if overlay: overlay.Visibility = Visibility.Visible
        except Exception:
            pass

    def _close_burger_menu(self, sender, args):
        """Ferme le menu burger"""
        try:
            from System.Windows import Visibility
        except Exception:
            return
        try:
            menu = getattr(self._win, 'BurgerMenu', None)
            overlay = getattr(self._win, 'BurgerMenuOverlay', None)
            
            if menu is not None:
                menu.Visibility = Visibility.Collapsed
            if overlay is not None:
                overlay.Visibility = Visibility.Collapsed
        except Exception:
            pass

    def _on_export(self, sender, args):
        try:
            doc = __revit__.ActiveUIDocument.Document  # type: ignore
        except Exception:
            doc = None
        if doc is None:
            return
        try:
            from ...services.core.ExportOrchestrator import ExportOrchestrator
            orch = ExportOrchestrator()
            def _progress(i, n, text):
                try:
                    if hasattr(self._win, 'ExportProgressBar'):
                        self._win.ExportProgressBar.Maximum = max(n, 1)
                        self._win.ExportProgressBar.Value = i
                except Exception:
                    pass
                if text:
                    pass
            def _log(msg):
                pass
            def _get_ctrl(name):
                return getattr(self._win, name, None)
            orch.run(doc, _get_ctrl, progress_cb=_progress, log_cb=_log, ui_win=self._win)
        except Exception as e:
            print('MainWindowController [003]: Export error: {}'.format(e))

    def initialize(self):
        # Build visual tree and bind
        self._merge_and_bind()
        # Detect Revit theme (light/dark)
        try:
            from Autodesk.Revit.UI import UIThemeManager, UITheme
            theme = UIThemeManager.CurrentTheme
        except Exception:
            theme = 'light'
        if theme == UITheme.Dark:
            self._on_dark_mode(None, None)
        # Populate UI
        self._load_param_combos()
        self._name_comp.refresh_buttons(self._win)
        self._init_destination()
        self._init_pdf_dwg()
        # Populate preview grid
        self._grid_comp.populate(self._win, self._get_selected_values())
        # Wire events
        self._wire_param_events()
        self._wire_naming_buttons()
        self._wire_grid_click()
        self._wire_export()
        self._wire_help_button()
        self._wire_dark_mode_toggle()
        self._wire_burger_menu()
        self._wire_profile_settings()

    def show(self):
        self.initialize()
        try:
            self._win.ShowDialog()
        except Exception:
            self._win.show()
        return True
