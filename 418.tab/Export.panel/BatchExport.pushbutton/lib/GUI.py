# -*- coding: utf-8 -*-

"""GUI module centralisant l'ouverture de la fenêtre WPF pour l'export.

API publique:
    - GUI.show(): ouvre la fenêtre principale (modal si possible).

Notes:
    - Tous les fichiers XAML résident maintenant dans le dossier GUI/ :
            * MainWindow.xaml (fenêtre principale)
            * Piker.xaml (fenêtre modale de nommage)
    - Ce module dépend de pyRevit (pyrevit.forms.WPFWindow). L'analyse statique
        hors Revit peut indiquer des imports manquants; dans Revit/pyRevit, ils sont disponibles.
"""

from pyrevit import forms
import os
try:
    # WPF Visibility enum for showing/hiding warnings
    from System.Windows import Visibility
except Exception:
    # Fallback stub (for static analyzers / non-Revit runtime)
    class _V:  # type: ignore
        Visible = 0
        Collapsed = 2
    Visibility = _V()
try:
    # Revit API imports (disponibles dans l'environnement pyRevit)
    from Autodesk.Revit.DB import FilteredElementCollector, ViewSheet
    REVIT_API_AVAILABLE = True
except Exception:  # en analyse statique hors Revit
    REVIT_API_AVAILABLE = False

try:
    from System.Windows.Media import Brushes  # pour feedback visuel
except Exception:
    Brushes = None  # type: ignore

# ------------------------------- Helpers ------------------------------- #

GUI_FILE = os.path.join('GUI', 'MainWindow.xaml')
PIKER_FILE = os.path.join('GUI', 'Piker.xaml')
EXPORT_WINDOW_TITLE = u"418 • Exportation"


def _get_xaml_path():
    """Chemin absolu vers GUI/MainWindow.xaml."""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), GUI_FILE)


def _get_piker_xaml_path():
    """Chemin absolu vers GUI/Piker.xaml. Ne crée pas le fichier si absent."""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    p = os.path.join(base_dir, PIKER_FILE)
    return p


