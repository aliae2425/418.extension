# -*- coding: utf-8 -*-
"""Le parcours : Dossier -> Pièces -> Aperçu, sans Revit ni WPF."""
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

from lib.viewmodels.MainViewModel import MainViewModel
from lib.viewmodels.DossierPageVM import AUCUN_CARTOUCHE
from lib.models import pieces as catalogue

CARTOUCHES = [(1, u'418_Cartouche : A1'), (2, u'418_Cartouche : A3')]


class _Store(object):
    """Double de UserConfig : rien n'est écrit sur le disque."""

    def __init__(self):
        self._d = {}

    def get(self, cle, defaut=None):
        return self._d.get(cle, defaut)

    def set(self, cle, valeur):
        # Fidèle : UserConfig sérialise TOUTE valeur en chaîne.
        self._d[cle] = u'{0}'.format(valeur)


class _Maquette(object):
    """Double du projet : deux coupes et une façade, sans feuille."""

    def __init__(self, vues=None):
        self.vues = vues if vues is not None else {
            u'Section': [(11, u'Coupe AA'), (12, u'Coupe BB')],
            u'Elevation': [(21, u'Façade Nord')],
        }
        self.cree = []

    def analyser(self, piece):
        sortie = []
        for type_de_vue in piece.vues:
            sortie.extend(self.vues.get(type_de_vue, []))
        return sortie

    def creer(self, plan, cartouche):
        self.cree.append((plan, cartouche))
        feuilles = len([f for j in plan.jeux for f in j.feuilles
                        if not f.existe])
        jeux = len([j for j in plan.jeux if not j.existe])
        return feuilles, jeux, []


def _vm(maquette=None, store=None, numeros=(), jeux=()):
    maquette = maquette or _Maquette()
    return MainViewModel(config=store if store is not None else _Store(),
                         cartouches=CARTOUCHES,
                         analyser=maquette.analyser,
                         numeros_existants=numeros,
                         jeux_existants=jeux,
                         creer=maquette.creer)


class TestParcours(unittest.TestCase):

    def test_on_ouvre_sur_le_dossier(self):
        self.assertEqual(_vm().Mode, u'dossier')

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
        vm = _vm()
        vm.set_mode(u'pieces')
        for piece in list(vm.PiecesVM.Pieces):
            piece.Coche = False
        list(vm.PiecesVM.Pieces)[0].Coche = True
        vm.set_mode(u'apercu')
        vm.set_mode(u'pieces')
        self.assertEqual(len(vm.PiecesVM.retenues()), 1)


class TestAnalyse(unittest.TestCase):
    """Le nombre de feuilles vient du projet, pas d'un réglage."""

    def test_une_piece_a_autant_de_feuilles_que_de_vues_libres(self):
        vm = _vm()
        vm.DossierVM.Type = u'PC'
        coupe = [p for p in list(vm.PiecesVM.Pieces) if p.Code == u'PC3'][0]
        self.assertEqual(coupe.Feuilles, 2)      # deux coupes dans le double
        self.assertIn(u'2 vue(s)', coupe.Mention)

    def test_une_piece_sans_vue_garde_une_feuille(self):
        vm = _vm()
        vm.DossierVM.Type = u'PC'
        notice = [p for p in list(vm.PiecesVM.Pieces) if p.Code == u'PC4'][0]
        self.assertEqual(notice.Feuilles, 1)
        self.assertIn(u'à remplir', notice.Mention)

    def test_un_projet_sans_coupe_laisse_une_feuille(self):
        vm = _vm(maquette=_Maquette(vues={}))
        vm.DossierVM.Type = u'PC'
        coupe = [p for p in list(vm.PiecesVM.Pieces) if p.Code == u'PC3'][0]
        self.assertEqual(coupe.Feuilles, 1)
        self.assertIn(u'aucune vue libre', coupe.Mention)

    def test_le_resume_compte_les_feuilles(self):
        vm = _vm()
        vm.DossierVM.Type = u'PC'
        self.assertIn(u'feuille(s)', vm.PiecesVM.Resume)


