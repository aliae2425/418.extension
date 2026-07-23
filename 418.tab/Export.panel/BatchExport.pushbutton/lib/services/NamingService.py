# -*- coding: utf-8 -*-
# Service de nommage : résolution de patterns contre un élément Revit + persistance.
#
# Consolide la logique historiquement répartie entre :
#   - lib/data/naming/NamingResolver.py   (résolution valeur/pattern)
#   - lib/data/naming/NamingPatternStore.py (persistance pattern + rows)
#
# Objectif : un service unique, testable hors Revit, sans dépendance UI.
#
# Évolution "tokens" (voir docstring de classe) : le pattern canonique est
# désormais une CHAÎNE avec jetons `{...}` (ex. "{numero}_{nom}"), en
# extension du système historique par `rows` (liste de dicts
# Name/Prefix/Suffix). L'ancien système `rows` reste supporté en entrée
# (compat) : `resolve_for_element` accepte toujours une liste, et
# `build_pattern(rows)` continue de produire une chaîne `{Name}` à partir de
# rows, réutilisable telle quelle par le nouveau résolveur de jetons.

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
    try:
        from lib.core.UserConfig import UserConfig  # type: ignore
    except Exception:
        UserConfig = None  # type: ignore


_TOKEN_RE = re.compile(r'\{([^{}]*)\}')

# Jetons spéciaux simples (sans argument), résolus avant le fallback
# paramètre. Clés en minuscules (comparaison insensible à la casse).
_SIMPLE_TOKENS = (
    'numero', 'nom', 'nom_tiret', 'nom_underscore', 'titre',
    'date', 'date_jour', 'date_mois', 'date_annee',
    'projet_nom', 'projet_numero', 'projet_client', 'projet_statut',
)