class ExportMainWindow(forms.WPFWindow):
    """Fenêtre WPF basée sur le XAML GUI.xaml."""
    def __init__(self):
        forms.WPFWindow.__init__(self, _get_xaml_path())
        try:
            self.Title = EXPORT_WINDOW_TITLE
        except Exception:
            # En environnement ironpython/pyRevit, certaines propriétés peuvent lever.
            pass
        # Etat interne pour éviter les boucles d'événements
        self._updating = False
        self._prev_selection = {}
        self._dest_valid = False

        # Peupler les ComboBox des paramètres de feuilles Revit
        try:
            _populate_sheet_param_combos(self)
        except Exception as e:
            print('[info] Remplissage combos échoué: {}'.format(e))
        # Appliquer sélection sauvegardée et abonner les événements
        try:
            _apply_saved_selection(self)
        except Exception as e:
            print('[info] Pré-sélection depuis config échouée: {}'.format(e))
        # (Ancienne logique d'unicité supprimée: on autorise des doublons,
        # mais on exigera l'unicité pour activer l'export)
        # Vérifier si suffisamment de paramètres pour trois sélections uniques
        try:
            _check_and_warn_insufficient(self)
        except Exception:
            pass
        # Peupler le tableau récapitulatif des jeux de feuilles
        try:
            _populate_sheet_sets(self)
        except Exception as e:
            print('[info] Récap jeux de feuilles échoué: {}'.format(e))
        # Mettre l'état du bouton Export
        try:
            _update_export_button_state(self)
        except Exception:
            pass
        # Abonnements
        for _cname in _PARAM_COMBOS:
            try:
                ctrl = getattr(self, _cname)
                ctrl.SelectionChanged += self._on_param_combo_changed
            except Exception:
                pass
        # Abonnement du bouton Export
        try:
            if hasattr(self, 'ExportButton'):
                self.ExportButton.Click += self._on_export_clicked
        except Exception:
            pass
        # Abonnements des boutons Nommage
        try:
            if hasattr(self, 'SheetNamingButton'):
                self.SheetNamingButton.Click += self._on_open_sheet_naming
            if hasattr(self, 'SetNamingButton'):
                self.SetNamingButton.Click += self._on_open_set_naming
        except Exception:
            pass
        # Destination: initialiser, lier événements
        try:
            if hasattr(self, 'BrowseButton'):
                self.BrowseButton.Click += self._on_browse_clicked
            if hasattr(self, 'PathTextBox'):
                # Valeur initiale depuis config
                from .destination import get_saved_destination
                self.PathTextBox.Text = get_saved_destination()
                # Valider et créer si besoin
                self._validate_destination(create=True)
                # Écouter les modifications manuelles
                self.PathTextBox.TextChanged += self._on_path_changed
            # Toggles destination
            self._init_destination_toggles()
        except Exception:
            pass
        # PDF/DWG setups & toggles
        try:
            self._init_pdf_dwg_controls()
        except Exception as e:
            print('[info] init PDF/DWG échouée:', e)
        # (Bouton de sauvegarde supprimé)
        # Snapshot des sélections pour pouvoir revenir en arrière si besoin
        try:
            self._prev_selection = _get_selected_values(self)
        except Exception:
            pass
        # Afficher les patterns de nommage sauvegardés sur les boutons
        try:
            self._refresh_naming_buttons()
        except Exception:
            pass
        # Permettre le toggle d'ouverture/fermeture des détails en cliquant la ligne
        try:
            if hasattr(self, 'CollectionGrid') and self.CollectionGrid is not None:
                self.CollectionGrid.PreviewMouseLeftButtonDown += self._on_grid_preview_mouse_left_button_down
        except Exception:
            pass

    # Événement: mémoriser le choix utilisateur
    def _on_param_combo_changed(self, sender, args):
        if getattr(self, '_updating', False):
            return
        try:
            self._updating = True
            # Ancienne contrainte d'unicité supprimée: on laisse le choix
            # Mettre à jour l'instantané "avant"
            self._prev_selection = _get_selected_values(self)
            # Auto-save: persister la valeur du sender après ajustement
            name = getattr(sender, 'Name', None) or 'Unknown'
            val = getattr(sender, 'SelectedItem', None)
            if val is not None:
                _save_param_selection(name, str(val))
            # Mettre à jour l'avertissement si insuffisant
            _check_and_warn_insufficient(self)
            # Mettre à jour l'état du bouton Export
            _update_export_button_state(self)
            # Rafraîchir l'aperçu des collections
            _populate_sheet_sets(self)
        except Exception:
            pass
        finally:
            self._updating = False

    # Clic sur Export
    def _on_export_clicked(self, sender, args):
        try:
            selected = _get_selected_values(self)
            print('[info] Export lancé avec paramètres:', selected)
            # Exécuter l'export via module exporter
            try:
                doc = __revit__.ActiveUIDocument.Document  # type: ignore
            except Exception:
                doc = None
            if doc is None:
                print('[info] Document Revit introuvable')
                return
            from .exporter import execute_exports
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
            # Callback statut pour mettre à jour le tableau en direct
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

    # Permettre de désélectionner une ligne par clic si elle est déjà sélectionnée,
    # afin de refermer les RowDetails (RowDetailsVisibilityMode=VisibleWhenSelected)
    def _on_grid_preview_mouse_left_button_down(self, sender, e):
        try:
            # Retrouver le DataGridRow depuis la source de l'événement
            from System.Windows import DependencyObject
            from System.Windows.Media import VisualTreeHelper
            from System.Windows.Controls import DataGridRow
        except Exception:
            return
        try:
            src = getattr(e, 'OriginalSource', None)
            obj = src if isinstance(src, DependencyObject) else None
            row = None
            # Remonter l'arbre visuel jusqu'à un DataGridRow
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
            # Si déjà sélectionnée, on la désélectionne et on consomme l'événement
            if getattr(row, 'IsSelected', False):
                try:
                    row.IsSelected = False
                    e.Handled = True
                except Exception:
                    pass
        except Exception:
            pass

    # Ouvrir la modale Piker.xaml depuis la section Nommage
    def _on_open_sheet_naming(self, sender, args):
        try:
            from . import piker
            piker.open_modal(kind='sheet', title=u"Nommage des feuilles")
            self._refresh_naming_buttons()
        except Exception as e:
            print('[info] Ouverture Piker (feuilles) échouée: {}'.format(e))

    def _on_open_set_naming(self, sender, args):
        try:
            from . import piker
            piker.open_modal(kind='set', title=u"Nommage des carnets")
            self._refresh_naming_buttons()
        except Exception as e:
            print('[info] Ouverture Piker (carnets) échouée: {}'.format(e))

    def _refresh_naming_buttons(self):
        try:
            from .naming import load_pattern
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

    # ---------------------- Destination: handlers & helpers ---------------------- #
    def _on_browse_clicked(self, sender, args):
        try:
            from .destination import choose_destination_explorer
            chosen = choose_destination_explorer(save=True)
            if chosen:
                try:
                    self.PathTextBox.Text = chosen
                except Exception:
                    pass
                self._validate_destination(create=True)
                _update_export_button_state(self)
        except Exception as e:
            print('[info] Sélection dossier échouée: {}'.format(e))

    def _on_path_changed(self, sender, args):
        # Valide à la volée sans créer le dossier
        try:
            self._validate_destination(create=False)
            _update_export_button_state(self)
        except Exception:
            pass

    def _validate_destination(self, create=False):
        """Valide/Crée le dossier, donne un feedback visuel et persiste la valeur."""
        try:
            from .destination import ensure_directory, set_saved_destination
        except Exception:
            return False
        path = ''
        try:
            path = self.PathTextBox.Text or ''
        except Exception:
            path = ''
        ok = False
        err = None
        if path:
            if create:
                ok, err = ensure_directory(path)
            else:
                try:
                    import os as _os
                    ok = _os.path.isdir(path)
                except Exception:
                    ok = False
        # Feedback visuel
        try:
            if ok:
                if Brushes is not None:
                    self.PathTextBox.BorderBrush = Brushes.Gray
                    self.PathTextBox.Background = Brushes.White
                self.PathTextBox.ToolTip = path
                # Persister si valide
                set_saved_destination(path)
            else:
                if Brushes is not None:
                    self.PathTextBox.BorderBrush = Brushes.Red
                    # léger rose pour signaler l'erreur
                    self.PathTextBox.Background = Brushes.MistyRose if hasattr(Brushes, 'MistyRose') else self.PathTextBox.Background
                self.PathTextBox.ToolTip = err or u"Chemin invalide"
        except Exception:
            pass
        self._dest_valid = bool(ok)
        return self._dest_valid

    def _init_destination_toggles(self):
        # Lecture depuis config (1/0)
        try:
            getv = lambda k, d=False: (CONFIG.get(k, '') == '1') if CONFIG else d
            setv = lambda k, v: CONFIG.set(k, '1' if v else '0') if CONFIG else None
            if hasattr(self, 'CreateSubfoldersCheck'):
                self.CreateSubfoldersCheck.IsChecked = getv('create_subfolders', False)
                self.CreateSubfoldersCheck.Checked += lambda s,a: setv('create_subfolders', True)
                self.CreateSubfoldersCheck.Unchecked += lambda s,a: setv('create_subfolders', False)
            if hasattr(self, 'SeparateByFormatCheck'):
                self.SeparateByFormatCheck.IsChecked = getv('separate_format_folders', False)
                self.SeparateByFormatCheck.Checked += lambda s,a: setv('separate_format_folders', True)
                self.SeparateByFormatCheck.Unchecked += lambda s,a: setv('separate_format_folders', False)
        except Exception:
            pass

    # ---------------------- PDF / DWG Setups ---------------------- #
    def _init_pdf_dwg_controls(self):
        doc = None
        try:
            doc = __revit__.ActiveUIDocument.Document  # type: ignore
        except Exception:
            doc = None
        # PDF setups
        try:
            from .pdf_export import list_all_pdf_setups, get_saved_pdf_setup, set_saved_pdf_setup, get_saved_pdf_separate, set_saved_pdf_separate
            if hasattr(self, 'PDFSetupCombo'):
                pdf_names = list_all_pdf_setups(doc)
                self.PDFSetupCombo.Items.Clear()
                if pdf_names:
                    for n in pdf_names:
                        self.PDFSetupCombo.Items.Add(n)
                    # Rétablir sélection
                    saved = get_saved_pdf_setup()
                    if saved and saved in pdf_names:
                        self.PDFSetupCombo.SelectedIndex = pdf_names.index(saved)
                    else:
                        self.PDFSetupCombo.SelectedIndex = 0
                else:
                    self.PDFSetupCombo.Items.Add('(Aucun réglage PDF)')
                    self.PDFSetupCombo.SelectedIndex = 0
                # Event
                self.PDFSetupCombo.SelectionChanged += lambda s,a: set_saved_pdf_setup(str(getattr(self.PDFSetupCombo,'SelectedItem', '')))
            if hasattr(self, 'PDFSeparateCheck'):
                self.PDFSeparateCheck.IsChecked = get_saved_pdf_separate(False)
                self.PDFSeparateCheck.Checked += lambda s,a: set_saved_pdf_separate(True)
                self.PDFSeparateCheck.Unchecked += lambda s,a: set_saved_pdf_separate(False)
            if hasattr(self, 'PDFCreateButton'):
                self.PDFCreateButton.Click += self._on_create_pdf_setup
        except Exception as e:
            print('[info] PDF setups non initialisés:', e)
        # DWG setups
        try:
            from .dwg_export import list_all_dwg_setups, get_saved_dwg_setup, set_saved_dwg_setup, get_saved_dwg_separate, set_saved_dwg_separate
            if hasattr(self, 'DWGSetupCombo'):
                dwg_names = list_all_dwg_setups(doc)
                self.DWGSetupCombo.Items.Clear()
                if dwg_names:
                    for n in dwg_names:
                        self.DWGSetupCombo.Items.Add(n)
                    saved = get_saved_dwg_setup()
                    if saved and saved in dwg_names:
                        self.DWGSetupCombo.SelectedIndex = dwg_names.index(saved)
                    else:
                        self.DWGSetupCombo.SelectedIndex = 0
                else:
                    self.DWGSetupCombo.Items.Add('(Aucun réglage DWG)')
                    self.DWGSetupCombo.SelectedIndex = 0
                self.DWGSetupCombo.SelectionChanged += lambda s,a: set_saved_dwg_setup(str(getattr(self.DWGSetupCombo,'SelectedItem', '')))
            if hasattr(self, 'DWGSeparateCheck'):
                self.DWGSeparateCheck.IsChecked = get_saved_dwg_separate(False)
                self.DWGSeparateCheck.Checked += lambda s,a: set_saved_dwg_separate(True)
                self.DWGSeparateCheck.Unchecked += lambda s,a: set_saved_dwg_separate(False)
            if hasattr(self, 'DWGCreateButton'):
                self.DWGCreateButton.Click += self._on_create_dwg_setup
        except Exception as e:
            print('[info] DWG setups non initialisés:', e)

    def _refresh_pdf_combo(self):
        try:
            doc = __revit__.ActiveUIDocument.Document  # type: ignore
        except Exception:
            doc = None
        try:
            from .pdf_export import list_all_pdf_setups, get_saved_pdf_setup
            if not hasattr(self, 'PDFSetupCombo'):
                return
            names = list_all_pdf_setups(doc)
            self.PDFSetupCombo.Items.Clear()
            for n in names:
                self.PDFSetupCombo.Items.Add(n)
            saved = get_saved_pdf_setup()
            if saved and saved in names:
                self.PDFSetupCombo.SelectedIndex = names.index(saved)
            elif names:
                self.PDFSetupCombo.SelectedIndex = 0
        except Exception:
            pass

    def _refresh_dwg_combo(self):
        try:
            doc = __revit__.ActiveUIDocument.Document  # type: ignore
        except Exception:
            doc = None
        try:
            from .dwg_export import list_all_dwg_setups, get_saved_dwg_setup
            if not hasattr(self, 'DWGSetupCombo'):
                return
            names = list_all_dwg_setups(doc)
            self.DWGSetupCombo.Items.Clear()
            for n in names:
                self.DWGSetupCombo.Items.Add(n)
            saved = get_saved_dwg_setup()
            if saved and saved in names:
                self.DWGSetupCombo.SelectedIndex = names.index(saved)
            elif names:
                self.DWGSetupCombo.SelectedIndex = 0
        except Exception:
            pass

    def _on_create_pdf_setup(self, sender, args):
        try:
            from .setup_editor import open_setup_editor
            if open_setup_editor(kind='pdf'):
                self._refresh_pdf_combo()
        except Exception as e:
            print('[info] Création réglage PDF échouée:', e)

    def _on_create_dwg_setup(self, sender, args):
        try:
            from .setup_editor import open_setup_editor
            if open_setup_editor(kind='dwg'):
                self._refresh_dwg_combo()
        except Exception as e:
            print('[info] Création réglage DWG échouée:', e)



