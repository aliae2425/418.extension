# -*- coding: utf-8 -*-
from pyrevit.userconfig import user_config
from pyrevit import DB, forms
import os
import sys
import json

# Assurer la compatibilité UTF-8
if sys.version_info[0] >= 3:
    unicode = str

activ_document = __revit__.ActiveUIDocument.Document
app = __revit__.Application


if __name__ == "__main__":
    print("Config module loaded")

    # Test de création des paramètres
    # create_sheet_parameters()
    
# ======================= WPF: Fenêtre à 3 sections ======================= #

def _xaml_path(filename):
    return os.path.join(os.path.dirname(__file__), filename)


class ThreeSectionWindow(forms.WPFWindow):
    """
    Fenêtre WPF pyRevit avec 3 sections, conforme au pattern WPFWindow de la doc pyRevit.

    Sections prévues:
      - Exportation
      - Carnet
      - DWG

    Chaque section fournit une ComboBox pour sélectionner une valeur.
    """

    def __init__(self, xaml_path, options, preselects=None, title=None):
        # Charge le XAML
        forms.WPFWindow.__init__(self, xaml_path)
        self.Options = options or {
            'Exportation': [],
            'Carnet': [],
            'DWG': [],
        }
        self.Preselects = preselects or {}
        self.Result = None

        # Titre optionnel
        if title:
            try:
                self.Title = title
            except Exception:
                pass

        # Alimente les ComboBox avec les options disponibles
        try:
            self.ExportationCombo.ItemsSource = self.Options.get('Exportation', [])
            self.CarnetCombo.ItemsSource = self.Options.get('Carnet', [])
            self.DWGCombo.ItemsSource = self.Options.get('DWG', [])
        except Exception:
            pass

        # Pré-sélectionne si possible
        try:
            exp = self.Preselects.get('Exportation')
            car = self.Preselects.get('Carnet')
            dwg = self.Preselects.get('DWG')
            if exp in self.Options.get('Exportation', []):
                self.ExportationCombo.SelectedItem = exp
            if car in self.Options.get('Carnet', []):
                self.CarnetCombo.SelectedItem = car
            if dwg in self.Options.get('DWG', []):
                self.DWGCombo.SelectedItem = dwg
        except Exception:
            pass

    # Gestion des clics boutons
    def OkButton_Click(self, sender, args):
        mapping = {}
        try:
            if self.ExportationCombo.SelectedItem:
                mapping['Exportation'] = self.ExportationCombo.SelectedItem
            if self.CarnetCombo.SelectedItem:
                mapping['Carnet'] = self.CarnetCombo.SelectedItem
            if self.DWGCombo.SelectedItem:
                mapping['DWG'] = self.DWGCombo.SelectedItem
        except Exception:
            mapping = {}
        self.Result = mapping
        self.Close()

    def CancelButton_Click(self, sender, args):
        self.Result = None
        self.Close()


def get_all_project_parameter_names(doc=None):
    """Retourne la liste des noms de paramètres de projet définis (bindings)."""
    doc = doc or activ_document
    names = set()
    try:
        it = doc.ParameterBindings.ForwardIterator()
        while it.MoveNext():
            try:
                defn = it.Key
                nm = getattr(defn, 'Name', None)
                if nm:
                    names.add(nm)
            except Exception:
                continue
    except Exception:
        pass
    return sorted(names)


def open_three_section_window(preselects=None, title="Sélection des paramètres d'export"):
    """
    Ouvre la fenêtre WPF avec 3 sections en alimentant les listes avec
    les paramètres de projet disponibles.

    Retourne un dict {'Exportation': str, 'Carnet': str, 'DWG': str} ou None si annulé.
    """
    options_all = get_all_project_parameter_names()
    if not options_all:
        forms.alert("Aucun paramètre de projet trouvé.", title="Sélection")
        return None

    options = {
        'Exportation': options_all,
        'Carnet': options_all,
        'DWG': options_all,
    }
    xaml = _xaml_path('ParamSelector.xaml')
    win = ThreeSectionWindow(xaml, options=options, preselects=preselects or {}, title=title)
    try:
        # Essaye d'ouvrir en modal si possible
        win.ShowDialog()
    except Exception:
        # Fallback non-modal
        win.show()
    return win.Result

# ======================= Persistance du mapping ======================= #

_MAPPING_OPTION_KEY = 'batch_export_param_mapping'

def save_mapping(mapping):
    """Sauvegarde le mapping dict dans user_config (JSON)."""
    try:
        # Coercition en str Python natif (au cas où objets .NET se glissent)
        py_map = {}
        for k, v in (mapping or {}).items():
            if k is None or v is None:
                continue
            py_key = str(k)
            py_val = str(v)
            py_map[py_key] = py_val
        user_config.add_section("BatchExport_mapping")
        user_config.BatchExport_mapping.property = py_map
        user_config.save_changes()
        # Tente d'enregistrer explicitement si l'API le permet
    except Exception:
        print("[error] Impossible de sauvegarder le mapping dans user_config.")

def get_saved_mapping():
    """Récupère le mapping depuis user_config, retourne dict ou {}."""
    try:
        raw = user_config.get_option("BatchExport_mapping", raw)
        if not raw:
            return {}
        # Si c'est déjà un dict (selon version pyRevit), le renvoyer
        if isinstance(raw, dict):
            # normaliser en str
            return {str(k): str(v) for k, v in raw.items() if k and v}
        # Sinon parser JSON
        return json.loads(raw)
    except Exception:
        return {}

def configure_parameters():
    """Force l'ouverture de la fenêtre de configuration et sauvegarde le mapping choisi."""
    chosen = open_three_section_window(preselects=get_saved_mapping())
    if chosen:
        save_mapping(chosen)
    return chosen or {}

def ensure_mapping():  # Conservé pour compatibilité, ne fait que retourner le mapping existant
    return get_saved_mapping()

def _is_mapping_complete(mapping, available_names):
    required = {"Exportation", "Carnet", "DWG"}
    if not isinstance(mapping, dict):
        return False
    for k in required:
        v = mapping.get(k)
        if not v or v not in available_names:
            return False
    return True

def ensure_complete_mapping():
    """Vérifie le mapping et ouvre le formulaire si incomplet. Retourne un dict complet ou {} si l'utilisateur annule."""
    available = set(get_all_project_parameter_names())
    mapping = get_saved_mapping()
    if _is_mapping_complete(mapping, available):
        return mapping
    # Ouvrir la fenêtre avec pré-sélection
    chosen = open_three_section_window(preselects=mapping)
    if chosen:
        # Fusion simple: remplacer/ajouter clés choisies
        mapping = dict(mapping or {})
        mapping.update(chosen)
        # Sauvegarder même si incomplet pour conserver le choix utilisateur
        save_mapping(mapping)
        if _is_mapping_complete(mapping, available):
            return mapping
    # Non configuré ou incomplet
    return mapping if mapping else {}
    