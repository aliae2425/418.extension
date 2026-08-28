# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Collecte Revit de l'outil « Gérer les filtres ».
#
# Le service ne fait QUE lire et mettre en dictionnaires : tout le comptage,
# le regroupement et la notation vivent dans les ViewModels, qui tournent donc
# hors Revit et se testent. Même partage que MaterialService / AuditPageVM.

try:
    from Autodesk.Revit.DB import (Category, FilteredElementCollector,
                                   FilterElement, SelectionFilterElement, View)
except Exception:
    Category = None
    FilteredElementCollector = None
    FilterElement = None
    SelectionFilterElement = None
    View = None

# Les deux types de vue que l'onglet Coupes liste pour l'instant.
TYPES_COUPE = ('Section', 'Elevation')

#: Sondes de surcharge graphique : (nom de propriété, « est-elle posée ? »).
#: Un filtre laissé visible ET sans aucune de ces surcharges ne change rien à
#: l'affichage — c'est ce que l'audit appelle « sans effet ».
#:
#: ponytail: liste de sondes plutôt qu'une comparaison à un
#: OverrideGraphicSettings neuf — la classe n'a pas d'égalité, et énumérer les
#: propriétés une à une reste lisible. Une surcharge exotique non sondée passe
#: pour « sans effet » ; ajouter la propriété ici suffit à la rattraper.
_SONDES = (
    ('Halftone', bool),
    ('Transparency', lambda v: int(v) > 0),
    ('DetailLevel', lambda v: v.ToString() != 'Undefined'),
    ('ProjectionLineColor', lambda v: bool(v.IsValid)),
    ('CutLineColor', lambda v: bool(v.IsValid)),
    ('ProjectionLineWeight', lambda v: int(v) > 0),
    ('CutLineWeight', lambda v: int(v) > 0),
    ('ProjectionLinePatternId', lambda v: _pose(v)),
    ('CutLinePatternId', lambda v: _pose(v)),
    ('SurfaceForegroundPatternId', lambda v: _pose(v)),
    ('SurfaceBackgroundPatternId', lambda v: _pose(v)),
    ('CutForegroundPatternId', lambda v: _pose(v)),
    ('CutBackgroundPatternId', lambda v: _pose(v)),
    # Les quatre drapeaux de visibilité de motif valent True par défaut :
    # c'est leur passage à False qui est une surcharge.
    ('SurfaceForegroundPatternVisible', lambda v: not v),
    ('SurfaceBackgroundPatternVisible', lambda v: not v),
    ('CutForegroundPatternVisible', lambda v: not v),
    ('CutBackgroundPatternVisible', lambda v: not v),
)


def _pose(element_id):
    """Vrai si l'ElementId désigne vraiment quelque chose."""
    return _entier(element_id) > 0


def _entier(element_id):
    """Valeur entière d'un ElementId, quel que soit le millésime.

    `IntegerValue` est déprécié depuis 2024 au profit de `Value` ; on tente
    donc `Value` d'abord. Sert de clé de dictionnaire : un ElementId n'est pas
    hachable de façon fiable sous IronPython.
    """
    for attribut in ('Value', 'IntegerValue'):
        try:
            return int(getattr(element_id, attribut))
        except Exception:
            continue
    return -1


