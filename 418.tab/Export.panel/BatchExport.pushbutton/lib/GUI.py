# -*- coding: utf-8 -*-

"""GUI module centralisant l'ouverture de la fenêtre WPF pour l'export.

API publique:
  - GUI.show(): ouvre la fenêtre principale (modal si possible).

Notes:
  - Ce module dépend de pyRevit (pyrevit.forms.WPFWindow). L'analyse statique
    hors Revit peut indiquer un import manquant; dans Revit/pyRevit, l'import
    est disponible.
"""

from pyrevit import forms
from Autodesk.Revit import DB
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

# ------------------------------- Helpers ------------------------------- #

GUI_FILE = 'GUI.xaml'
EXPORT_WINDOW_TITLE = u"418 • Exportation"


def _get_xaml_path():
    """Chemin absolu vers GUI.xaml situé un dossier au-dessus de ce fichier."""
    # GUI.py est dans .../BatchExport.pushbutton/lib
    # Le XAML est dans .../BatchExport.pushbutton/GUI.xaml
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), GUI_FILE)


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
        for _cname in ["ExportationCombo", "CarnetCombo", "DWGCombo"]:
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
        # Snapshot des sélections pour pouvoir revenir en arrière si besoin
        try:
            self._prev_selection = _get_selected_values(self)
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
            # Persister la valeur du sender après ajustement
            name = getattr(sender, 'Name', None) or 'Unknown'
            val = getattr(sender, 'SelectedItem', None)
            if val is not None:
                _config_set('sheet_param_{}'.format(name), str(val))
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


# ------------------------------- Paramètres & jeux de feuilles (délégués aux modules) ------------------------------- #

from .config import UserConfigStore
from .sheets import collect_sheet_parameter_names, get_sheet_sets

# Store de config (namespace par défaut)
CONFIG = UserConfigStore('batch_export')


def _get_sheet_sets(doc):
    return get_sheet_sets(doc)


def _populate_sheet_sets(win):
    """Remplit le ListView SheetSetsList avec les jeux de feuilles."""
    try:
        lv = getattr(win, 'SheetSetsList', None)
        if lv is None:
            return
        # Récupération doc
        try:
            doc = __revit__.ActiveUIDocument.Document  # type: ignore
        except Exception:
            # Placeholder si pas de doc
            lv.Items.Clear()
            lv.Items.Add({'Titre': 'Document introuvable', 'Feuilles': 0})
            return
        data = _get_sheet_sets(doc)
        try:
            lv.Items.Clear()
        except Exception:
            pass
        if not data:
            lv.Items.Add({'Titre': 'Aucun jeu trouvé', 'Feuilles': 0})
            return
        for row in data:
            try:
                lv.Items.Add(row)
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
        if btn is None:
            return
        avail = getattr(win, '_available_param_names', None)
        count = len(avail) if isinstance(avail, list) else 0
        if count < 3:
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


def _apply_saved_selection(win):
    """Charge la sélection mémorisée pour chaque combo si l'item existe."""
    for cname in ["ExportationCombo", "CarnetCombo", "DWGCombo"]:
        ctrl = getattr(win, cname, None)
        if ctrl is None:
            continue
        try:
            saved = CONFIG.get('sheet_param_{}'.format(cname))
            if not saved:
                continue
            idx = -1
            try:
                for i in range(ctrl.Items.Count):
                    if str(ctrl.Items[i]) == str(saved):
                        idx = i
                        break
            except Exception:
                pass
            if idx >= 0:
                try:
                    ctrl.SelectedIndex = idx
                except Exception:
                    pass
        except Exception:
            pass


# (filtrage des noms de paramètres déplacé dans lib.sheets.filter_param_names)


def _config_set(key, value):
    CONFIG.set(key, value)