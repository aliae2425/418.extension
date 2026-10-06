# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

import core.selection as selection


class FakeSheet(object):
    def __init__(self, sid):
        self.Id = sid


class FakeOther(object):
    def __init__(self, oid):
        self.Id = oid


class FakeSelection(object):
    def __init__(self, ids):
        self._ids = ids

    def GetElementIds(self):
        return self._ids


class FakeDoc(object):
    def __init__(self, by_id):
        self._by_id = by_id

    def GetElement(self, eid):
        return self._by_id[eid]


class FakeUIDoc(object):
    def __init__(self, ids, by_id):
        self.Selection = FakeSelection(ids)
        self.Document = FakeDoc(by_id)


class FakeView(object):
    def __init__(self, is_template=False):
        self.IsTemplate = is_template


class TestIsDuplicableView(unittest.TestCase):
    def setUp(self):
        self._orig_View = selection.View
        self._orig_ViewSheet = selection.ViewSheet
        selection.View = FakeView

    def tearDown(self):
        selection.View = self._orig_View
        selection.ViewSheet = self._orig_ViewSheet

    def test_vue_normale_est_duplicable(self):
        vue = FakeView(is_template=False)
        selection.ViewSheet = None  # pas de ViewSheet dans ce contexte
        self.assertTrue(selection._is_duplicable_view(vue))

    def test_template_non_duplicable(self):
        vue = FakeView(is_template=True)
        selection.ViewSheet = None
        self.assertFalse(selection._is_duplicable_view(vue))

    def test_non_view_non_duplicable(self):
        selection.ViewSheet = None
        self.assertFalse(selection._is_duplicable_view(object()))

    def test_viewsheet_non_duplicable(self):
        # Une instance FakeView qui est aussi une FakeSheet (double héritage)
        class FakeSheet(FakeView):
            pass
        selection.ViewSheet = FakeSheet
        feuille = FakeSheet(is_template=False)
        self.assertFalse(selection._is_duplicable_view(feuille))


class TestGetSelectedSheets(unittest.TestCase):
    def setUp(self):
        self._orig = selection.ViewSheet
        selection.ViewSheet = FakeSheet  # substitue le type filtré

    def tearDown(self):
        selection.ViewSheet = self._orig

    def test_ne_retient_que_les_feuilles(self):
        s1, s2, other = FakeSheet(1), FakeSheet(2), FakeOther(3)
        by_id = {1: s1, 2: s2, 3: other}
        uidoc = FakeUIDoc([1, 3, 2], by_id)
        result = selection.get_selected_sheets(uidoc)
        self.assertEqual(result, [s1, s2])

    def test_selection_vide_donne_liste_vide(self):
        uidoc = FakeUIDoc([], {})
        self.assertEqual(selection.get_selected_sheets(uidoc), [])


class TestCleNaturelle(unittest.TestCase):

    def _trie(self, valeurs):
        return sorted(valeurs, key=selection.cle_naturelle)

    def test_numeros_de_feuille_en_ordre_numerique(self):
        """A9 avant A10 : un tri de chaînes donnerait A10, A2, A9."""
        self.assertEqual(
            self._trie([u'A10', u'A2', u'A9', u'A1']),
            [u'A1', u'A2', u'A9', u'A10'])

    def test_prefixes_alphabetiques_respectes(self):
        self.assertEqual(
            self._trie([u'B01', u'A10', u'A02']),
            [u'A02', u'A10', u'B01'])

    def test_noms_de_vue_insensibles_a_la_casse(self):
        self.assertEqual(
            self._trie([u'niveau 2', u'Niveau 10', u'Niveau 1']),
            [u'Niveau 1', u'niveau 2', u'Niveau 10'])

    def test_valeurs_vides_ne_levent_pas(self):
        """None et '' partagent la même clé (tri stable) et passent devant."""
        self.assertEqual(self._trie([u'A1', u'', None])[-1], u'A1')


if __name__ == '__main__':
    unittest.main()
