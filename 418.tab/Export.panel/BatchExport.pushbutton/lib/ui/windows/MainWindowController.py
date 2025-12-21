# -*- coding: utf-8 -*-
# Contrôleur de la fenêtre principale: construit la fenêtre et branche la logique UI

from __future__ import unicode_literals



try:
    from pyrevit import EXEC_PARAMS
    _verbose = EXEC_PARAMS.debug_mode
except Exception:
    _verbose = False

from .MainWindow import MainWindow
from .sections.DestinationSectionController import DestinationSectionController
from .sections.ExportSectionController import ExportSectionController
from .sections.BurgerMenuSectionController import BurgerMenuSectionController
from .sections.HelpSectionController import HelpSectionController
from .sections.ParametersSectionController import ParametersSectionController
from .sections.NamingSectionController import NamingSectionController
from .sections.PreviewSectionController import PreviewSectionController
from .sections.ThemeSectionController import ThemeSectionController
from .sections.WindowBindingController import WindowBindingController

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

        self._destination_section = DestinationSectionController(
            self._win,
            self._cfg,
            self._dest,
            self._dest_comp,
            on_destination_validity_changed=self._update_export_button_state,
        )
        self._export_section = ExportSectionController(self._win, self._opts_comp)
        self._preview_section = PreviewSectionController(self._win, self._grid_comp, self._get_selected_values)
        self._parameters_section = ParametersSectionController(
            self._win,
            self._cfg,
            self._sheet_params,
            self._param_comp,
            on_export_state_update=self._update_export_button_state,
            on_preview_update=self._preview_section.populate,
        )
        self._naming_section = NamingSectionController(
            self._win,
            self._name_comp,
            on_preview_update=self._preview_section.populate,
        )
        self._burger_section = BurgerMenuSectionController(self._win)
        self._help_section = HelpSectionController(self._win)
        self._theme_section = ThemeSectionController(self._win, self._paths)
        self._binding_section = WindowBindingController(
            self._win,
            self._paths,
            self._res_loader_cls,
            self._binder_cls,
            verbose=_verbose,
        )

    def _load_param_combos(self):
        self._parameters_section.initialize()

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

    def _check_and_warn_insufficient(self):
        self._parameters_section.check_warnings()

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
        self._destination_section.initialize()

    def _init_pdf_dwg(self):
        self._export_section.initialize()

    def _wire_param_events(self):
        self._parameters_section.wire_events()

    def _wire_naming_buttons(self):
        self._naming_section.wire_buttons()

    def _wire_grid_click(self):
        self._preview_section.wire_grid_click()

    def _wire_export(self):
        self._export_section.wire_export_button(self._on_export)

    def _wire_help_button(self):
        self._help_section.wire()

    def _wire_dark_mode_toggle(self):
        self._theme_section.wire_toggle()

    def _wire_burger_menu(self):
        self._burger_section.wire()

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
            # Refresh UI after modal closes
            self._refresh_ui()
        except Exception as e:
            print('MainWindowController [004]: Profile settings error: {}'.format(e))

    def _refresh_ui(self):
        """Refreshes the UI from current configuration."""
        try:
            # Reload combos selection
            self._parameters_section.apply_saved_selection()
            # Refresh naming buttons
            self._naming_section.refresh_buttons()
            # Refresh destination
            self._init_destination()
            # Refresh PDF/DWG options
            self._init_pdf_dwg()
            # Refresh grid
            self._preview_section.populate()
            # Check warnings
            self._parameters_section.check_warnings()
            self._update_export_button_state()
        except Exception as e:
            print('MainWindowController [005]: Refresh UI error: {}'.format(e))

    def _on_export(self, sender, args):
        self._export_section.run_export(self._win)

    def initialize(self):
        # Build visual tree and bind
        self._binding_section.merge_and_bind()
        self._theme_section.apply_initial_theme()
        # Populate UI
        self._load_param_combos()
        self._naming_section.initialize()
        self._init_destination()
        self._init_pdf_dwg()
        # Populate preview grid
        self._preview_section.populate()
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