def _show_ui():
    """Affiche la fenêtre principale si le XAML existe."""
    xaml_path = _get_xaml_path()
    if not os.path.exists(xaml_path):
        print('[info] fenetre_wpf.xaml introuvable')
        return False
    try:
        win = ExportMainWindow()
        # Modal si possible
        try:
            win.ShowDialog()
        except Exception:
            win.show()
        return True
    except Exception as e:
        print('[info] Erreur ouverture UI: {}'.format(e))
        return False


class GUI:
    @staticmethod
    def show():
        """Ouvre la fenêtre d'export et renvoie True si affichée avec succès."""
        return _show_ui()


## Piker extrait dans module séparé (.piker). L'ancienne classe et l'appel modal
## sont supprimés ici pour alléger le fichier.


# ------------------------------- Paramètres & jeux de feuilles (délégués aux modules) ------------------------------- #

from .config import UserConfigStore as UC
from .sheets import collect_sheet_parameter_names, get_sheet_sets

# Store de config (namespace par défaut)
CONFIG = UC('batch_export')


# ------------------------------- Accès config (helpers) ------------------------------- #

_PARAM_COMBOS = ["ExportationCombo", "CarnetCombo", "DWGCombo"]


def _config_key_for(cname):
    return 'sheet_param_{}'.format(cname)


