# -*- coding: utf-8 -*-
"""Gestion de la persistance des patterns de nommage.

Ce module isole la logique de sauvegarde/chargement des patterns
utilisés pour nommer feuilles et carnets.

Structure persistée:
- pattern string : pattern_sheet / pattern_set
- rows JSON (liste de dict) : pattern_sheet_rows / pattern_set_rows

Les rows conservent {Name, Prefix, Suffix} pour reconstruction future.
"""

import json
from .config import UserConfigStore

CONFIG = UserConfigStore('batch_export')

# Keys
_PATTERN_KEY = {
    'sheet': 'pattern_sheet',
    'set': 'pattern_set'
}
_ROWS_KEY = {
    'sheet': 'pattern_sheet_rows',
    'set': 'pattern_set_rows'
}


def save_pattern(kind, pattern, rows):
    """Persist pattern + rows.

    kind: 'sheet' | 'set'
    pattern: string pattern
    rows: iterable of dict {Name, Prefix, Suffix}
    """
    kpat = _PATTERN_KEY.get(kind)
    krows = _ROWS_KEY.get(kind)
    if not kpat or not krows:
        return False
    try:
        CONFIG.set(kpat, pattern or '')
    except Exception:
        pass
    try:
        # Sérialiser rows en JSON
        safe_rows = []
        for r in rows or []:
            if not isinstance(r, dict):
                continue
            safe_rows.append({
                'Name': r.get('Name',''),
                'Prefix': r.get('Prefix',''),
                'Suffix': r.get('Suffix','')
            })
        CONFIG.set(krows, json.dumps(safe_rows))
    except Exception:
        pass
    return True


def load_pattern(kind):
    """Retourne (pattern_string, rows_list). Si absent: ('', [])."""
    kpat = _PATTERN_KEY.get(kind)
    krows = _ROWS_KEY.get(kind)
    if not kpat or not krows:
        return '', []
    try:
        patt = CONFIG.get(kpat, '') or ''
    except Exception:
        patt = ''
    rows = []
    try:
        raw = CONFIG.get(krows, '')
        if raw:
            rows = json.loads(raw)
            if not isinstance(rows, list):
                rows = []
    except Exception:
        rows = []
    # Nettoyage minimal
    cleaned = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        name = r.get('Name','')
        cleaned.append({
            'Name': name,
            'Prefix': r.get('Prefix',''),
            'Suffix': r.get('Suffix','')
        })
    return patt, cleaned


def build_pattern_from_rows(rows):
    """Construit le pattern en concaténant Prefix + {Name} + Suffix pour chaque row."""
    parts = []
    for r in rows or []:
        name = r.get('Name','').strip()
        if not name:
            continue
        pf = r.get('Prefix','') or ''
        sf = r.get('Suffix','') or ''
        parts.append(pf + '{' + name + '}' + sf)
    return ''.join(parts)


def has_saved_pattern(kind):
    patt, rows = load_pattern(kind)
    return bool(patt) and bool(rows)


# ---------------------- Résolution des tokens pour un élément Revit ---------------------- #

def _get_param_value(elem, param_name):
    """Retourne une représentation chaîne du paramètre nommé sur l'élément, si trouvé.

    Essaye AsString puis AsValueString; pour Oui/Non, renvoie '1'/'0'. Retourne '' si absent.
    """
    try:
        params = getattr(elem, 'Parameters', None)
        if params is None:
            return ''
        for p in params:
            try:
                d = getattr(p, 'Definition', None)
                if d is not None and getattr(d, 'Name', None) == param_name:
                    # AsString si possible
                    try:
                        s = p.AsString()
                        if s:
                            return s
                    except Exception:
                        pass
                    # AsValueString sinon
                    try:
                        vs = p.AsValueString()
                        if vs:
                            return vs
                    except Exception:
                        pass
                    # Oui/Non -> entier
                    try:
                        ival = p.AsInteger()
                        if ival in (0, 1):
                            return '1' if ival == 1 else '0'
                    except Exception:
                        pass
                    # Dernier recours: ToString
                    try:
                        return str(p)
                    except Exception:
                        return ''
            except Exception:
                continue
    except Exception:
        pass
    return ''


def resolve_rows_for_element(elem, rows, empty_fallback=True):
    """Construit une chaîne à partir des rows en remplaçant {Token} par la valeur du paramètre sur l'élément.

    - empty_fallback: si True et que la valeur résolue est vide, écrit le nom du token à la place.
    Retourne une chaîne (sans accolades).
    """
    parts = []
    for r in rows or []:
        token = (r.get('Name', '') or '').strip()
        if not token:
            continue
        pf = r.get('Prefix', '') or ''
        sf = r.get('Suffix', '') or ''
        val = _get_param_value(elem, token)
        if not val and empty_fallback:
            val = token
        parts.append(u"{}{}{}".format(pf, val, sf))
    return u''.join(parts)

