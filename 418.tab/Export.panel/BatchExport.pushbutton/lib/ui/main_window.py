# -*- coding: utf-8 -*-

# Fenêtre principale WPF pour l'export (classe unique)

from pyrevit import forms

# Etat/constantes partagés
from .state import EXPORT_WINDOW_TITLE, Visibility, REVIT_API_AVAILABLE, Brushes, CONFIG, _PARAM_COMBOS

# Chargement XAML et injection des sections
from .sections_loader import _get_xaml_path, _load_section_into

# Helpers UI (aperçu, paramètres, destination, PDF/DWG)
from .preview.grid import (
    _populate_sheet_sets,
    _refresh_collection_grid,
    _set_collection_status,
    _set_detail_status,
    _on_collection_grid_click,
)
from .params.combo_state import (
    _populate_sheet_param_combos,
    _apply_saved_selection,
    _check_and_warn_insufficient,
    _update_export_button_state,
    _get_selected_values,
)
from .pdf_dwg.panel import init_pdf_dwg_controls, refresh_pdf_combo, refresh_dwg_combo
from .destination.panel import validate_destination, init_destination_toggles


class ExportMainWindow(forms.WPFWindow):
    # Fenêtre WPF basée sur le XAML MainWindow.xaml
    def __init__(self):
        forms.WPFWindow.__init__(self, _get_xaml_path())
        try:
            self.Title = EXPORT_WINDOW_TITLE
        except Exception:
            pass
        # Charger les sections modulaires dans leurs hôtes
        try:
            _load_section_into(self, 'ParametersHost', 'ParametersSection.xaml')
        except Exception:
            pass
        try:
            _load_section_into(self, 'DestinationHost', 'DestinationSection.xaml')
        except Exception:
            pass
        try:
            _load_section_into(self, 'NamingHost', 'NamingSection.xaml')
        except Exception:
            pass
        try:
            _load_section_into(self, 'PreviewHost', 'PreviewSection.xaml')
        except Exception:
            pass
        # Brancher le toggle expand/collapse sur clic de ligne du DataGrid
        try:
            if hasattr(self, 'CollectionGrid'):
                self.CollectionGrid.PreviewMouseLeftButtonUp += lambda s,a: _on_collection_grid_click(self, s, a)
        except Exception:
            pass

        # Etats internes
        self._updating = False
        self._prev_selection = {}
        self._dest_valid = False
        self.REVIT_API_AVAILABLE = REVIT_API_AVAILABLE

        # Peupler les ComboBox des paramètres de feuilles Revit
        try:
            _populate_sheet_param_combos(self)
        except Exception as e:
            print('[info] Remplissage combos échoué: {}'.format(e))
        # Appliquer sélection sauvegardée
        try:
            _apply_saved_selection(self)
        except Exception as e:
            print('[info] Pré-sélection depuis config échouée: {}'.format(e))
        # Avertissements
        try:
            _check_and_warn_insufficient(self)
        except Exception:
            pass
        # Récapitulatif des jeux de feuilles
        try:
            _populate_sheet_sets(self)
        except Exception as e:
            print('[info] Récap jeux de feuilles échoué: {}'.format(e))
        # État bouton Export
        try:
            _update_export_button_state(self)
        except Exception:
            pass
        # Abonnements combos
        for _cname in _PARAM_COMBOS:
            try:
                ctrl = getattr(self, _cname)
                ctrl.SelectionChanged += self._on_param_combo_changed
            except Exception:
                pass
        # Bouton Export
        try:
            if hasattr(self, 'ExportButton'):
                self.ExportButton.Click += self._on_export_clicked
        except Exception:
            pass
        # Boutons Nommage
        try:
            if hasattr(self, 'SheetNamingButton'):
                self.SheetNamingButton.Click += self._on_open_sheet_naming
            if hasattr(self, 'SetNamingButton'):
                self.SetNamingButton.Click += self._on_open_set_naming
        except Exception:
            pass
        # Destination: init + événements
        try:
            if hasattr(self, 'BrowseButton'):
                self.BrowseButton.Click += self._on_browse_clicked
            if hasattr(self, 'PathTextBox'):
                from ..destination import get_saved_destination
                self.PathTextBox.Text = get_saved_destination()
                validate_destination(self, create=True)
                self.PathTextBox.TextChanged += self._on_path_changed
            init_destination_toggles(self)
        except Exception:
            pass
        # PDF/DWG setups & toggles
        try:
            init_pdf_dwg_controls(self)
        except Exception as e:
            print('[info] init PDF/DWG échouée:', e)

        # Snapshot des sélections
        try:
            self._prev_selection = _get_selected_values(self)
        except Exception:
            pass
        # Rafraîchir les boutons de nommage
        try:
            self._refresh_naming_buttons()
        except Exception:
            pass

    # Événement: combos de paramètres
    def _on_param_combo_changed(self, sender, args):
        if getattr(self, '_updating', False):
            return
        try:
            self._updating = True
            self._prev_selection = _get_selected_values(self)
            name = getattr(sender, 'Name', None) or 'Unknown'
            val = getattr(sender, 'SelectedItem', None)
            if val is not None:
                self._save_param_selection(name, str(val))
            _check_and_warn_insufficient(self)
            _update_export_button_state(self)
            _populate_sheet_sets(self)
        except Exception:
            pass
        finally:
            self._updating = False

    # Sauvegarde d'un choix combo vers CONFIG
    def _save_param_selection(self, combo_name, value):
        if value in (None, ''):
            return
        try:
            CONFIG.set('sheet_param_{}'.format(combo_name), value)
        except Exception:
            pass

    # Clic Export
    def _on_export_clicked(self, sender, args):
        try:
            selected = _get_selected_values(self)
            print('[info] Export lancé avec paramètres:', selected)
            try:
                doc = __revit__.ActiveUIDocument.Document  # type: ignore
            except Exception:
                doc = None
            if doc is None:
                print('[info] Document Revit introuvable')
                return
            from ..exporter import execute_exports

            def _progress(i, n, text):
                try:
                    if hasattr(self, 'ExportProgressBar'):
                        self.ExportProgressBar.Maximum = max(n, 1)
                        self.ExportProgressBar.Value = i
                except Exception:
                    pass
                if text:
                    print('[info]', text)

            def _log(msg):
                print('[info]', msg)

            def _get_ctrl(name):
                return getattr(self, name, None)

            def _status(kind, payload):
                try:
                    if kind == 'collection':
                        state = payload.get('state')
                        name = payload.get('name')
                        _set_collection_status(self, name, state)
                        _refresh_collection_grid(self)
                    elif kind == 'sheet':
                        state = payload.get('state')
                        cname = payload.get('collection')
                        nm = payload.get('name')
                        fmt = payload.get('format')
                        _set_detail_status(self, cname, nm, fmt, state)
                        _refresh_collection_grid(self)
                except Exception:
                    pass

            execute_exports(doc, _get_ctrl, progress_cb=_progress, log_cb=_log, ui_win=self)
        except Exception as e:
            print('[info] Erreur export:', e)

    # Ouvrir la modale de nommage (feuilles)
    def _on_open_sheet_naming(self, sender, args):
        try:
            from .. import piker
            piker.open_modal(kind='sheet', title=u"Nommage des feuilles")
            self._refresh_naming_buttons()
        except Exception as e:
            print('[info] Ouverture Piker (feuilles) échouée: {}'.format(e))

    # Ouvrir la modale de nommage (carnets)
    def _on_open_set_naming(self, sender, args):
        try:
            from .. import piker
            piker.open_modal(kind='set', title=u"Nommage des carnets")
            self._refresh_naming_buttons()
        except Exception as e:
            print('[info] Ouverture Piker (carnets) échouée: {}'.format(e))

    def _refresh_naming_buttons(self):
        try:
            from ..naming import load_pattern
        except Exception:
            return
        try:
            sheet_patt, _ = load_pattern('sheet')
        except Exception:
            sheet_patt = ''
        try:
            set_patt, _ = load_pattern('set')
        except Exception:
            set_patt = ''
        try:
            if hasattr(self, 'SheetNamingButton'):
                self.SheetNamingButton.Content = sheet_patt or '...'
        except Exception:
            pass
        try:
            if hasattr(self, 'SetNamingButton'):
                self.SetNamingButton.Content = set_patt or '...'
        except Exception:
            pass

    # Destination: navigateur
    def _on_browse_clicked(self, sender, args):
        try:
            from ..destination import choose_destination_explorer
            chosen = choose_destination_explorer(save=True)
            if chosen:
                try:
                    self.PathTextBox.Text = chosen
                except Exception:
                    pass
                validate_destination(self, create=True)
                _update_export_button_state(self)
        except Exception as e:
            print('[info] Sélection dossier échouée: {}'.format(e))

    def _on_path_changed(self, sender, args):
        try:
            validate_destination(self, create=False)
            _update_export_button_state(self)
        except Exception:
            pass

    # PDF/DWG: création réglages
    def _on_create_pdf_setup(self, sender, args):
        try:
            from ..setup_editor import open_setup_editor
            if open_setup_editor(kind='pdf'):
                refresh_pdf_combo(self)
        except Exception as e:
            print('[info] Création réglage PDF échouée:', e)

    def _on_create_dwg_setup(self, sender, args):
        try:
            from ..setup_editor import open_setup_editor
            if open_setup_editor(kind='dwg'):
                refresh_dwg_combo(self)
        except Exception as e:
            print('[info] Création réglage DWG échouée:', e)
