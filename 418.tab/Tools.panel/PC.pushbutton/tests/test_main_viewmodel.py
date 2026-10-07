# -*- coding: utf-8 -*-
"""Le parcours : Dossier -> Pièces -> Aperçu, sans Revit ni WPF."""
from __future__ import unicode_literals
import os
import shutil
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path:
    sys.path.insert(0, _BUTTON)

from lib.viewmodels.MainViewModel import MainViewModel
from lib.viewmodels.PiecesPageVM import AUCUN_JEU
from lib.models import pieces as catalogue

INFOS = {u'projet_numero': u'2431', u'projet_nom': u'Maison Dupont'}


class _Store(object):
    """Double de UserConfig : rien n'est écrit sur le disque."""

    def __init__(self):
        self._d = {}

    def get(self, cle, defaut=None):
        return self._d.get(cle, defaut)

    def set(self, cle, valeur):
        # Fidèle : UserConfig sérialise TOUTE valeur en chaîne.
        self._d[cle] = u'{0}'.format(valeur)


def _vm(jeux=None, store=None):
    return MainViewModel(config=store if store is not None else _Store(),
                         infos=INFOS, jeux=jeux or [])


class TestParcours(unittest.TestCase):

    def test_on_ouvre_sur_le_dossier(self):
        self.assertEqual(_vm().Mode, u'dossier')

    def test_les_pieces_du_type_par_defaut_sont_chargees(self):
        vm = _vm()
        self.assertTrue(len(list(vm.PiecesVM.Pieces)) > 0)

    def test_les_obligatoires_sont_cochees_d_office(self):
        vm = _vm()
        vm.DossierVM.Type = u'PC'
        coches = set(p.Code for p in vm.PiecesVM.retenues())
        self.assertEqual(coches, set(catalogue.obligatoires(u'PC')))

    def test_changer_de_type_recharge_les_pieces(self):
        vm = _vm()
        vm.DossierVM.Type = u'PC'
        vm.DossierVM.Type = u'PD'
        codes = [p.Code for p in list(vm.PiecesVM.Pieces)]
        self.assertTrue(all(c.startswith(u'PD') for c in codes), codes)

    def test_un_type_grise_est_refuse(self):
        vm = _vm()
        avant = vm.DossierVM.Type
        vm.DossierVM.Type = u'PCMI'      # pas de catalogue : inactif
        self.assertEqual(vm.DossierVM.Type, avant)

    def test_revenir_sur_les_pieces_ne_perd_pas_les_cases(self):
        # La navigation ne doit jamais effacer un choix.
        vm = _vm()
        vm.set_mode(u'pieces')
        for piece in list(vm.PiecesVM.Pieces):
            piece.Coche = False
        list(vm.PiecesVM.Pieces)[0].Coche = True
        vm.set_mode(u'apercu')
        vm.set_mode(u'pieces')
        self.assertEqual(len(vm.PiecesVM.retenues()), 1)

    def test_l_apercu_se_recalcule_en_y_entrant(self):
        vm = _vm()
        vm.DossierVM.Destination = tempfile.gettempdir()
        vm.set_mode(u'apercu')
        # La racine, plus une ligne par pièce retenue.
        self.assertEqual(len(vm.ApercuVM.Lignes),
                         len(vm.PiecesVM.retenues()) + 1)


class TestApercu(unittest.TestCase):

    def test_sans_destination_on_ne_peut_pas_generer(self):
        vm = _vm()
        vm.set_mode(u'apercu')
        self.assertFalse(vm.ApercuVM.PeutGenerer)
        self.assertIn(u'destination', vm.ApercuVM.Avertissement)

    def test_sans_piece_on_ne_peut_pas_generer(self):
        vm = _vm()
        vm.DossierVM.Destination = tempfile.gettempdir()
        vm.set_mode(u'pieces')
        vm.PiecesVM.tout_decocher()
        vm.set_mode(u'apercu')
        self.assertFalse(vm.ApercuVM.PeutGenerer)
        self.assertIn(u'pièce', vm.ApercuVM.Avertissement)

    def test_l_apercu_porte_le_jeu_retenu(self):
        vm = _vm(jeux=[u'PC - Coupes'])
        vm.DossierVM.Destination = tempfile.gettempdir()
        vm.set_mode(u'pieces')
        list(vm.PiecesVM.Pieces)[0].Jeu = u'PC - Coupes'
        vm.set_mode(u'apercu')
        self.assertIn(u'PC - Coupes', [l.Jeu for l in vm.ApercuVM.Lignes])

    def test_aucun_jeu_ne_s_affiche_pas(self):
        vm = _vm(jeux=[u'PC - Coupes'])
        vm.DossierVM.Destination = tempfile.gettempdir()
        vm.set_mode(u'apercu')
        for ligne in vm.ApercuVM.Lignes:
            self.assertFalse(ligne.JeuVisible)
            self.assertNotEqual(ligne.Jeu, AUCUN_JEU)


class TestLancer(unittest.TestCase):

    def setUp(self):
        self.dossier = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dossier, ignore_errors=True)

    def test_genere_l_arborescence_annoncee_par_l_apercu(self):
        vm = _vm()
        vm.DossierVM.Type = u'PC'
        vm.DossierVM.Destination = self.dossier
        vm.set_mode(u'apercu')
        attendus = vm.ApercuVM.chemins()
        vm.lancer()
        for chemin in attendus:
            self.assertTrue(os.path.isdir(chemin), chemin)

    def test_le_nom_de_racine_suit_le_motif(self):
        vm = _vm()
        vm.DossierVM.Type = u'PC'
        vm.DossierVM.Destination = self.dossier
        vm.lancer()
        self.assertTrue(os.path.isdir(
            os.path.join(self.dossier, u'2431 - Maison Dupont - PC')))

    def test_sans_destination_rien_n_est_ecrit_et_on_le_dit(self):
        vm = _vm()
        vm.set_mode(u'apercu')
        message = vm.lancer()
        self.assertIn(u'destination', message)
        self.assertEqual(os.listdir(self.dossier), [])


class TestPersistance(unittest.TestCase):

    def test_le_type_et_la_destination_sont_retenus(self):
        store = _Store()
        vm = _vm(store=store)
        vm.DossierVM.Type = u'PD'
        vm.DossierVM.Destination = u'C:\\projets'
        self.assertEqual(_vm(store=store).DossierVM.Type, u'PD')
        self.assertEqual(_vm(store=store).DossierVM.Destination,
                         u'C:\\projets')

    def test_un_type_persiste_puis_grise_retombe_sur_un_actif(self):
        # Le jour où un type sort du catalogue, le réglage sauvegardé ne doit
        # pas ouvrir la fenêtre sur un type mort.
        store = _Store()
        store.set('type', u'PCMI')
        self.assertTrue(catalogue.actif(_vm(store=store).DossierVM.Type))

    def test_aucun_none_ecrit_dans_un_magasin_de_chaines(self):
        # UserConfig sérialise None en « None », qui repasserait ensuite pour
        # une valeur légitime.
        store = _Store()
        vm = _vm(store=store)
        vm.DossierVM.Destination = None
        self.assertNotIn(u'None', store._d.values())


if __name__ == '__main__':
    unittest.main()