def _load_saved_param_selections():
    """Retourne dict {ComboName: saved_value_or_None}."""
    saved = {}
    for cname in _PARAM_COMBOS:
        try:
            saved[cname] = CONFIG.get(_config_key_for(cname))
        except Exception:
            saved[cname] = None
    return saved


def _save_param_selection(combo_name, value):
    """Persiste la valeur (string) pour un combo (ignore None)."""
    if value in (None, ''):
        return
    try:
        CONFIG.set(_config_key_for(combo_name), value)
    except Exception:
        pass


def _get_sheet_sets(doc):
    return get_sheet_sets(doc)


def _populate_sheet_sets(win):
    """Remplit la ListView CollectionPreviewList avec un tableau des collections (6 colonnes),
    chaque ligne étant extensible pour afficher un sous-tableau des feuilles.

    Colonnes (collections): Nom | Feuilles | Export | Carnet | DWG | Statut
    Sous-table (feuilles): Nom | Format | Statut
    """
    try:
        lst = getattr(win, 'CollectionGrid', None)
        doc = __revit__.ActiveUIDocument.Document  # type: ignore
        if lst is None or doc is None or not REVIT_API_AVAILABLE:
            return

        # Imports .NET nécessaires
        try:
            from System.Collections.ObjectModel import ObservableCollection  # type: ignore
            from System.Windows.Data import CollectionViewSource, PropertyGroupDescription  # type: ignore
        except Exception:
            ObservableCollection = None  # type: ignore
            CollectionViewSource = None  # type: ignore
            PropertyGroupDescription = None  # type: ignore
        try:
            from Autodesk.Revit import DB  # type: ignore
        except Exception:
            DB = None  # type: ignore

        # Helpers
        def _collections(document):
            if DB is None:
                return []
            try:
                return list(DB.FilteredElementCollector(document).OfClass(DB.SheetCollection).ToElements())
            except Exception:
                return []

        def _sheets_in(document, collection):
            if DB is None:
                return []
            out = []
            try:
                for vs in DB.FilteredElementCollector(document).OfClass(DB.ViewSheet).ToElements():
                    try:
                        if vs.SheetCollectionId == collection.Id:
                            out.append(vs)
                    except Exception:
                        continue
            except Exception:
                pass
            return out

        def _read_flag(elem, pname, default=False):
            if not pname:
                return default
            try:
                for p in elem.Parameters:
                    try:
                        d = getattr(p, 'Definition', None)
                        if d is not None and d.Name == pname:
                            try:
                                v = p.AsInteger()
                                return bool(v)
                            except Exception:
                                return default
                    except Exception:
                        continue
            except Exception:
                pass
            return default

        # Sélections courantes
        selected = _get_selected_values(win)
        pname_export = selected.get('ExportationCombo')
        pname_carnet = selected.get('CarnetCombo')
        pname_dwg = selected.get('DWGCombo')

        # Nommage feuilles
        try:
            from .naming import load_pattern, resolve_rows_for_element
            _, sheet_rows = load_pattern('sheet')
        except Exception:
            sheet_rows = []
        try:
            from .destination import sanitize_filename
        except Exception:
            def sanitize_filename(s):
                return s or ''

    # Préparer la collection d'items
        items = []
        cols = _collections(doc)
        # Trier les collections par nom (insensible à la casse)
        cols_sorted = sorted(cols, key=lambda c: (getattr(c, 'Name', '') or '').lower())
        for coll in cols_sorted:
            try:
                do_export = _read_flag(coll, pname_export, False)
                per_sheet = _read_flag(coll, pname_carnet, False)
                do_dwg = _read_flag(coll, pname_dwg, False)
                do_pdf = bool(do_export)
                sheets = _sheets_in(doc, coll)

                # Construire le sous-tableau (Details) et trier par Nom
                details = []
                # PDF
                if do_pdf:
                    if per_sheet:
                        for sh in sheets:
                            try:
                                base = sanitize_filename(resolve_rows_for_element(sh, sheet_rows, empty_fallback=False)) or getattr(sh, 'Name', 'Sheet')
                                details.append({'Nom': base, 'Format': 'PDF', 'StatutText': u'', 'StatutColor': Brushes.Green if Brushes is not None else None})
                            except Exception:
                                continue
                    else:
                        base = ''
                        try:
                            if sheets:
                                base = sanitize_filename(resolve_rows_for_element(sheets[0], sheet_rows, empty_fallback=False))
                        except Exception:
                            base = ''
                        if not base:
                            base = coll.Name
                        details.append({'Nom': base, 'Format': 'PDF (combiné)', 'StatutText': u'', 'StatutColor': Brushes.Green if Brushes is not None else None})
                # DWG
                if do_dwg:
                    for sh in sheets:
                        try:
                            base = sanitize_filename(resolve_rows_for_element(sh, sheet_rows, empty_fallback=False)) or getattr(sh, 'Name', 'Sheet')
                            details.append({'Nom': base, 'Format': 'DWG', 'StatutText': u'', 'StatutColor': Brushes.Green if Brushes is not None else None})
                        except Exception:
                            continue

                # Trier les détails par Nom
                try:
                    details.sort(key=lambda d: (d.get('Nom','') or '').lower())
                except Exception:
                    pass

                # Item collection (ligne principale)
                items.append({
                    'Nom': coll.Name,
                    'Feuilles': len(sheets),
                    'ExportText': u"\u2713" if do_pdf else u"\u2717",  # ✓ / ✗
                    'ExportColor': Brushes.Green if (Brushes is not None and do_pdf) else (Brushes.Gray if Brushes is not None else None),
                    'CarnetText': u"\u2713" if per_sheet else u"\u2717",
                    'CarnetColor': Brushes.Green if (Brushes is not None and per_sheet) else (Brushes.Gray if Brushes is not None else None),
                    'DWGText': u"\u2713" if do_dwg else u"\u2717",
                    'DWGColor': Brushes.Green if (Brushes is not None and do_dwg) else (Brushes.Gray if Brushes is not None else None),
                    'StatutText': u"",  # à remplir pendant l'export
                    'StatutColor': Brushes.Green if False else None,
                    'Details': details,
                })
            except Exception:
                continue

        # Trier les collections par Nom (insensible à la casse)
        try:
            items.sort(key=lambda i: (i.get('Nom','') or '').lower())
        except Exception:
            pass

        # Mémoriser pour mises à jour dynamiques et mettre à jour le compteur
        try:
            win._preview_items = items
        except Exception:
            win._preview_items = items
        try:
            counter = getattr(win, 'PreviewCounterText', None)
            if counter is not None:
                ncoll = len(items)
                nelems = sum(len(it.get('Details', []) or []) for it in items)
                counter.Text = u"Collections: {} • Éléments: {}".format(ncoll, nelems)
        except Exception:
            pass
        # Appliquer ItemsSource
        try:
            lst.ItemsSource = win._preview_items
        except Exception:
            pass
    except Exception:
        pass


