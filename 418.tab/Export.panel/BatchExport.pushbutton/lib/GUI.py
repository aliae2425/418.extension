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
        # Assurer l'unicité initiale entre les trois combos
        try:
            _ensure_unique_across_combos(self)
        except Exception:
            pass
        # Abonnements
        for _cname in ["ExportationCombo", "CarnetCombo", "DWGCombo"]:
            try:
                ctrl = getattr(self, _cname)
                ctrl.SelectionChanged += self._on_param_combo_changed
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
            # Appliquer contrainte d'unicité
            _enforce_unique_for_sender(self, sender)
            # Mettre à jour l'instantané "avant"
            self._prev_selection = _get_selected_values(self)
            # Persister la valeur du sender après ajustement
            name = getattr(sender, 'Name', None) or 'Unknown'
            val = getattr(sender, 'SelectedItem', None)
            if val is not None:
                _config_set('sheet_param_{}'.format(name), str(val))
        except Exception:
            pass
        finally:
            self._updating = False


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


# ------------------------------- Paramètres ViewSheet ------------------------------- #

def _collect_sheet_parameter_names(doc):
    """Retourne la liste triée des noms de paramètres modifiables des feuilles.

    On agrège sur toutes les feuilles pour couvrir les partagés/non renseignés.
    """
    names = set()
    any_writable = {}
    try:
        sheets = DB.FilteredElementCollector(doc).OfClass(DB.SheetCollection)
    except Exception:
        return []
    for sheet in sheets:
        try:
            # Parcours des paramètres
            for p in sheet.Parameters:
                try:
                    d = p.Definition
                    if d is None:
                        continue
                    name = d.Name
                    if name and name.strip():
                        n = name.strip()
                        names.add(n)
                        try:
                            if hasattr(p, 'IsReadOnly') and not p.IsReadOnly:
                                any_writable[n] = True
                            else:
                                any_writable.setdefault(n, False)
                        except Exception:
                            any_writable.setdefault(n, True)
                except Exception:
                    continue
        except Exception:
            continue
    # Filtrer: garder seulement ceux qui sont modifiables (si connu) puis appliquer filtres noms
    filtered = [n for n in names if any_writable.get(n, True)]
    filtered = _apply_name_filters(filtered)
    return sorted(filtered, key=lambda s: s.lower())


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

    param_names = _collect_sheet_parameter_names(doc)
    if not param_names:
        _fill_combos_with_placeholder(win, "(Aucun paramètre de feuille)")
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


# ------------------------------- Unicité des ComboBox ------------------------------- #

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


def _ensure_unique_across_combos(win):
    """Force une sélection unique pour chaque combo si possible."""
    names_order = ["ExportationCombo", "CarnetCombo", "DWGCombo"]
    used = set()
    for cname in names_order:
        ctrl = getattr(win, cname, None)
        if ctrl is None:
            continue
        try:
            current = getattr(ctrl, 'SelectedItem', None)
            sval = None if current is None else str(current)
            if sval and sval not in used:
                used.add(sval)
                continue
            # Choisir la première option disponible non utilisée
            choice = None
            try:
                for i in range(ctrl.Items.Count):
                    cand = str(ctrl.Items[i])
                    if cand not in used:
                        choice = cand
                        break
            except Exception:
                pass
            if choice is not None:
                try:
                    ctrl.SelectedItem = choice
                    used.add(choice)
                except Exception:
                    pass
            else:
                # Aucune option unique dispo: effacer la sélection
                try:
                    ctrl.SelectedIndex = -1
                except Exception:
                    pass
        except Exception:
            continue


def _enforce_unique_for_sender(win, sender):
    """Si le sender duplique un autre combo, sélectionner une valeur unique.

    Si aucune valeur unique n'est dispo, on restaure l'ancienne valeur si possible
    sinon on efface la sélection du sender.
    """
    try:
        sname = getattr(sender, 'Name', None) or ''
        sval_obj = getattr(sender, 'SelectedItem', None)
        sval = None if sval_obj is None else str(sval_obj)
    except Exception:
        return

    # Récupérer les autres valeurs sélectionnées
    selected = _get_selected_values(win)
    others = {k: v for k, v in selected.items() if k != sname and v is not None}

    if sval is None or sval not in others.values():
        # Déjà unique ou rien sélectionné
        return

    # Conflit détecté -> chercher une alternative disponible
    used = set([v for v in others.values() if v is not None])
    alt = None
    try:
        for i in range(sender.Items.Count):
            cand = str(sender.Items[i])
            if cand not in used:
                alt = cand
                break
    except Exception:
        pass

    if alt is not None:
        try:
            sender.SelectedItem = alt
            return
        except Exception:
            pass

    # Pas d'alternative -> tenter de revenir à l'ancienne valeur si dispo
    try:
        prev = getattr(win, '_prev_selection', {}).get(sname)
        if prev is not None and prev not in used:
            sender.SelectedItem = prev
            return
    except Exception:
        pass

    # Dernier recours: vider la sélection
    try:
        sender.SelectedIndex = -1
    except Exception:
        pass


def _apply_saved_selection(win):
    """Charge la sélection mémorisée pour chaque combo si l'item existe."""
    for cname in ["ExportationCombo", "CarnetCombo", "DWGCombo"]:
        ctrl = getattr(win, cname, None)
        if ctrl is None:
            continue
        try:
            saved = _config_get('sheet_param_{}'.format(cname))
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


def _apply_name_filters(names):
    """Applique des filtres simples et liste d'exclusion config.

    - supprime noms vides
    - supprime noms commençant par '_' (convention technique)
    - exclut noms présents dans la config (liste noire)
    """
    try:
        exclude_cfg = _config_get('excluded_sheet_params', default=[])
        if isinstance(exclude_cfg, str):
            exclude_cfg = [s.strip() for s in exclude_cfg.split(',') if s.strip()]
    except Exception:
        exclude_cfg = []
    exclude_set = set([s.lower() for s in exclude_cfg])
    out = []
    for n in names:
        if not n:
            continue
        if n.startswith('_'):
            continue
        if n.lower() in exclude_set:
            continue
        out.append(n)
    return out


# ------------------------------- Config adapter ------------------------------- #

def _config_get(key, default=None):
    """Lit une valeur depuis user_Config si disponible.

    Tente plusieurs signatures pour compatibilité. Espace de noms: 'batch_export'.
    """
    try:
        import user_Config as UC  # type: ignore
        ns = 'batch_export'
        if hasattr(UC, 'get'):
            return UC.get(ns, key, default)
        if hasattr(UC, 'get_config'):
            return UC.get_config(ns, key, default)
        if hasattr(UC, 'read'):
            return UC.read(ns, key, default)
        if hasattr(UC, 'get_value'):
            return UC.get_value(key, default)
    except Exception:
        pass
    return default


def _config_set(key, value):
    """Écrit une valeur vers user_Config si disponible; no-op sinon."""
    try:
        import user_Config as UC  # type: ignore
        ns = 'batch_export'
        if hasattr(UC, 'set'):
            UC.set(ns, key, value)
            return True
        if hasattr(UC, 'set_config'):
            UC.set_config(ns, key, value)
            return True
        if hasattr(UC, 'write'):
            UC.write(ns, key, value)
            return True
        if hasattr(UC, 'set_value'):
            UC.set_value(key, value)
            return True
    except Exception:
        pass
    return False