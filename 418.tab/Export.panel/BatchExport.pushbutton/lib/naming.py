# -*- coding: utf-8 -*-
# FACADE: Toute la logique est migrée vers lib/data/naming.
# Ce module expose des wrappers pour compatibilité existante.

from __future__ import unicode_literals

def _store():
    try:
        from .data.naming.NamingPatternStore import NamingPatternStore
        return NamingPatternStore()
    except Exception:
        return None

def _resolver():
    try:
        from .data.naming.NamingResolver import NamingResolver
        return NamingResolver()
    except Exception:
        return None

def save_pattern(kind, pattern, rows):
    st = _store()
    return st.save(kind, pattern, rows) if st is not None else False

def load_pattern(kind):
    st = _store()
    return st.load(kind) if st is not None else ('', [])

def build_pattern_from_rows(rows):
    res = _resolver()
    return res.build_pattern(rows) if res is not None else ''

def has_saved_pattern(kind):
    st = _store()
    return st.has_saved(kind) if st is not None else False

def resolve_rows_for_element(elem, rows, empty_fallback=True):
    res = _resolver()
    return res.resolve_for_element(elem, rows, empty_fallback=empty_fallback) if res is not None else ''

