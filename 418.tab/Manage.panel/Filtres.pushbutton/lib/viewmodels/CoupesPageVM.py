# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from ui.base.BaseViewModel import BaseViewModel
except Exception:
    from lib.ui.base.BaseViewModel import BaseViewModel

# Libellés d'affichage des `ViewType` listés par l'onglet.
_LIBELLES = {'Section': u'Coupe', 'Elevation': u'Élévation'}


class CoupeRowVM(BaseViewModel):
    """Une coupe ou une élévation. Lecture seule pour l'instant."""

    def __init__(self, vue_id, nom, type_vue):
        super(CoupeRowVM, self).__init__()
        self.Id = vue_id
        self._nom = nom
        self._type = type_vue

    @property
    def Nom(self):
        return self._nom

    @property
    def TypeVue(self):
        return _LIBELLES.get(self._type, self._type)


class CoupesPageVM(BaseViewModel):
    """Onglet 1 : la liste des coupes et élévations du modèle.

    Scaffold : pas de sélection, pas de filtre, pas d'action. Quand la logique
    arrivera, la liste passera par `SelectionPageVM` du socle plutôt que par
    ces lignes nues.
    """

    def __init__(self, coupes=None):
        super(CoupesPageVM, self).__init__()
        self.Lignes = [CoupeRowVM(c['id'], c['nom'], c['type'])
                       for c in (coupes or [])]

    @property
    def TitrePage(self):
        return u'Coupes et élévations'

    @property
    def Resume(self):
        return u'{} vue{} dans le modèle'.format(
            len(self.Lignes), u's' if len(self.Lignes) > 1 else u'')
