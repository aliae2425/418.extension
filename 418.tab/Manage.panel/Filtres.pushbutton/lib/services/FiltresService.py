# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Collecte Revit de l'outil « Gérer les filtres ».
#
# Scaffold : seule la collecte de l'onglet Coupes est écrite. Les onglets
# Audit et Plans de repérage n'ont encore ni service ni ViewModel.

try:
    from Autodesk.Revit.DB import FilteredElementCollector, View
except Exception:
    FilteredElementCollector = None
    View = None

# Les deux types de vue que l'onglet 1 liste pour l'instant.
TYPES_COUPE = ('Section', 'Elevation')


class FiltresService(object):
    def __init__(self, doc=None):
        self._doc = doc

    def collecter_coupes(self):
        """[{'id', 'nom', 'type'}] — coupes et élévations, triées par nom.

        `type` est le nom brut de `ViewType` ('Section' / 'Elevation') : le
        tri par nom de ViewType est la forme utilisée partout dans le dépôt,
        elle survit aux vues qui ne dérivent pas de la classe attendue.
        """
        if self._doc is None or FilteredElementCollector is None:
            return []
        vues = []
        for vue in FilteredElementCollector(self._doc).OfClass(View).ToElements():
            if getattr(vue, 'IsTemplate', False):
                continue
            type_vue = self._type(vue)
            if type_vue in TYPES_COUPE:
                vues.append({'id': vue.Id, 'nom': vue.Name, 'type': type_vue})
        vues.sort(key=lambda v: v['nom'])
        return vues

    @staticmethod
    def _type(vue):
        try:
            return vue.ViewType.ToString()
        except Exception:
            return u''
