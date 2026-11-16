# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))  # -> 418.extension/lib
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from ui.PressePapiersVM import PressePapiersVM


class _Entree(object):
    def __init__(self, id, libelle='3 Murs, 1 Porte', nb_ignores=0, est_2d=False):
        self.id = id
        self.horodatage = datetime.datetime(2026, 11, 4, 9, 5, 7)
        self.libelle = libelle
        self.nb = 4
        self.nb_ignores = nb_ignores
        self.doc_source = 'Projet A'
        self.vue_source = 'Niveau 1'
        self.est_2d = est_2d


class _HistoriqueFactice(object):
    """Double de core.presse_papiers.Historique : plus récente d'abord."""

    def __init__(self, *entrees):
        self.entrees = list(entrees)
        self._abonnes = []

    def ajouter(self, e):
        self.entrees.insert(0, e)
        self._notifier()

    def retirer(self, id):
        self.entrees = [e for e in self.entrees if e.id != id]
        self._notifier()

    def vider(self):
        self.entrees = []
        self._notifier()

    def abonner(self, fn):
        self._abonnes.append(fn)

    def _notifier(self):
        for fn in self._abonnes:
            fn()


class _CompteRendu(object):
    def __init__(self, nb_colles=0, ignores=(), annule=False):
        self.nb_colles = nb_colles
        self.ignores = list(ignores)
        self.annule = annule


class TestPressePapiersVM(unittest.TestCase):
    def setUp(self):
        self.hist = _HistoriqueFactice(_Entree(2, nb_ignores=2, est_2d=True),
                                       _Entree(1, libelle='1 Mur'))
        self.appels = []          # (uidoc, entree.id, mode)
        self.cr = _CompteRendu(nb_colles=4)

        test = self

        class _Noyau(object):
            # Double de core.presse_papiers : retirer/vider passent par lui,
            # comme le vrai, qui purge aussi le document caché.
            def coller(self, uidoc, entree, mode):
                test.appels.append((uidoc, entree.id, mode))
                return test.cr
            retirer = staticmethod(self.hist.retirer)
            vider = staticmethod(self.hist.vider)

        self.noyau = _Noyau()
        self.executes = []

        def executer(fn):
            self.executes.append(fn)
            fn('UIDOC')

        self.vm = PressePapiersVM(self.hist, executer, noyau=self.noyau)

    def test_formatage_des_lignes(self):
        l = self.vm.Lignes[0]
        self.assertEqual(l.Heure, '09:05:07')
        self.assertEqual(l.Source, 'Projet A · Niveau 1')
        self.assertEqual(l.Badge, '2D')
        self.assertEqual(l.Ignores, '2 ignorés')
        self.assertTrue(l.IgnoresVisible)
        l = self.vm.Lignes[1]
        self.assertEqual((l.Libelle, l.Badge, l.Ignores, l.IgnoresVisible),
                         ('1 Mur', '3D', '', False))

    def test_la_plus_recente_est_selectionnee(self):
        self.assertEqual(self.vm.Selection.Id, 2)

    def test_rafraichi_sur_notification_et_garde_la_selection(self):
        self.vm.Selection = self.vm.Lignes[1]
        self.hist.ajouter(_Entree(3))
        self.assertEqual([l.Id for l in self.vm.Lignes], [3, 2, 1])
        self.assertEqual(self.vm.Selection.Id, 1)

    def test_chaque_commande_colle_avec_son_mode(self):
        for commande, mode in (
                (self.vm.CollerMemeEmplacementCommand, 'meme_emplacement'),
                (self.vm.CollerVueCouranteCommand, 'vue_courante'),
                (self.vm.CollerNormalCommand, 'normal')):
            commande.Execute(None)
            self.assertEqual(self.appels[-1], ('UIDOC', 2, mode))
        self.assertEqual(len(self.executes), 3)

    def test_compte_rendu(self):
        self.vm.coller('normal')
        self.assertEqual(self.vm.Etat, '4 éléments collés.')
        self.cr = _CompteRendu(nb_colles=1, ignores=['Pièce', 'Cote'])
        self.vm.coller('normal')
        self.assertEqual(self.vm.Etat, '1 élément collé. 2 ignorés.')
        self.cr = _CompteRendu(annule=True)
        self.vm.coller('normal')
        self.assertEqual(self.vm.Etat, 'Collage annulé.')

    def test_echec_du_collage_affiche_et_ne_leve_pas(self):
        def coller(uidoc, entree, mode):
            raise RuntimeError('boum')
        self.noyau.coller = coller
        vm = PressePapiersVM(self.hist, lambda fn: fn(None), noyau=self.noyau)
        vm.coller('normal')
        self.assertIn('boum', vm.Etat)

    def test_rien_a_coller_sans_selection(self):
        vm = PressePapiersVM(_HistoriqueFactice(), self.executes.append,
                             noyau=self.noyau)
        self.assertTrue(vm.EstVide)
        self.assertFalse(vm.CollerNormalCommand.CanExecute(None))
        vm.coller('normal')
        self.assertEqual(self.executes, [])
        self.assertTrue(vm.Etat)

    def test_retirer_et_vider_passent_par_l_executeur(self):
        self.vm.RetirerCommand.Execute(None)
        self.assertEqual(len(self.executes), 1)
        self.assertEqual([l.Id for l in self.vm.Lignes], [1])
        self.assertEqual(self.vm.Selection.Id, 1)
        self.vm.ViderCommand.Execute(None)
        self.assertTrue(self.vm.EstVide)
        self.assertIsNone(self.vm.Selection)

    def test_fleches_bornees(self):
        self.vm.selectionner_decalage(1)
        self.vm.selectionner_decalage(1)
        self.assertEqual(self.vm.Selection.Id, 1)
        self.vm.selectionner_decalage(-5)
        self.assertEqual(self.vm.Selection.Id, 2)

    def test_popup_non_abonnee_se_rafraichit_seule(self):
        vm = PressePapiersVM(self.hist, lambda fn: fn(None), noyau=self.noyau,
                             suivre=False)
        self.assertEqual(len(self.hist._abonnes), 1)   # celui de setUp seul
        vm.retirer()
        self.assertEqual([l.Id for l in vm.Lignes], [1])


if __name__ == '__main__':
    unittest.main()
