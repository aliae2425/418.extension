# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import io
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path:
    sys.path.insert(0, _BUTTON)

from lib.dxf import ecrire, polyligne


def _lignes(contenu):
    """Le DXF est une paire (code, valeur) par deux lignes."""
    return [l for l in contenu.split('\n') if l != '']


class TestPolyligne(unittest.TestCase):
    def test_structure_et_vertex(self):
        texte = polyligne([(0, 0), (10, 0), (10, 5)])
        self.assertEqual(texte.count('VERTEX'), 3)
        self.assertEqual(texte.count('POLYLINE'), 1)
        self.assertEqual(texte.count('SEQEND'), 1)
        # 66 = « des VERTEX suivent », obligatoire en R12.
        self.assertIn('66\n1\n', texte)

    def test_flag_fermeture(self):
        self.assertIn('70\n1\n', polyligne([(0, 0), (1, 1)], fermee=True))
        self.assertIn('70\n0\n', polyligne([(0, 0), (1, 1)], fermee=False))

    def test_coordonnees_ecrites(self):
        texte = polyligne([(1.5, -2.25)])
        self.assertIn('10\n1.500000\n', texte)
        self.assertIn('20\n-2.250000\n', texte)


class TestEcrire(unittest.TestCase):
    def setUp(self):
        fd, self.chemin = tempfile.mkstemp(suffix='.dxf')
        os.close(fd)

    def tearDown(self):
        if os.path.exists(self.chemin):
            os.remove(self.chemin)

    def _contenu(self):
        with io.open(self.chemin, 'r', encoding='ascii') as f:
            return f.read()

    def test_fichier_complet(self):
        nb = ecrire(self.chemin, [([(0, 0), (10, 0)], False),
                                  ([(0, 0), (5, 5), (0, 5)], True)])
        self.assertEqual(nb, 2)
        contenu = self._contenu()
        self.assertEqual(contenu.count('POLYLINE'), 2)
        self.assertEqual(contenu.count('VERTEX'), 5)
        self.assertIn('AC1009', contenu)
        # Le fichier doit se terminer par la paire 0/EOF.
        self.assertEqual(_lignes(contenu)[-2:], ['0', 'EOF'])

    def test_polyligne_degeneree_ignoree(self):
        nb = ecrire(self.chemin, [([(0, 0)], False), ([], False),
                                  ([(0, 0), (1, 1)], False)])
        self.assertEqual(nb, 1)
        self.assertEqual(self._contenu().count('POLYLINE'), 1)

    def test_fichier_vide_reste_valide(self):
        self.assertEqual(ecrire(self.chemin, []), 0)
        contenu = self._contenu()
        self.assertIn('ENTITIES', contenu)
        self.assertEqual(_lignes(contenu)[-2:], ['0', 'EOF'])


if __name__ == '__main__':
    unittest.main()
