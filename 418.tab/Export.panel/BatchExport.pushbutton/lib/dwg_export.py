# -*- coding: utf-8 -*-
"""Gestion des paramètres d'export DWG.

Fonctions fournies:
    list_dwg_setups(doc) -> [str]
    get_saved_dwg_setup() / set_saved_dwg_setup(name)
    get_saved_dwg_separate() / set_saved_dwg_separate(bool)
    build_dwg_export_options(doc) -> options (placeholder)

Notes:
    - Utilise la config utilisateur (UserConfigStore) avec clés:
        dwg_setup_name, dwg_separate_views ("1"/"0")
    - Revit >= versions modernes expose ExportDWGSettings; on récupère leurs noms.
    - Fallback: renvoie liste vide si API indisponible.
"""

try:
    from Autodesk.Revit import DB  # type: ignore
except Exception:
    DB = None  # type: ignore

from .config import UserConfigStore
import json

CONFIG = UserConfigStore('batch_export')

_SETUP_KEY = 'dwg_setup_name'
_SEPARATE_KEY = 'dwg_separate_views'


def list_dwg_setups(doc):
    """Retourne la liste des noms de réglages d'export DWG disponibles."""
    if DB is None or doc is None:
        return []
    names = []
    try:
        col = DB.FilteredElementCollector(doc).OfClass(DB.ExportDWGSettings).ToElements()
        for s in col:
            try:
                nm = s.Name
                if nm and nm not in names:
                    names.append(nm)
            except Exception:
                continue
    except Exception:
        pass
    return sorted(names, key=lambda x: x.lower())


def _load_custom_list():
    try:
        raw = CONFIG.get('custom_dwg_setups', '')
        if not raw:
            return []
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def list_custom_dwg_setups():
    lst = _load_custom_list()
    out = []
    for it in lst:
        try:
            nm = it.get('name')
            if nm and nm not in out:
                out.append(nm)
        except Exception:
            continue
    return sorted(out, key=lambda x: x.lower())


def get_custom_dwg_setup_data(name):
    for it in _load_custom_list():
        try:
            if it.get('name') == name:
                d = it.get('data')
                return d if isinstance(d, dict) else None
        except Exception:
            continue
    return None


def list_all_dwg_setups(doc):
    revit = list_dwg_setups(doc)
    custom = list_custom_dwg_setups()
    s = {n: 'revit' for n in revit}
    for n in custom:
        s[n] = 'custom'
    return sorted(s.keys(), key=lambda x: x.lower())


def get_saved_dwg_setup(default=None):
    try:
        val = CONFIG.get(_SETUP_KEY, '')
        return val or default
    except Exception:
        return default


def set_saved_dwg_setup(name):
    if not name:
        return False
    try:
        return CONFIG.set(_SETUP_KEY, name)
    except Exception:
        return False


def get_saved_dwg_separate(default=False):
    try:
        raw = CONFIG.get(_SEPARATE_KEY, '')
        return True if raw == '1' else False if raw == '0' else default
    except Exception:
        return default


def set_saved_dwg_separate(flag):
    try:
        return CONFIG.set(_SEPARATE_KEY, '1' if flag else '0')
    except Exception:
        return False


def build_dwg_export_options(doc, setup_name=None):
    """Construit (placeholder) les options DWG basées sur un setup nommé.

    Revit propose DB.DWGExportOptions; on peut copier depuis ExportDWGSettings.GetDWGExportOptions()
    si disponible. Ici on retourne simplement l'instance pour usage futur.
    """
    if DB is None or doc is None:
        return None
    try:
        options = DB.DWGExportOptions()
    except Exception:
        return None
    if setup_name:
        try:
            col = DB.FilteredElementCollector(doc).OfClass(DB.ExportDWGSettings).ToElements()
            for s in col:
                if s.Name == setup_name:
                    try:
                        opt = s.GetDWGExportOptions()
                        if opt is not None:
                            options = opt
                    except Exception:
                        pass
                    break
        except Exception:
            pass
    return options


__all__ = [
    'list_dwg_setups',
    'list_custom_dwg_setups',
    'list_all_dwg_setups',
    'get_custom_dwg_setup_data',
    'get_saved_dwg_setup',
    'set_saved_dwg_setup',
    'get_saved_dwg_separate',
    'set_saved_dwg_separate',
    'build_dwg_export_options',
]
