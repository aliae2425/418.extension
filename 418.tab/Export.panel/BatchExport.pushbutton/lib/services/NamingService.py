# -*- coding: utf-8 -*-
# Service de nommage : résolution de patterns contre un élément Revit + persistance.
#
# Consolide la logique historiquement répartie entre :
#   - lib/data/naming/NamingResolver.py   (résolution valeur/pattern)
#   - lib/data/naming/NamingPatternStore.py (persistance pattern + rows)
#
# Objectif : un service unique, testable hors Revit, sans dépendance UI.

from __future__ import unicode_literals

import json
import re

try:
    from Autodesk.Revit import DB  # type: ignore
except Exception:
    DB = None  # type: ignore

try:
    from core.UserConfig import UserConfig  # type: ignore
except Exception:
    UserConfig = None  # type: ignore


class NamingService(object):
    """Résout des patterns de nommage et persiste les patterns utilisateur.

    Un pattern de nommage est une liste de dicts :
        [{"Name": "Numero_Feuille", "Prefix": "", "Suffix": "-"}, ...]

    Noms système réservés (résolus sans accès à l'élément) :
        'Date: Jour', 'Date: Mois', 'Date: Année'
    """

    _PATTERN_KEY = {'sheet': 'pattern_sheet', 'set': 'pattern_set'}
    _ROWS_KEY = {'sheet': 'pattern_sheet_rows', 'set': 'pattern_set_rows'}

    def __init__(self, doc=None, config=None, namespace='batch_export'):
        self._doc = doc
        self._project_params_cache = None
        if config is not None:
            self._cfg = config
        elif UserConfig is not None:
            self._cfg = UserConfig(namespace)
        else:
            self._cfg = None

    # ------------------------------------------------------------------
    # Résolution
    # ------------------------------------------------------------------

    def resolve_for_element(self, elem, rows):
        """Construit la chaîne résolue pour `elem` à partir de `rows`.

        Chaque row {"Name", "Prefix", "Suffix"} devient Prefix + valeur + Suffix.
        Les rows sans "Name" sont ignorées. Une valeur introuvable/invalide
        devient une chaîne vide (pas de fallback vers le nom du paramètre).
        """
        parts = []
        for row in rows or []:
            name = (row.get('Name', '') or '').strip()
            if not name:
                continue
            prefix = row.get('Prefix', '') or ''
            suffix = row.get('Suffix', '') or ''
            value = self._sanitize_resolved_value(self._get_param_value(elem, name))
            parts.append(u"{}{}{}".format(prefix, value, suffix))
        return u''.join(parts)

    def build_pattern(self, rows):
        """Construit un template lisible : Prefix + {Name} + Suffix concaténés."""
        parts = []
        for row in rows or []:
            name = (row.get('Name', '') or '').strip()
            if not name:
                continue
            prefix = row.get('Prefix', '') or ''
            suffix = row.get('Suffix', '') or ''
            parts.append(prefix + '{' + name + '}' + suffix)
        return ''.join(parts)

    # ------------------------------------------------------------------
    # Persistance (via UserConfig, namespace 'batch_export')
    # ------------------------------------------------------------------

    def save(self, kind, pattern, rows):
        """Persiste pattern + rows (JSON) pour kind ('sheet' ou 'set')."""
        if self._cfg is None:
            return False
        kpat = self._PATTERN_KEY.get(kind)
        krows = self._ROWS_KEY.get(kind)
        if not kpat or not krows:
            return False
        try:
            self._cfg.set(kpat, pattern or '')
        except Exception:
            pass
        try:
            self._cfg.set(krows, json.dumps(rows or []))
        except Exception:
            pass
        return True

    def load(self, kind):
        """Retourne (pattern_string, rows_list) pour kind ('sheet' ou 'set')."""
        if self._cfg is None:
            return ('', [])
        kpat = self._PATTERN_KEY.get(kind)
        krows = self._ROWS_KEY.get(kind)
        if not kpat or not krows:
            return ('', [])
        try:
            pattern = self._cfg.get(kpat, '') or ''
        except Exception:
            pattern = ''
        rows = []
        try:
            raw = self._cfg.get(krows, '')
            if raw:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    rows = parsed
        except Exception:
            rows = []
        return (pattern, rows)

    def has_saved(self, kind):
        pattern, rows = self.load(kind)
        return bool(pattern) and bool(rows)

    # ------------------------------------------------------------------
    # Extraction de valeur paramètre (robuste, ordre de repli)
    # ------------------------------------------------------------------

    def _get_param_value(self, elem, param_name):
        """Retourne la valeur du paramètre nommé pour `elem`, via repli successif."""
        # 0. Paramètres système (Date)
        sys_val = self._get_system_param_value(param_name)
        if sys_val is not None:
            return sys_val

        # 1. LookupParameter (le plus fiable/rapide)
        try:
            p = elem.LookupParameter(param_name)
            if p:
                val = self._extract_param_value(p)
                if val:
                    return val
        except Exception:
            pass

        # 2. Itération manuelle sur .Parameters (fallback)
        try:
            params = getattr(elem, 'Parameters', None)
            if params:
                for p in params:
                    try:
                        d = getattr(p, 'Definition', None)
                        if d and getattr(d, 'Name', '') == param_name:
                            val = self._extract_param_value(p)
                            if val:
                                return val
                    except Exception:
                        continue
        except Exception:
            pass

        # 3. Propriété directe sur l'élément (ex: 'Name')
        try:
            if hasattr(elem, param_name):
                val = getattr(elem, param_name)
                if val and type(val).__name__ in ('str', 'unicode'):
                    return val
        except Exception:
            pass

        # 4. Repli : paramètres du projet (ProjectInformation)
        return self._get_project_param_value(param_name)

    def _extract_param_value(self, param):
        """Extrait la valeur d'un paramètre Revit de manière robuste."""
        if not param:
            return ''

        # AsString (textes)
        try:
            s = param.AsString()
            if s is not None and len(s) > 0:
                return s
        except Exception:
            pass

        # AsValueString (nombres/unités/booléens formatés)
        try:
            vs = param.AsValueString()
            if vs:
                return vs
        except Exception:
            pass

        # Fallback via StorageType
        try:
            if DB:
                st = param.StorageType
                if st == DB.StorageType.Integer:
                    return str(param.AsInteger())
                elif st == DB.StorageType.Double:
                    return "{:.3f}".format(param.AsDouble())
                elif st == DB.StorageType.String:
                    return param.AsString() or ''
                elif st == DB.StorageType.ElementId:
                    eid = param.AsElementId()
                    return str(eid.IntegerValue) if eid else ''
        except Exception:
            pass

        return ''

    def _get_system_param_value(self, param_name):
        """Retourne la valeur d'un paramètre système (Date), ou None si non concerné."""
        try:
            from datetime import datetime
            now = datetime.now()
            if param_name == 'Date: Jour':
                return now.strftime('%d')
            elif param_name == 'Date: Mois':
                return now.strftime('%m')
            elif param_name == 'Date: Année':
                return now.strftime('%Y')
        except Exception:
            pass
        return None

    def _get_project_param_value(self, param_name):
        """Retourne la valeur d'un paramètre du projet (ProjectInformation)."""
        if self._doc is None or DB is None:
            return ''

        if self._project_params_cache is None:
            self._project_params_cache = {}
            try:
                proj_info = DB.FilteredElementCollector(self._doc).OfClass(DB.ProjectInfo).ToElements()
                if proj_info and len(proj_info) > 0:
                    for param in proj_info[0].Parameters:
                        try:
                            pdef = param.Definition
                            if pdef is None:
                                continue
                            pname = pdef.Name
                            if not pname:
                                continue
                            val = self._extract_param_value(param)
                            val = self._sanitize_resolved_value(val)
                            self._project_params_cache[pname] = val
                        except Exception:
                            continue
            except Exception:
                pass

        return self._project_params_cache.get(param_name, '')

    # ------------------------------------------------------------------
    # Nettoyage valeur (repr .NET invalide -> vide)
    # ------------------------------------------------------------------

    def _sanitize_resolved_value(self, val):
        """Nettoie une valeur destinée à un nom de fichier.

        Si pythonnet renvoie une représentation d'objet .NET (ex :
        "<Autodesk.Revit.DB.WallType object at 0x00000123>"), on retourne
        une chaîne vide plutôt que ce texte inutilisable.
        """
        if val is None:
            return ''

        try:
            if type(val).__name__ not in ('str', 'unicode'):
                val = str(val)
        except Exception:
            return ''

        if not val:
            return ''

        try:
            stripped = val.strip()
            if 'Autodesk.Revit.DB' in stripped and 'object at' in stripped and '0x' in stripped:
                return ''
        except Exception:
            pass

        return val
