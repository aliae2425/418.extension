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
        except Exception:
            pass
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
        except Exception:
            pass
        finally:
            self._updating = False

    # Clic sur Export
    def _on_export_clicked(self, sender, args):
        try:
            selected = _get_selected_values(self)
            print('[info] Export lancé avec paramètres:', selected)
            # TODO: Implémenter la logique d'export réelle ici
        except Exception as e:
            print('[info] Erreur export:', e)

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
    """Remplit le ListView SheetSetsList avec les jeux de feuilles."""
    try:
        GUI_ListView = getattr(win, 'SheetSetsList', None)
        doc = __revit__.ActiveUIDocument.Document  # type: ignore

        data = _get_sheet_sets(doc)
        try:
            GUI_ListView.Items.Clear()
        except Exception:
            pass
        if not data:
            GUI_ListView.Items.Add({'Titre': 'Aucun jeu trouvé', 'Feuilles': 0})
            return
        for row in data:
            try:
                GUI_ListView.Items.Add(row)
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
    """Active le bouton Export si 3 sélections valides et uniques sont présentes."""
    try:
        btn = getattr(win, 'ExportButton', None)
        unique_err = getattr(win, 'UniqueErrorText', None)
        # Si le bouton n'existe pas, rien à faire
        if btn is None:
            return
        avail = getattr(win, '_available_param_names', None)
        count = len(avail) if isinstance(avail, list) else 0
        # Destination valide ?
        dest_ok = bool(getattr(win, '_dest_valid', False))
        if count < 3 or not dest_ok:
            btn.IsEnabled = False
            return
        are_unique, selected = _are_three_unique(win)
        if not are_unique:
            btn.IsEnabled = False
            # Afficher le message d'erreur d'unicité si pertinent
            if unique_err is not None:
                try:
                    unique_err.Visibility = Visibility.Visible
                except Exception:
                    pass
            return
        btn.IsEnabled = True
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