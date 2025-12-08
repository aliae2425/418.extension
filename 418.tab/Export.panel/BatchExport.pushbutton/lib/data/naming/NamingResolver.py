# -*- coding: utf-8 -*-
# Résolution de nommage pour éléments Revit à partir de rows

from __future__ import unicode_literals

try:
    from Autodesk.Revit import DB  # type: ignore
except Exception:
    DB = None  # type: ignore

class NamingResolver(object):
    def __init__(self, doc=None):
        self._doc = doc
        self._project_params_cache = None

    def _get_project_param_value(self, param_name):
        """Retourne la valeur d'un paramètre du projet (ProjectInformation)."""
        if self._doc is None or DB is None:
            return ''
        
        # Cache les paramètres projet pour éviter de les récupérer à chaque fois
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
                            
                            # Essayer de récupérer la valeur
                            val = ''
                            try:
                                s = param.AsString()
                                if s:
                                    val = s
                            except Exception:
                                pass
                            if not val:
                                try:
                                    vs = param.AsValueString()
                                    if vs:
                                        val = vs
                                except Exception:
                                    pass
                            if not val:
                                try:
                                    val = str(param)
                                except Exception:
                                    pass
                            
                            self._project_params_cache[pname] = val
                        except Exception:
                            continue
            except Exception:
                pass
        
        return self._project_params_cache.get(param_name, '')

    def _extract_param_value(self, param):
        """Extrait la valeur d'un paramètre Revit de manière robuste."""
        if not param:
            return ''
        
        # 1. AsString (pour textes)
        try:
            s = param.AsString()
            if s is not None and len(s) > 0:
                return s
        except Exception:
            pass
            
        # 2. AsValueString (pour nombres/unités/booléens formatés)
        try:
            vs = param.AsValueString()
            if vs:
                return vs
        except Exception:
            pass
            
        # 3. Fallback types primitifs si AsValueString échoue (ex: int brut)
        try:
            # Vérifier le StorageType si DB est dispo
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

    def _get_param_value(self, elem, param_name):
        """Retourne une représentation chaîne du paramètre nommé sur l'élément, si trouvé."""
        val = ''
        
        # 1. Essayer LookupParameter (plus fiable et rapide)
        try:
            p = elem.LookupParameter(param_name)
            if p:
                val = self._extract_param_value(p)
                if val:
                    return val
        except Exception:
            pass

        # 2. Itération manuelle (fallback si LookupParameter échoue pour une raison obscure)
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
        
        # 3. Fallback: Propriété directe (ex: 'Name' sur une SheetCollection qui n'est pas un paramètre standard)
        try:
            if hasattr(elem, param_name):
                val = getattr(elem, param_name)
                # Compatibilité simple: vérifier si c'est une string
                if val and type(val).__name__ in ('str', 'unicode'):
                    return val
        except Exception:
            pass

        # 4. Si pas trouvé sur l'élément, chercher dans les paramètres du projet
        return self._get_project_param_value(param_name)

    # Construit une chaîne résolue pour un élément
    def resolve_for_element(self, elem, rows, empty_fallback=True):
        parts = []
        # Accept both dict and custom string format (already parsed by NamingPatternStore.load)
        for r in rows or []:
            name = r.get('Name', '') if isinstance(r, dict) else r.get('name', '')
            prefix = r.get('Prefix', '') if isinstance(r, dict) else r.get('prefixe', '')
            suffix = r.get('Suffix', '') if isinstance(r, dict) else r.get('suffixe', '')
            token = (name or '').strip()
            if not token:
                continue
            val = self._get_param_value(elem, token)
            if not val:
                val = ''
            parts.append(u"{}{}{}".format(prefix, val, suffix))
        return u''.join(parts)

    # Construit un pattern à partir des rows
    def build_pattern(self, rows):
        parts = []
        for r in rows or []:
            name = r.get('Name', '') if isinstance(r, dict) else r.get('name', '')
            pf = r.get('Prefix', '') if isinstance(r, dict) else r.get('prefixe', '')
            sf = r.get('Suffix', '') if isinstance(r, dict) else r.get('suffixe', '')
            name = name.strip()
            if not name:
                continue
            parts.append(pf + '{' + name + '}' + sf)
        return ''.join(parts)
