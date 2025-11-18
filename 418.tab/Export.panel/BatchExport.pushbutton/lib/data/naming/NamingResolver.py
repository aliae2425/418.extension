# -*- coding: utf-8 -*-
# Résolution de nommage pour éléments Revit à partir de rows

from __future__ import unicode_literals

class NamingResolver(object):
    def __init__(self):
        pass

    def _get_param_value(self, elem, param_name):
        """Retourne une représentation chaîne du paramètre nommé sur l'élément, si trouvé."""
        try:
            params = getattr(elem, 'Parameters', None)
            if params is None:
                return ''
            for p in params:
                try:
                    d = getattr(p, 'Definition', None)
                    if d is not None and getattr(d, 'Name', None) == param_name:
                        try:
                            s = p.AsString()
                            if s:
                                return s
                        except Exception:
                            pass
                        try:
                            vs = p.AsValueString()
                            if vs:
                                return vs
                        except Exception:
                            pass
                        try:
                            ival = p.AsInteger()
                            if ival in (0, 1):
                                return '1' if ival == 1 else '0'
                        except Exception:
                            pass
                        try:
                            return str(p)
                        except Exception:
                            return ''
                except Exception:
                    continue
        except Exception:
            pass
        return ''

    # Construit une chaîne résolue pour un élément
    def resolve_for_element(self, elem, rows, empty_fallback=True):
        parts = []
        for r in rows or []:
            token = (r.get('Name', '') or '').strip()
            if not token:
                continue
            pf = r.get('Prefix', '') or ''
            sf = r.get('Suffix', '') or ''
            val = self._get_param_value(elem, token)
            if not val and empty_fallback:
                val = token
            parts.append(u"{}{}{}".format(pf, val, sf))
        return u''.join(parts)

    # Construit un pattern à partir des rows
    def build_pattern(self, rows):
        parts = []
        for r in rows or []:
            name = r.get('Name', '').strip()
            if not name:
                continue
            pf = r.get('Prefix', '') or ''
            sf = r.get('Suffix', '') or ''
            parts.append(pf + '{' + name + '}' + sf)
        return ''.join(parts)