# ---------------------- Mise à jour dynamique du statut (collection & feuilles) ---------------------- #

def _refresh_collection_grid(win):
    try:
        grid = getattr(win, 'CollectionGrid', None)
        if grid is None:
            return
        try:
            from System.Windows.Data import CollectionViewSource  # type: ignore
            view = CollectionViewSource.GetDefaultView(grid.ItemsSource)
            if view is not None:
                view.Refresh()
            else:
                grid.ItemsSource = list(grid.ItemsSource or [])
        except Exception:
            try:
                grid.Items.Refresh()
            except Exception:
                pass
    except Exception:
        pass


def _set_collection_status(win, collection_name, state):
    # state: 'progress' | 'ok' | 'error'
    try:
        items = getattr(win, '_preview_items', []) or []
        color = None
        txt = u""
        if state == 'progress':
            txt = u"En cours…"
            color = getattr(Brushes, 'DarkOrange', None) or getattr(Brushes, 'Orange', None) or getattr(Brushes, 'Gray', None)
        elif state == 'ok':
            txt = u"Terminé"
            color = getattr(Brushes, 'Green', None)
        elif state == 'error':
            txt = u"Erreur"
            color = getattr(Brushes, 'Red', None)
        for it in items:
            try:
                if it.get('Nom') == collection_name:
                    it['StatutText'] = txt
                    it['StatutColor'] = color
                    break
            except Exception:
                continue
    except Exception:
        pass


