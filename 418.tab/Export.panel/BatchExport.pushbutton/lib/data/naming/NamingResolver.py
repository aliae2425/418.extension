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

    def _get_param_value(self, elem, param_name):
        """Retourne une représentation chaîne du paramètre nommé sur l'élément, si trouvé."""
        # D'abord chercher sur l'élément lui-même
        try:
            params = getattr(elem, 'Parameters', None)
            if params is None:
                # Si pas de paramètres sur l'élément, chercher dans le projet
                return self._get_project_param_value(param_name)
            
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
        
        # Si pas trouvé sur l'élément, chercher dans les paramètres du projet
        return self._get_project_param_value(param_name)

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
            # Si valeur vide: utiliser chaîne vide (pas de fallback vers token)
            if not val:
                val = ''
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
