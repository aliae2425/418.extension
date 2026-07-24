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


if __name__ == '__main__':
    unittest.main()
