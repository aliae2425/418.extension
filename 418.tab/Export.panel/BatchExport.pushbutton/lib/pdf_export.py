# -*- coding: utf-8 -*-
"""Gestion des paramètres d'export PDF / impressions.

Fonctions:
    list_pdf_setups(doc) -> [str]
    get_saved_pdf_setup() / set_saved_pdf_setup(name)
    get_saved_pdf_separate() / set_saved_pdf_separate(bool)
    build_pdf_export_options(doc, setup_name=None) -> options (placeholder)

Clés de config:
    pdf_setup_name
    pdf_separate_views ("1"/"0")

Approche:
    - Les "PrintSetting" (ou PDFExportSettings si disponibles) sont collectés et leurs noms exposés.
    - Pour Revit >= 2022, PDFExportSettings existe (sinon fallback PrintSetting).
"""

try:
    from Autodesk.Revit import DB  # type: ignore
except Exception:
    DB = None  # type: ignore

from .config import UserConfigStore
import json

CONFIG = UserConfigStore('batch_export')

_SETUP_KEY = 'pdf_setup_name'
_SEPARATE_KEY = 'pdf_separate_views'


def list_pdf_setups(doc):
    if DB is None or doc is None:
        return []
    names = []
    # PDFExportSettings (nouveau) prioritaire
    try:
        if hasattr(DB, 'PDFExportSettings'):
            col = DB.FilteredElementCollector(doc).OfClass(DB.PDFExportSettings).ToElements()
            for s in col:
                try:
                    nm = s.Name
                    if nm and nm not in names:
                        names.append(nm)
                except Exception:
                    continue
    except Exception:
        pass
    # Fallback PrintSetting
    try:
        col = DB.FilteredElementCollector(doc).OfClass(DB.PrintSetting).ToElements()
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
        raw = CONFIG.get('custom_pdf_setups', '')
        if not raw:
            return []
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def list_custom_pdf_setups():
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


def get_custom_pdf_setup_data(name):
    for it in _load_custom_list():
        try:
            if it.get('name') == name:
                d = it.get('data')
                return d if isinstance(d, dict) else None
        except Exception:
            continue
    return None


def list_all_pdf_setups(doc):
    """Fusionne setups Revit et personnalisés, sans doublons (customs priment)."""
    revit = list_pdf_setups(doc)
    custom = list_custom_pdf_setups()
    s = {n: 'revit' for n in revit}
    for n in custom:
        s[n] = 'custom'
    return sorted(s.keys(), key=lambda x: x.lower())


def get_saved_pdf_setup(default=None):
    try:
        val = CONFIG.get(_SETUP_KEY, '')
        return val or default
    except Exception:
        return default


def set_saved_pdf_setup(name):
    if not name:
        return False
    try:
        return CONFIG.set(_SETUP_KEY, name)
    except Exception:
        return False


def get_saved_pdf_separate(default=False):
    try:
        raw = CONFIG.get(_SEPARATE_KEY, '')
        return True if raw == '1' else False if raw == '0' else default
    except Exception:
        return default


def set_saved_pdf_separate(flag):
    try:
        return CONFIG.set(_SEPARATE_KEY, '1' if flag else '0')
    except Exception:
        return False


def build_pdf_export_options(doc, setup_name=None):
    """Placeholder pour options PDF.

    Revit API fournit PDFExportOptions (>=2022). Ici on retourne l'instance si possible;
    copie des paramètres d'un setup nommé non implémentée (TODO futur).
    """
    if DB is None or doc is None:
        return None
    options = None
    try:
        if hasattr(DB, 'PDFExportOptions'):
            options = DB.PDFExportOptions()
    except Exception:
        options = None
    return options


__all__ = [
    'list_pdf_setups',
    'list_custom_pdf_setups',
    'list_all_pdf_setups',
    'get_custom_pdf_setup_data',
    'get_saved_pdf_setup',
    'set_saved_pdf_setup',
    'get_saved_pdf_separate',
    'set_saved_pdf_separate',
    'build_pdf_export_options',
]