class TestApercu(unittest.TestCase):

    def test_sans_piece_on_ne_peut_pas_creer(self):
        vm = _vm()
        vm.set_mode(u'pieces')
        vm.PiecesVM.tout_decocher()
        vm.set_mode(u'apercu')
        self.assertFalse(vm.ApercuVM.PeutCreer)
        self.assertIn(u'pièce', vm.ApercuVM.Avertissement)

    def test_l_apercu_montre_les_jeux_et_leurs_feuilles(self):
        vm = _vm()
        vm.DossierVM.Type = u'PC'
        vm.set_mode(u'apercu')
        jeux = [l for l in vm.ApercuVM.Lignes if l.EstJeu]
        self.assertEqual(len(jeux), len(vm.PiecesVM.retenues()))
        self.assertTrue(len(vm.ApercuVM.Lignes) > len(jeux))

    def test_tout_existant_bloque_la_creation_et_le_dit(self):
        vm = _vm()
        vm.set_mode(u'pieces')
        for piece in list(vm.PiecesVM.Pieces):
            piece.Coche = False
        list(vm.PiecesVM.Pieces)[0].Coche = True
        vm.set_mode(u'apercu')
        numeros = [f.numero for j in vm.ApercuVM.plan().jeux
                   for f in j.feuilles]
        vm2 = _vm(numeros=numeros)
        vm2.set_mode(u'pieces')
        for piece in list(vm2.PiecesVM.Pieces):
            piece.Coche = False
        list(vm2.PiecesVM.Pieces)[0].Coche = True
        vm2.set_mode(u'apercu')
        self.assertFalse(vm2.ApercuVM.PeutCreer)
        self.assertIn(u'existent déjà', vm2.ApercuVM.Avertissement)


class TestLancer(unittest.TestCase):

    def test_cree_exactement_le_plan_affiche(self):
        maquette = _Maquette()
        vm = _vm(maquette=maquette)
        vm.DossierVM.Type = u'PC'
        vm.set_mode(u'apercu')
        attendu = vm.ApercuVM.plan()
        vm.lancer()
        self.assertEqual(len(maquette.cree), 1)
        self.assertEqual(maquette.cree[0][0].jeux, attendu.jeux)

    def test_le_cartouche_retenu_part_avec_le_plan(self):
        maquette = _Maquette()
        vm = _vm(maquette=maquette)
        vm.DossierVM.Cartouche = u'418_Cartouche : A3'
        vm.lancer()
        self.assertEqual(maquette.cree[0][1], 2)

    def test_aucun_cartouche_ne_passe_pas_d_identifiant(self):
        maquette = _Maquette()
        vm = _vm(maquette=maquette)
        vm.DossierVM.Cartouche = AUCUN_CARTOUCHE
        vm.lancer()
        self.assertIsNone(maquette.cree[0][1])

    def test_sans_piece_rien_n_est_ecrit_et_on_le_dit(self):
        maquette = _Maquette()
        vm = _vm(maquette=maquette)
        vm.set_mode(u'pieces')
        vm.PiecesVM.tout_decocher()
        message = vm.lancer()
        self.assertEqual(maquette.cree, [])
        self.assertIn(u'pièce', message)

    def test_lancer_replanifie_avant_d_ecrire(self):
        # Ne pas dépendre d'un passage par l'onglet Aperçu : la justesse ne
        # doit pas tenir à l'ordre des clics.
        maquette = _Maquette()
        vm = _vm(maquette=maquette)
        vm.lancer()                       # sans jamais ouvrir l'aperçu
        self.assertEqual(len(maquette.cree), 1)


class TestPersistance(unittest.TestCase):

    def test_le_type_et_le_cartouche_sont_retenus(self):
        store = _Store()
        vm = _vm(store=store)
        vm.DossierVM.Type = u'PD'
        vm.DossierVM.Cartouche = u'418_Cartouche : A3'
        self.assertEqual(_vm(store=store).DossierVM.Type, u'PD')
        self.assertEqual(_vm(store=store).DossierVM.Cartouche,
                         u'418_Cartouche : A3')

    def test_un_type_persiste_puis_grise_retombe_sur_un_actif(self):
        store = _Store()
        store.set('type', u'PCMI')
        self.assertTrue(catalogue.actif(_vm(store=store).DossierVM.Type))

    def test_un_cartouche_disparu_retombe_sur_le_premier(self):
        # Le cartouche retenu peut avoir été purgé du projet depuis.
        store = _Store()
        store.set('cartouche', u'418_Cartouche : A0')
        self.assertEqual(_vm(store=store).DossierVM.Cartouche,
                         u'418_Cartouche : A1')

    def test_un_projet_sans_cartouche_n_est_pas_une_erreur(self):
        vm = MainViewModel(config=_Store(), cartouches=[],
                           analyser=_Maquette().analyser)
        self.assertEqual(vm.DossierVM.Cartouche, AUCUN_CARTOUCHE)
        self.assertIsNone(vm.DossierVM.cartouche_id())

    def test_aucun_none_ecrit_dans_un_magasin_de_chaines(self):
        store = _Store()
        vm = _vm(store=store)
        vm.DossierVM.Cartouche = None
        self.assertNotIn(u'None', store._d.values())


if __name__ == '__main__':
    unittest.main()
