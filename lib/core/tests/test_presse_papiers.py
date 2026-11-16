# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core.presse_papiers import Entree, Historique, decalage_niveau, libelle


class TestHistorique(unittest.TestCase):

    def test_la_plus_recente_dabord(self):
        h = Historique()
        a, b = Entree(), Entree()
        h.ajouter(a)
        h.ajouter(b)
        self.assertEqual(h.entrees, [b, a])
        self.assertLess(a.id, b.id)

    def test_limite_evince_la_plus_ancienne(self):
        h = Historique(limite=2)
        a, b, c = Entree(), Entree(), Entree()
        self.assertEqual(h.ajouter(a), [])
        h.ajouter(b)
        self.assertEqual(h.ajouter(c), [a])
        self.assertEqual(h.entrees, [c, b])

    def test_retirer(self):
        h = Historique()
        a, b = Entree(), Entree()
        h.ajouter(a)
        h.ajouter(b)
        self.assertIs(h.retirer(a.id), a)
        self.assertIsNone(h.retirer(a.id))
        self.assertEqual(h.entrees, [b])

    def test_vider(self):
        h = Historique()
        a = Entree()
        h.ajouter(a)
        self.assertEqual(h.vider(), [a])
        self.assertEqual(h.entrees, [])

    def test_abonnes_notifies_a_chaque_changement(self):
        h = Historique()
        appels = []
        h.abonner(lambda: appels.append(1))
        h.abonner(lambda: 1 / 0)           # un abonné qui plante ne bloque rien
        a = Entree()
        h.ajouter(a)
        h.retirer(a.id)
        h.retirer(a.id)                    # rien retiré : pas de notification
        h.vider()
        self.assertEqual(len(appels), 3)


class TestLibelle(unittest.TestCase):

    def test_par_nombre_decroissant_puis_nom(self):
        cats = ['Portes', 'Murs', 'Murs', 'Fenêtres', 'Murs']
        self.assertEqual(libelle(cats), '3 Murs, 1 Fenêtres, 1 Portes')

    def test_categorie_absente(self):
        self.assertEqual(libelle([None]), '1 Sans catégorie')


class TestDecalageNiveau(unittest.TestCase):

    def test_difference_des_elevations(self):
        self.assertEqual(decalage_niveau(3.0, 10.0), 7.0)

    def test_zero_si_un_niveau_manque(self):
        self.assertEqual(decalage_niveau(None, 10.0), 0.0)
        self.assertEqual(decalage_niveau(3.0, None), 0.0)


if __name__ == '__main__':
    unittest.main()
