# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core.transaction import revit_transaction


class FakeTransaction(object):
    """Enregistre la séquence d'appels pour vérifier le flux."""
    def __init__(self, doc, name):
        self.name = name
        self.calls = []
        FakeTransaction.last = self

    def Start(self):
        self.calls.append('Start')

    def Commit(self):
        self.calls.append('Commit')

    def RollBack(self):
        self.calls.append('RollBack')


class TestRevitTransaction(unittest.TestCase):
    def setUp(self):
        import core.transaction as mod
        self._mod = mod
        self._orig = mod.Transaction
        mod.Transaction = FakeTransaction

    def tearDown(self):
        self._mod.Transaction = self._orig

    def test_commit_en_sortie_normale(self):
        with revit_transaction(object(), u'T'):
            pass
        self.assertEqual(FakeTransaction.last.calls, ['Start', 'Commit'])

    def test_rollback_puis_reeleve_sur_exception(self):
        with self.assertRaises(ValueError):
            with revit_transaction(object(), u'T'):
                raise ValueError('boom')
        self.assertEqual(FakeTransaction.last.calls, ['Start', 'RollBack'])


if __name__ == '__main__':
    unittest.main()