class FiltresService(object):
    def __init__(self, doc=None):
        self._doc = doc

    # -- Onglet Coupes ----------------------------------------------------

    def collecter_coupes(self):
        """[{'id', 'nom', 'type'}] — coupes et élévations, triées par nom.

        `type` est le nom brut de `ViewType` ('Section' / 'Elevation') : le
        tri par nom de ViewType est la forme utilisée partout dans le dépôt,
        elle survit aux vues qui ne dérivent pas de la classe attendue.
        """
        if self._doc is None or FilteredElementCollector is None:
            return []
        vues = []
        for vue in self._toutes_les_vues():
            if getattr(vue, 'IsTemplate', False):
                continue
            type_vue = self._type(vue)
            if type_vue in TYPES_COUPE:
                vues.append({'id': vue.Id, 'nom': vue.Name, 'type': type_vue})
        vues.sort(key=lambda v: v['nom'])
        return vues

    # -- Onglet Audit -----------------------------------------------------

    def collecter_filtres(self):
        """[{...}] — un dictionnaire par filtre du modèle, trié par nom.

        Clés : `nom`, `genre` ('parametrique' | 'selection'), `categories`
        (noms lisibles), `vues` et `gabarits` (noms de ce qui l'applique),
        `effets` (nombre d'applications qui changent vraiment l'affichage).

        Que des types Python : l'AuditPageVM en dérive tous ses chiffres sans
        jamais retoucher au document, et se teste hors Revit.
        """
        if self._doc is None or FilteredElementCollector is None:
            return []
        usages = self._usages()
        filtres = []
        for filtre in FilteredElementCollector(self._doc).OfClass(FilterElement).ToElements():
            usage = usages.get(_entier(filtre.Id), None) or {
                'vues': [], 'gabarits': [], 'effets': 0}
            filtres.append({
                'nom': filtre.Name,
                'genre': self._genre(filtre),
                'categories': self._categories(filtre),
                'vues': sorted(usage['vues']),
                'gabarits': sorted(usage['gabarits']),
                'effets': usage['effets'],
            })
        filtres.sort(key=lambda f: f['nom'])
        return filtres

    def _usages(self):
        """{id entier du filtre: {'vues', 'gabarits', 'effets'}}.

        Un seul balayage des vues : `GetFilters()` est la seule façon de
        savoir où un filtre sert, il n'y a pas de chemin inverse dans l'API.
        Les vues qui n'admettent pas de filtre (légendes, feuilles, certaines
        nomenclatures) lèvent — d'où le try/except par vue.
        """
        usages = {}
        for vue in self._toutes_les_vues():
            try:
                ids = list(vue.GetFilters())
            except Exception:
                continue
            for fid in ids:
                entree = usages.setdefault(
                    _entier(fid), {'vues': [], 'gabarits': [], 'effets': 0})
                ou = 'gabarits' if getattr(vue, 'IsTemplate', False) else 'vues'
                entree[ou].append(vue.Name)
                if self._a_un_effet(vue, fid):
                    entree['effets'] += 1
        return usages

    @staticmethod
    def _a_un_effet(vue, fid):
        """Vrai si l'application du filtre change quelque chose à l'écran."""
        try:
            if not vue.GetFilterVisibility(fid):
                return True                 # le filtre masque : effet certain
        except Exception:
            pass
        try:
            surcharges = vue.GetFilterOverrides(fid)
        except Exception:
            return True                     # dans le doute, pas d'accusation
        for (propriete, est_posee) in _SONDES:
            try:
                if est_posee(getattr(surcharges, propriete)):
                    return True
            except Exception:
                continue
        return False

    @staticmethod
    def _genre(filtre):
        if SelectionFilterElement is not None and isinstance(filtre, SelectionFilterElement):
            return 'selection'
        return 'parametrique'

    def _categories(self, filtre):
        """Noms des catégories ciblées. Vide pour un filtre de sélection."""
        try:
            ids = list(filtre.GetCategories())
        except Exception:
            return []
        noms = []
        for cat_id in ids:
            noms.append(self._nom_categorie(cat_id))
        return sorted(n for n in noms if n)

    def _nom_categorie(self, cat_id):
        try:
            categorie = Category.GetCategory(self._doc, cat_id)
        except Exception:
            categorie = None
        if categorie is None:
            return u'#{}'.format(_entier(cat_id))
        try:
            return categorie.Name
        except Exception:
            return u''

    # -- Commun -----------------------------------------------------------

    def _toutes_les_vues(self):
        """Toutes les vues du document, GABARITS COMPRIS.

        Contrairement à `core.selection.all_views`, qui les écarte : ici un
        gabarit est justement l'endroit où un filtre DEVRAIT vivre.
        """
        return list(FilteredElementCollector(self._doc).OfClass(View).ToElements())

    @staticmethod
    def _type(vue):
        try:
            return vue.ViewType.ToString()
        except Exception:
            return u''