def _set_detail_status(win, collection_name, detail_name, detail_format, state):
    try:
        items = getattr(win, '_preview_items', []) or []
        color = None
        txt = u""
        if state == 'progress':
            txt = u"En cours…"
            color = getattr(Brushes, 'DarkOrange', None) or getattr(Brushes, 'Orange', None) or getattr(Brushes, 'Gray', None)
        elif state == 'ok':
            txt = u"Terminé"
            color = getattr(Brushes, 'Green', None)
        elif state == 'error':
            txt = u"Erreur"
            color = getattr(Brushes, 'Red', None)
        for it in items:
            try:
                if it.get('Nom') != collection_name:
                    continue
                for d in it.get('Details', []) or []:
                    try:
                        if (d.get('Nom') == detail_name) and (d.get('Format') == detail_format):
                            d['StatutText'] = txt
                            d['StatutColor'] = color
                            return
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception:
        pass


def _populate_sheet_param_combos(win):
    """Remplit ExportationCombo, CarnetCombo, DWGCombo avec les noms de paramètres.

    Si aucun paramètre trouvé ou API indisponible, insère un placeholder.
    """
    if not REVIT_API_AVAILABLE:
        _fill_combos_with_placeholder(win, "(API Revit indisponible)")
        return
    # Récupération du document actif via pyRevit
    try:
        doc = __revit__.ActiveUIDocument.Document  # type: ignore  # fourni par pyRevit
    except Exception:
        _fill_combos_with_placeholder(win, "(Document introuvable)")
        return

    param_names = collect_sheet_parameter_names(doc, CONFIG)
    if not param_names:
        _fill_combos_with_placeholder(win, "(Aucun paramètre booléen de feuille)")
        return

    target_combo_names = ["ExportationCombo", "CarnetCombo", "DWGCombo"]
    for cname in target_combo_names:
        ctrl = getattr(win, cname, None)
        if ctrl is None:
            continue
        try:
            # Nettoyage existant
            try:
                ctrl.Items.Clear()
            except Exception:
                pass
            for n in param_names:
                try:
                    ctrl.Items.Add(n)
                except Exception:
                    continue
            # Sélectionner premier par défaut
            if ctrl.Items.Count > 0:
                try:
                    ctrl.SelectedIndex = 0
                except Exception:
                    pass
        except Exception:
            print('[info] Impossible de remplir {}.'.format(cname))
    # Stocker pour contrôles ultérieurs
    try:
        win._available_param_names = param_names
    except Exception:
        pass