class NamingService(object):
    """Résout des patterns de nommage et persiste les patterns utilisateur.

    Deux notations de pattern sont acceptées par `resolve_for_element` :

    1. CHAÎNE À JETONS (canonique) : ``"{numero}_{nom}_{param:Phase}"``.
       Chaque `{...}` est remplacé par sa valeur résolue. Jetons spéciaux
       (insensibles à la casse), résolus avant tout fallback paramètre :

           {numero}            SheetNumber de la feuille
           {nom}               SheetName (ou nom/titre de la collection si
                                `elem` est une SheetCollection)
           {nom_tiret}         {nom} avec espaces -> '-'
           {nom_underscore}    {nom} avec espaces -> '_'
           {titre}             titre de la collection (carnet)
           {date}              date du jour AAAA-MM-JJ
           {date_jour}         jour (2 chiffres)
           {date_mois}         mois (2 chiffres)
           {date_annee}        année (4 chiffres)
           {projet_nom}        ProjectInformation.Name
           {projet_numero}     ProjectInformation.Number
           {projet_client}     ProjectInformation.ClientName
           {projet_statut}     ProjectInformation.Status
           {param:NOM}         paramètre NOM sur `elem`
           {param_projet:NOM}  paramètre NOM sur ProjectInformation

       Un jeton `{X}` non reconnu comme spécial est traité comme un NOM DE
       PARAMÈTRE (compat avec les anciens motifs, ex. `{Numéro de projet}`) :
       lookup sur `elem` puis repli ProjectInfo, comme avant. Un jeton
       introuvable résout en chaîne vide (jamais de `{...}` brut dans le
       résultat).

    2. ROWS (historique, compat) : liste de dicts
       ``[{"Name": "Numero_Feuille", "Prefix": "", "Suffix": "-"}, ...]``.
       Si `pattern` est une liste, elle est d'abord convertie en chaîne via
       `build_pattern`, puis résolue comme ci-dessus -- donc les anciens
       noms de paramètres (ex. 'Date: Jour') continuent de fonctionner via
       le fallback paramètre.

    Noms système historiques toujours reconnus via le fallback paramètre :
        'Date: Jour', 'Date: Mois', 'Date: Année'
    """

    _PATTERN_KEY = {'sheet': 'pattern_sheet', 'set': 'pattern_set'}
    _ROWS_KEY = {'sheet': 'pattern_sheet_rows', 'set': 'pattern_set_rows'}
    _PRESETS_KEY = 'naming_presets'

    def __init__(self, doc=None, config=None, namespace='batch_export'):
        self._doc = doc
        self._project_params_cache = None
        self._project_info_elem_cache = None
        if config is not None:
            self._cfg = config
        elif UserConfig is not None:
            self._cfg = UserConfig(namespace)
        else:
            self._cfg = None

    # ------------------------------------------------------------------
    # Résolution
    # ------------------------------------------------------------------

    def resolve_for_element(self, elem, pattern):
        """Résout `pattern` contre `elem`.

        `pattern` peut être :
          - une chaîne à jetons `{...}` (nouveau système, canonique) ;
          - une liste de rows Name/Prefix/Suffix (ancien système, compat) --
            convertie via `build_pattern` puis résolue comme une chaîne.

        Une valeur de jeton introuvable/invalide résout en chaîne vide.
        Ne lève jamais : retourne '' en cas d'échec inattendu.
        """
        try:
            if isinstance(pattern, (list, tuple)):
                pattern = self.build_pattern(pattern)
            pattern = pattern or ''
            if not isinstance(pattern, (str, type(u''))):
                pattern = str(pattern)
        except Exception:
            return ''

        try:
            return _TOKEN_RE.sub(lambda m: self._resolve_token(elem, m.group(1)), pattern)
        except Exception:
            return ''

    def _resolve_token(self, elem, token_body):
        """Résout le contenu d'un `{...}` (sans les accolades) en chaîne."""
        try:
            raw = token_body if token_body is not None else ''
            stripped = raw.strip()
            if not stripped:
                return ''

            lowered = stripped.lower()

            # Jetons paramétrés : {param:NOM} / {param_projet:NOM}
            if ':' in stripped:
                keyword, _, arg = stripped.partition(':')
                keyword_l = keyword.strip().lower()
                arg = arg.strip()
                if keyword_l == 'param':
                    return self._sanitize_resolved_value(self._get_param_value(elem, arg))
                if keyword_l == 'param_projet':
                    return self._sanitize_resolved_value(self._get_project_param_value(arg))
                # Préfixe ':' non reconnu -> traiter comme paramètre nommé
                # complet (fallback), au cas où un nom de paramètre contient
                # ':' (rare mais possible historiquement).
                return self._sanitize_resolved_value(self._get_param_value(elem, stripped))

            if lowered in _SIMPLE_TOKENS:
                return self._resolve_simple_token(elem, lowered)

            # Fallback : nom de paramètre (compat ancien système).
            return self._sanitize_resolved_value(self._get_param_value(elem, stripped))
        except Exception:
            return ''

    def _resolve_simple_token(self, elem, lowered):
        try:
            if lowered == 'numero':
                return self._sanitize_resolved_value(self._get_sheet_number(elem))
            if lowered == 'nom':
                return self._sanitize_resolved_value(self._get_display_name(elem))
            if lowered == 'nom_tiret':
                nom = self._get_display_name(elem)
                return self._sanitize_resolved_value(nom).replace(' ', '-')
            if lowered == 'nom_underscore':
                nom = self._get_display_name(elem)
                return self._sanitize_resolved_value(nom).replace(' ', '_')
            if lowered == 'titre':
                return self._sanitize_resolved_value(self._get_collection_title(elem))
            if lowered == 'date':
                return self._get_date_part('date')
            if lowered in ('date_jour', 'date_mois', 'date_annee'):
                return self._get_date_part(lowered)
            if lowered == 'projet_nom':
                return self._sanitize_resolved_value(self._get_project_info_property('Name'))
            if lowered == 'projet_numero':
                return self._sanitize_resolved_value(self._get_project_info_property('Number'))
            if lowered == 'projet_client':
                return self._sanitize_resolved_value(self._get_project_info_property('ClientName'))
            if lowered == 'projet_statut':
                return self._sanitize_resolved_value(self._get_project_info_property('Status'))
        except Exception:
            return ''
        return ''

    def build_pattern(self, rows):
        """Construit un template lisible : Prefix + {Name} + Suffix concaténés.

        Conservé pour compat avec l'ancien système `rows` : produit une
        chaîne à jetons `{Name}` que `resolve_for_element` sait résoudre via
        son fallback "nom de paramètre".
        """
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
    # Jetons spéciaux : extraction élément / collection / projet
    # ------------------------------------------------------------------

    def _get_sheet_number(self, elem):
        if elem is None:
            return ''
        try:
            val = getattr(elem, 'SheetNumber', None)
            if val:
                return val
        except Exception:
            pass
        val = self._get_param_value(elem, 'Sheet Number')
        if val:
            return val
        return self._get_param_value(elem, 'SheetNumber')

    def _get_display_name(self, elem):
        """Nom d'affichage : SheetName pour une feuille, nom/titre pour une
        collection (carnet). Repli sur propriété 'Name' générique."""
        if elem is None:
            return ''
        try:
            val = getattr(elem, 'Name', None)
            if val:
                return val
        except Exception:
            pass
        val = self._get_param_value(elem, 'Sheet Name')
        if val:
            return val
        return self._get_param_value(elem, 'SheetName')

    def _get_collection_title(self, elem):
        """Titre d'une collection (carnet) : propriété 'Name', repli sur
        paramètre 'Titre'/'Title'."""
        if elem is None:
            return ''
        try:
            val = getattr(elem, 'Name', None)
            if val:
                return val
        except Exception:
            pass
        val = self._get_param_value(elem, 'Titre')
        if val:
            return val
        return self._get_param_value(elem, 'Title')

    def _get_date_part(self, kind):
        try:
            from datetime import datetime
            now = datetime.now()
            if kind == 'date':
                return now.strftime('%Y-%m-%d')
            if kind == 'date_jour':
                return now.strftime('%d')
            if kind == 'date_mois':
                return now.strftime('%m')
            if kind == 'date_annee':
                return now.strftime('%Y')
        except Exception:
            pass
        return ''

    def _get_project_info_elem(self):
        """Retourne l'élément ProjectInfo brut (mis en cache), ou None."""
        if self._project_info_elem_cache is not None:
            return self._project_info_elem_cache
        if self._doc is None or DB is None:
            return None
        try:
            proj_info = DB.FilteredElementCollector(self._doc).OfClass(DB.ProjectInfo).ToElements()
            if proj_info and len(proj_info) > 0:
                self._project_info_elem_cache = proj_info[0]
                return self._project_info_elem_cache
        except Exception:
            pass
        return None

    def _get_project_info_property(self, prop_name):
        """Lit une propriété .NET directe de ProjectInfo (Name, Number,
        ClientName, Status) -- indépendant de la langue Revit, à la
        différence d'un lookup par nom de paramètre localisé."""
        elem = self._get_project_info_elem()
        if elem is None:
            return ''
        try:
            val = getattr(elem, prop_name, None)
            if val is not None and type(val).__name__ in ('str', 'unicode'):
                return val
        except Exception:
            pass
        return ''

    # ------------------------------------------------------------------
    # Persistance (via UserConfig, namespace 'batch_export')
    # ------------------------------------------------------------------

    def save(self, kind, pattern, rows=None):
        """Persiste `pattern` (chaîne canonique) pour kind ('sheet' ou 'set').

        `rows` est accepté pour compat de signature avec l'ancien appelant
        (`save(kind, pattern, rows)`) mais n'est plus la source de vérité :
        conservé uniquement en best-effort pour ne pas casser d'anciens
        lecteurs de `*_rows`, jamais requis pour `load`.
        """
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
        """Retourne (pattern_string, rows_list) pour kind ('sheet' ou 'set').

        `pattern_string` est la valeur canonique (chaîne à jetons, ou ancien
        template `{Name}` produit par `build_pattern`). `rows_list` est
        conservé pour compat des appelants historiques (liste vide si le
        pattern a été enregistré sans rows, ex. saisie directe d'une chaîne
        à jetons dans l'UI)."""
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
        """Un pattern est considéré comme enregistré dès qu'il est non vide.

        NB : ne dépend plus de la présence de `rows` -- un pattern à jetons
        enregistré sans rows (nouveau système) doit être reconnu comme
        "enregistré" au même titre qu'un ancien pattern avec rows."""
        pattern, _rows = self.load(kind)
        return bool(pattern)

    # ------------------------------------------------------------------
    # Presets nommés (persistés en JSON sous une clé unique)
    # ------------------------------------------------------------------

    def list_presets(self):
        """Retourne `[{'name': unicode, 'pattern': unicode}, ...]`."""
        if self._cfg is None:
            return []
        try:
            raw = self._cfg.get(self._PRESETS_KEY, '')
            if not raw:
                return []
            parsed = json.loads(raw)
            if not isinstance(parsed, list):
                return []
            out = []
            for item in parsed:
                if isinstance(item, dict) and item.get('name'):
                    out.append({
                        'name': item.get('name', ''),
                        'pattern': item.get('pattern', ''),
                    })
            return out
        except Exception:
            return []

    def save_preset(self, name, pattern):
        """Ajoute/remplace un preset nommé. Best-effort, ne lève jamais."""
        if self._cfg is None:
            return False
        name = (name or '').strip()
        if not name:
            return False
        try:
            presets = self.list_presets()
            presets = [p for p in presets if p.get('name') != name]
            presets.append({'name': name, 'pattern': pattern or ''})
            self._cfg.set(self._PRESETS_KEY, json.dumps(presets))
            return True
        except Exception:
            return False

    def delete_preset(self, name):
        """Supprime un preset nommé. Best-effort, ne lève jamais."""
        if self._cfg is None:
            return False
        name = (name or '').strip()
        if not name:
            return False
        try:
            presets = self.list_presets()
            remaining = [p for p in presets if p.get('name') != name]
            if len(remaining) == len(presets):
                return False
            self._cfg.set(self._PRESETS_KEY, json.dumps(remaining))
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Jetons disponibles (pour badges insérables côté UI)
    # ------------------------------------------------------------------

    def available_tokens(self):
        """Retourne `[{'token': '{numero}', 'desc': '...'}, ...]` : la liste
        des jetons spéciaux gérés, pour affichage de badges insérables dans
        l'éditeur de nommage. Inclut des entrées génériques pour les jetons
        paramétrés `{param:NOM}` / `{param_projet:NOM}`."""
        return [
            {'token': '{numero}', 'desc': 'Numéro de feuille'},
            {'token': '{nom}', 'desc': 'Nom de la feuille (ou titre du carnet)'},
            {'token': '{nom_tiret}', 'desc': 'Nom avec espaces remplacés par -'},
            {'token': '{nom_underscore}', 'desc': 'Nom avec espaces remplacés par _'},
            {'token': '{titre}', 'desc': 'Titre du carnet'},
            {'token': '{date}', 'desc': 'Date du jour (AAAA-MM-JJ)'},
            {'token': '{date_jour}', 'desc': 'Jour courant (JJ)'},
            {'token': '{date_mois}', 'desc': 'Mois courant (MM)'},
            {'token': '{date_annee}', 'desc': 'Année courante (AAAA)'},
            {'token': '{projet_nom}', 'desc': 'Nom du projet'},
            {'token': '{projet_numero}', 'desc': 'Numéro du projet'},
            {'token': '{projet_client}', 'desc': 'Client du projet'},
            {'token': '{projet_statut}', 'desc': 'Statut du projet'},
            {'token': '{param:NOM}', 'desc': "Paramètre NOM sur l'élément"},
            {'token': '{param_projet:NOM}', 'desc': 'Paramètre NOM du projet'},
        ]

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
            elem = self._get_project_info_elem()
            if elem is not None:
                try:
                    for param in elem.Parameters:
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
