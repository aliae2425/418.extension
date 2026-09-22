# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))  # -> lib
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core import journal


class TestJournal(unittest.TestCase):
    def setUp(self):
        journal.vider()

    def tearDown(self):
        journal.vider()

    def test_ecrit_puis_relit(self):
        journal.journal('test').error('bouée %s', 42)
        fin = journal.lire()
        self.assertIn('bouée 42', fin)
        self.assertIn('openarchi.test', fin)
        self.assertIn('ERROR', fin)

    def test_accents_et_niveaux(self):
        log = journal.journal('accents')
        log.info('café à l\'œil')
        self.assertIn('café à l\'œil', journal.lire())

    def test_lire_limite_le_nombre_de_lignes(self):
        log = journal.journal('volume')
        for i in range(30):
            log.info('ligne %s', i)
        self.assertEqual(len(journal.lire(5).splitlines()), 5)
        self.assertIn('ligne 29', journal.lire(5))

    def test_vider_remet_a_zero(self):
        journal.journal('test').info('avant')
        journal.vider()
        self.assertEqual(journal.lire(), '')

    def test_flux_est_ouvert_en_ajout(self):
        # Sert de sortie à un sous-processus : il ne doit pas tronquer.
        journal.journal('test').info('avant')
        ouvert = journal.flux()
        self.assertIsNotNone(ouvert)
        ouvert.write(b'depuis un fils\n')
        ouvert.close()
        fin = journal.lire()
        self.assertIn('avant', fin)
        self.assertIn('depuis un fils', fin)

    def test_pas_de_remontee_vers_la_racine_logging(self):
        # Sinon pyRevit reçoit une copie de chaque ligne.
        self.assertFalse(journal.journal('test').parent.propagate)


if __name__ == '__main__':
    unittest.main()
