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
import unicodedata
import re

# ------------------------------- Variables globales ------------------------------- #
activ_document = __revit__.ActiveUIDocument.Document
app = __revit__.Application

# Dictionnaire d'alias: clé canonique -> variantes acceptées
CUSTOM_PARAM_ALIASES = {
    "Exportation": [
        "Exportation", "Export", "Exporter",
        "Export PDF", "Export en PDF", "PDF Export"
    ],
    "Carnet": [
        "Carnet", "Carnets", "Regroupement", "Regrouper","Regroupé"
    ],
    "DWG": [
        "DWG", "Export DWG", "DWGs", "D.W.G.", "Export en DWG"
    ],
}

# ------------------------------- Fonctions ------------------------------- #

def _normalize(text):
    """Normalise une chaîne pour comparaison tolérante (sans accents, insensible à la casse, sans ponctuation)."""
    if text is None:
        return ""
    # Enlever accents
    text = unicodedata.normalize('NFD', text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != 'Mn')
    # Minuscule + enlever tout ce qui n'est pas alphanumérique
    text = text.strip().lower()
    return "".join(ch for ch in text if ch.isalnum())

def get_param_by_alias(element, canonical_key):
    """Retourne (param, alias_trouvé) si un paramètre correspondant aux alias de canonical_key est trouvé sur l'élément."""
    aliases = CUSTOM_PARAM_ALIASES.get(canonical_key, [canonical_key])

    # 1) Tentative directe via LookupParameter pour chaque alias (rapide)
    for name in aliases:
        try:
            p = element.LookupParameter(name)
            if p:
                return p, name
        except Exception:
            pass

    # 2) Fallback: balayage de tous les paramètres et comparaison normalisée
    alias_norm_map = {_normalize(a): a for a in aliases}
    try:
        for p in element.Parameters:
            try:
                defn = p.Definition
                pname = getattr(defn, 'Name', None)
                if pname and _normalize(pname) in alias_norm_map:
                    return p, alias_norm_map[_normalize(pname)]
            except Exception:
                continue
    except Exception:
        pass

    return None, None

def check_parameters_exist(sheet_set):
    """Vérifie si tous les paramètres requis existent (avec alias) sur un jeu de feuilles."""
    missing_params = []
    for canonical in CUSTOM_PARAM_ALIASES.keys():
        p, _found = get_param_by_alias(sheet_set, canonical)
        if not p:
            missing_params.append(canonical)
    return missing_params

def display_sheet_sets_info(sheet_sets):
    """Affiche les informations des jeux de feuilles et leurs paramètres (avec alias)."""
    print("\n=== {} jeu(x) de feuilles trouvé(s) ===".format(len(sheet_sets)))
    
    for sheet_set in sheet_sets:
        print("\nJeu de feuilles: {}".format(sheet_set.Name))
        
        for canonical in CUSTOM_PARAM_ALIASES.keys():
            param, found_name = get_param_by_alias(sheet_set, canonical)
            if param and param.HasValue:
                # Gestion Oui/Non (int 0/1). On affiche aussi l'alias réellement trouvé.
                try:
                    value = param.AsInteger()
                    display_value = "Oui" if value == 1 else "Non"
                except Exception:
                    # Fallback: tenter AsString/AsDouble
                    v = None
                    try:
                        v = param.AsString()
                    except Exception:
                        try:
                            v = param.AsDouble()
                        except Exception:
                            v = "(valeur non lisible)"
                    display_value = v
                alias_note = " (alias: {} )".format(found_name) if found_name and found_name != canonical else ""
                print("    {}: {}{}".format(canonical, display_value, alias_note))
            else:
                print("    {}: Non défini".format(canonical))

# ------------------------------- Script principal ------------------------------- #

if __name__ == "__main__":
    print("=== Hello Batch Export ===")
    
    # Récupérer tous les jeux de feuilles du document
    collector = DB.FilteredElementCollector(activ_document)
    sheet_sets = collector.OfClass(DB.SheetCollection).ToElements()

    if not sheet_sets:
        alert("Aucun jeu de feuilles trouvé dans le document.", title="Batch Export")
        script.exit()
    
    # Vérifier les paramètres sur le premier jeu de feuilles
    if sheet_sets and sheet_sets[0].IsValidObject:
        missing_params = check_parameters_exist(sheet_sets[0])
        
        if missing_params:
            message = "Paramètres manquants détectés:\n\n"
            for param in missing_params:
                message += "- {}\n".format(param)
            message += "\nCes paramètres doivent être créés manuellement dans Revit.\n"
            message += "Allez dans Gérer > Paramètres de projet pour les créer."
            
            alert(message, title="Paramètres manquants")
            print("Paramètres manquants: {}".format(", ".join(missing_params)))
        else:
            print("Tous les paramètres requis sont présents !")
            display_sheet_sets_info(sheet_sets)
    
    print("\n=== Fin du script ===")