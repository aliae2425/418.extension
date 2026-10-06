# -*- coding: utf-8 -*-
"""Un collecteur sans filtre refuse d'être parcouru — Revit lève.

C'est ce qu'a fait `revit_categories(avec_types=True)` en vrai. Le double ci-
dessous rejoue exactement cette règle : itérer sans filtre lève.
"""
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from rvt.outils import requete


class _Collecteur(object):
    def __init__(self, elements):
        self._elements = elements
        self._filtre = None

    def WhereElementIsNotElementType(self):
        self._filtre = False
        return self

    def WhereElementIsElementType(self):
        self._filtre = True
        return self

    def __iter__(self):
        if self._filtre is None:
            raise Exception('The collector does not have a filter applied.')
        return iter([e for e in self._elements if e[0] is self._filtre])


class _DB(object):
    # (est_un_type, categorie)
    ELEMENTS = [(False, 'Murs'), (False, 'Murs'), (False, 'Portes'),
                (True, 'Murs'), (True, 'Inconnue')]

    @classmethod
    def FilteredElementCollector(cls, doc):
        return _Collecteur(cls.ELEMENTS)


class TestCategories(unittest.TestCase):
    def setUp(self):
        self._db = requete.DB
        requete.DB = _DB
        self._nom = requete.base.categorie_nom
        requete.base.categorie_nom = lambda e: e[1]

    def tearDown(self):
        requete.DB = self._db
        requete.base.categorie_nom = self._nom

    def test_instances_seules(self):
        self.assertEqual(requete.categories(None)['categories'],
                         {'Murs': 2, 'Portes': 1})

    def test_avec_types_n_itere_jamais_sans_filtre(self):
        self.assertEqual(requete.categories(None, {'avec_types': True})
                         ['categories'], {'Murs': 3, 'Portes': 1})


if __name__ == '__main__':
    unittest.main()
