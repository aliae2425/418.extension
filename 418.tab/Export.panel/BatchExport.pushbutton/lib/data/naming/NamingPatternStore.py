# -*- coding: utf-8 -*-
# Persistance des patterns de nommage (pattern + rows)

from __future__ import unicode_literals

import json


class NamingPatternStore(object):
    """Gère la sauvegarde/lecture des patterns et de leurs rows (JSON).

    Clés utilisées:
      - 'pattern_sheet' / 'pattern_set'
      - 'pattern_sheet_rows' / 'pattern_set_rows'
    """

    def __init__(self, namespace='batch_export'):
        try:
            from ...core.UserConfig import UserConfig
        except Exception:
            UserConfig = None  # type: ignore
        self._cfg = UserConfig(namespace) if UserConfig is not None else None
        self._PATTERN_KEY = {'sheet': 'pattern_sheet', 'set': 'pattern_set'}
        self._ROWS_KEY = {'sheet': 'pattern_sheet_rows', 'set': 'pattern_set_rows'}


    def save(self, kind, pattern, rows):
        """Persist pattern + rows (sous forme de chaîne custom)."""
        if self._cfg is None:
            return False
        kpat = self._PATTERN_KEY.get(kind)
        krows = self._ROWS_KEY.get(kind)
        if not kpat or not krows:
            return False
        try:
            self._cfg.set(kpat, pattern or '')
        except Exception as e:
            print("NamingPatternStore [001]: Error saving pattern '{}': {}".format(kpat, e))
        try:
            # Construction de la chaîne custom
            row_strs = []
            for r in rows or []:
                name = r.get('Name', '')
                prefix = r.get('Prefix', '')
                suffix = r.get('Suffix', '')
                row_strs.append(u'[ "name": "{}", "prefixe": "{}", "suffixe": "{}" ]'.format(name, prefix, suffix))
            final_rows_str = u'[' + u', '.join(row_strs) + u']'
            # print("rows_string:", final_rows_str)
            self._cfg.set(krows, final_rows_str)
        except Exception as e:
            print("NamingPatternStore [002]: Error saving rows '{}': {}".format(krows, e))
        return True

    def load(self, kind):
        """Retourne (pattern_string, rows_list)."""
        if self._cfg is None:
            return ('', [])
        kpat = self._PATTERN_KEY.get(kind)
        krows = self._ROWS_KEY.get(kind)
        if not kpat or not krows:
            return ('', [])
        try:
            patt = self._cfg.get(kpat, '') or ''
        except Exception:
            patt = ''
        rows = []
        try:
            raw = self._cfg.get(krows, '')
            print("namminingpatternstore load rows raw:", raw)
            if raw:
                rows = json.loads(raw)
                if not isinstance(rows, list):
                    rows = []
        except Exception:
            rows = []
        cleaned = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            cleaned.append({
                'Name': r.get('Name', ''),
                'Prefix': r.get('Prefix', ''),
                'Suffix': r.get('Suffix', ''),
            })
        return (patt, cleaned)

    def has_saved(self, kind):
        patt, rows = self.load(kind)
        return bool(patt) and bool(rows)
