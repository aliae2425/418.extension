# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path:
    sys.path.insert(0, _BUTTON)

from lib.viewmodels.CoupesPageVM import CoupesPageVM
from lib.viewmodels.MainViewModel import MainViewModel


class _ServiceFactice(object):
    """Le contrat que `MainViewModel.charger()` attend d'un FiltresService."""

    def collecter_coupes(self):
        return [{'id': 1, 'nom': u'Coupe AA', 'type': 'Section'},
                {'id': 2, 'nom': u'Façade Sud', 'type': 'Elevation'}]

    def collecter_filtres(self):
        return []


class TestCoupesPageVM(unittest.TestCase):
    def test_libelle_de_type_traduit(self):
        vm = CoupesPageVM(_ServiceFactice().collecter_coupes())
        self.assertEqual([l.TypeVue for l in vm.Lignes],
                         [u'Coupe', u'Élévation'])

    def test_resume(self):
        self.assertEqual(CoupesPageVM([]).Resume, u'0 vue dans le modèle')
        vm = CoupesPageVM(_ServiceFactice().collecter_coupes())
        self.assertEqual(vm.Resume, u'2 vues dans le modèle')


class TestMainViewModel(unittest.TestCase):
    def test_mode_initial_audit(self):
        self.assertEqual(MainViewModel().Mode, u'audit')

    def test_charger_alimente_l_onglet_coupes(self):
        vm = MainViewModel(service=_ServiceFactice())
        vm.charger()
        self.assertEqual(len(vm.CoupesVM.Lignes), 2)

    def test_charger_sans_service_ne_casse_pas(self):
        vm = MainViewModel()
        vm.charger()
        self.assertEqual(vm.CoupesVM.Lignes, [])


if __name__ == '__main__':
    unittest.main()