def _fill_combos_with_placeholder(win, text):
    for cname in ["ExportationCombo", "CarnetCombo", "DWGCombo"]:
        ctrl = getattr(win, cname, None)
        if ctrl is None:
            continue
        try:
            try:
                ctrl.Items.Clear()
            except Exception:
                pass
            ctrl.Items.Add(text)
            ctrl.SelectedIndex = 0
        except Exception:
            pass
    try:
        win._available_param_names = []
    except Exception:
        pass


# ------------------------------- État & validations des ComboBox ------------------------------- #

def _get_selected_values(win):
    out = {}
    for cname in ["ExportationCombo", "CarnetCombo", "DWGCombo"]:
        ctrl = getattr(win, cname, None)
        if ctrl is None:
            continue
        try:
            val = getattr(ctrl, 'SelectedItem', None)
            out[cname] = None if val is None else str(val)
        except Exception:
            out[cname] = None
    return out


def _are_three_unique(win):
    """Retourne (bool, selected_dict) indiquant si 3 valeurs non vides et toutes différentes."""
    selected = _get_selected_values(win)
    vals = [v for v in selected.values() if v]
    if len(vals) != 3:
        return False, selected
    if len(set(vals)) != 3:
        return False, selected
    return True, selected


def _check_and_warn_insufficient(win):
    """Affiche/masque un avertissement si < 3 paramètres uniques disponibles."""
    try:
        warn = getattr(win, 'ParamWarningText', None)
        unique_err = getattr(win, 'UniqueErrorText', None)
        expander = getattr(win, 'CollectionExpander', None)
        if warn is None:
            return
        avail = getattr(win, '_available_param_names', None)
        count = len(avail) if isinstance(avail, list) else 0
        # Si moins de 3 paramètres distincts, afficher l'avertissement
        if count < 3:
            warn.Visibility = Visibility.Visible
            warn.Text = u"Paramètres insuffisants pour assurer des sélections uniques ({} trouvés).".format(count)
        else:
            warn.Visibility = Visibility.Collapsed
        # Gestion de l'erreur d'unicité (affichée seulement si on a au moins 3 paramètres disponibles)
        if unique_err is not None:
            try:
                are_unique, _ = _are_three_unique(win)
                if count >= 3 and not are_unique:
                    unique_err.Visibility = Visibility.Visible
                else:
                    unique_err.Visibility = Visibility.Collapsed
            except Exception:
                pass
        # Si aucun paramètre booléen n'est disponible, masquer l'expander
        if expander is not None:
            if count == 0:
                expander.Visibility = Visibility.Collapsed
            else:
                expander.Visibility = Visibility.Visible
    except Exception:
        pass


