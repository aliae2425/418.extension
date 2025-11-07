# -*- coding: utf-8 -*-

# ------------------------------- info pyrevit ------------------------------- #
__title__ = "Exportation"
__doc__ = """
    Version 0.1 - Version nettoyée
    Auteur : Aliae
    _____________________________________________

    Export les feuilles par jeu de feuilles en fonction des parametre du jeu 

    Export : inclus les feuilles du jeux a l'export 
    Export par feuilles : exporte les feuilles une par une, par defaut export en carnet compilé avec le nom du jeu
    Export en DWG : Export en DWG en plus du PDF
    _____________________________________________
"""
__author__ = 'Aliae'                               
__min_revit_ver__ = 2026                                       

# ------------------------------- Imports ------------------------------- #
from pyrevit import script, forms
from pyrevit import DB, revit
from pyrevit.forms import alert
import config

# ------------------------------- Variables globales ------------------------------- #
activ_document = __revit__.ActiveUIDocument.Document
app = __revit__.Application

REQUIRED_KEYS = ["Exportation", "Carnet", "DWG"]

# ------------------------------- Fonctions ------------------------------- #

def _param_value_to_str(param):
    if not param:
        return "Non défini"
    if not param.HasValue:
        return "Non défini"
    # Oui/Non
    try:
        val = param.AsInteger()
        if val in (0, 1):
            return "Oui" if val == 1 else "Non"
    except Exception:
        pass
    # Chaîne
    try:
        s = param.AsString()
        if s is not None:
            return s
    except Exception:
        pass
    # Nombre
    try:
        d = param.AsDouble()
        if d is not None:
            return str(d)
    except Exception:
        pass
    return "(valeur non lisible)"

def display_sheet_sets_info(sheet_sets, mapping):
    """Affiche les informations des jeux de feuilles et leurs paramètres (noms exacts du mapping)."""
    print("\n=== {} jeu(x) de feuilles trouvé(s) ===".format(len(sheet_sets)))
    for sheet_set in sheet_sets:
        print("\nJeu de feuilles: {}".format(sheet_set.Name))
        for key in REQUIRED_KEYS:
            pname = mapping.get(key)
            param = None
            try:
                if pname:
                    param = sheet_set.LookupParameter(pname)
            except Exception:
                param = None
            print("    {}: {}".format(key, _param_value_to_str(param)))

# ------------------------------- Script principal ------------------------------- #

if __name__ == "__main__":
    print("=== Hello Batch Export ===")
    
    # Vérifie que les paramètres sont configurés; si non, ouvre le formulaire via config
    mapping = config.ensure_complete_mapping()
    # Log interne pour debug persistance
    print("[debug] Mapping chargé: {}".format(mapping))
    if not mapping or any(not mapping.get(k) for k in REQUIRED_KEYS):
        alert("Paramètres non configurés ou incomplets. Re-lancez et choisissez les paramètres.", title="Batch Export")
        script.exit()
    
    # Récupérer tous les jeux de feuilles du document
    collector = DB.FilteredElementCollector(activ_document)
    sheet_sets = collector.OfClass(DB.SheetCollection).ToElements()

    if not sheet_sets:
        alert("Aucun jeu de feuilles trouvé dans le document.", title="Batch Export")
        script.exit()
    
    # Vérifier les paramètres sur le premier jeu de feuilles
    if sheet_sets and sheet_sets[0].IsValidObject:
        print("Paramètres configurés: {}".format(", ".join(["{}=\"{}\"".format(k, mapping.get(k)) for k in REQUIRED_KEYS])))
        display_sheet_sets_info(sheet_sets, mapping)
    
    print("\n=== Fin du script ===")