def _update_export_button_state(win):
    """Active le bouton Export si la destination est valide et qu'au moins un paramètre est disponible.

    Note: l'ancienne contrainte d'unicité des 3 sélections est levée pour éviter de bloquer l'export.
    """
    try:
        btn = getattr(win, 'ExportButton', None)
        status = getattr(win, 'ExportStatusText', None)
        unique_err = getattr(win, 'UniqueErrorText', None)
        if btn is None:
            return
        avail = getattr(win, '_available_param_names', None)
        count = len(avail) if isinstance(avail, list) else 0
        dest_ok = bool(getattr(win, '_dest_valid', False))

        # Déterminer l'état et le message
        messages = []
        if not dest_ok:
            messages.append(u"Sélectionnez un dossier de destination valide.")
        if count < 1:
            messages.append(u"Aucun paramètre de feuille disponible.")

        enabled = (len(messages) == 0)
        btn.IsEnabled = enabled

        # Mettre à jour la ligne de statut
        if status is not None:
            try:
                if enabled:
                    status.Text = u"Prêt à exporter."  # message court et clair
                    if Brushes is not None and hasattr(Brushes, 'Green'):
                        status.Foreground = Brushes.Green
                else:
                    status.Text = u" • ".join(messages)
                    if Brushes is not None and hasattr(Brushes, 'Red'):
                        status.Foreground = Brushes.Red
            except Exception:
                pass

        # Cacher l'ancienne erreur d'unicité (plus bloquante)
        if unique_err is not None:
            try:
                unique_err.Visibility = Visibility.Collapsed
            except Exception:
                pass
    except Exception:
        pass
    # (Handler de sauvegarde supprimé)


def _apply_saved_selection(win):
    """Charge les sélections mémorisées pour chaque combo si l'item existe."""
    saved_map = _load_saved_param_selections()
    for cname in _PARAM_COMBOS:
        ctrl = getattr(win, cname, None)
        if ctrl is None:
            continue
        saved = saved_map.get(cname)
        if not saved:
            continue
        try:
            idx = -1
            try:
                for i in range(ctrl.Items.Count):
                    try:
                        if str(ctrl.Items[i]) == str(saved):
                            idx = i
                            break
                    except Exception:
                        continue
            except Exception:
                pass
            if idx >= 0:
                try:
                    ctrl.SelectedIndex = idx
                except Exception:
                    pass
        except Exception:
            pass