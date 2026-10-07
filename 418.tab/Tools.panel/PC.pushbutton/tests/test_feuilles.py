# -*- coding: utf-8 -*-
"""La planification : ce qui sera créé, décidé sans toucher à Revit."""
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

from lib.models.pieces import Piece
from lib.services import FeuillesService as service


def _piece(code, libelle, vues=()):
    return Piece(code, libelle, False, tuple(vues))


COUPE = _piece(u'PC3', u'Plan en coupe', (u'Section',))
NOTICE = _piece(u'PC4', u'Notice descriptive')


class TestNomJeu(unittest.TestCase):

    def test_le_code_vient_en_tete(self):
        self.assertEqual(service.nom_jeu(COUPE), u'PC3 - Plan en coupe')

    def test_les_caracteres_interdits_par_revit_sont_retires(self):
        nom = service.nom_jeu(_piece(u'PC4', u'Notice : {terrain}'))
        for interdit in u'\\:{}[]|;<>?`~':
            self.assertNotIn(interdit, nom)


class TestPlanifier(unittest.TestCase):

    def test_une_piece_sans_vue_recoit_une_feuille_nommee_par_elle(self):
        # Une notice se dépose sur une feuille comme le reste.
        plan = service.planifier([(NOTICE, [])])
        feuille = plan.jeux[0].feuilles[0]
        self.assertEqual(feuille.numero, u'PC4')
        self.assertEqual(feuille.nom, u'Notice descriptive')
        self.assertIsNone(feuille.vue)

    def test_une_seule_vue_donne_le_code_nu(self):
        plan = service.planifier([(COUPE, [(1, u'Coupe AA')])])
        feuille = plan.jeux[0].feuilles[0]
        self.assertEqual(feuille.numero, u'PC3')
        self.assertEqual(feuille.vue, 1)

    def test_plusieurs_vues_se_suffixent(self):
        plan = service.planifier([(COUPE, [(1, u'Coupe AA'), (2, u'Coupe BB'),
                                           (3, u'Coupe CC')])])
        numeros = [f.numero for f in plan.jeux[0].feuilles]
        self.assertEqual(numeros, [u'PC3.1', u'PC3.2', u'PC3.3'])

    def test_la_feuille_porte_le_titre_contractuel_pas_le_nom_de_la_vue(self):
        # L'instructeur cherche « Plan en coupe », pas « Coupe AA ». Trois
        # feuilles de PC3 portent le même nom et se distinguent par leur
        # numéro — c'est la lecture du bordereau.
        plan = service.planifier([(COUPE, [(1, u'Coupe AA'), (2, u'Coupe BB')])])
        noms = [f.nom for f in plan.jeux[0].feuilles]
        self.assertEqual(noms, [u'Plan en coupe', u'Plan en coupe'])

    def test_le_nom_de_la_vue_reste_disponible_pour_l_apercu(self):
        # Utile à la relecture — laquelle des coupes va sur PC3.2 — mais il
        # ne doit jamais atterrir dans le nom de la feuille.
        plan = service.planifier([(COUPE, [(1, u'Coupe AA'), (2, u'Coupe BB')])])
        self.assertEqual([f.vue_nom for f in plan.jeux[0].feuilles],
                         [u'Coupe AA', u'Coupe BB'])

    def test_une_piece_sans_vue_n_annonce_aucune_vue(self):
        plan = service.planifier([(NOTICE, [])])
        self.assertEqual(plan.jeux[0].feuilles[0].vue_nom, u'')

    def test_un_jeu_par_piece(self):
        plan = service.planifier([(COUPE, [(1, u'AA')]), (NOTICE, [])])
        self.assertEqual([j.nom for j in plan.jeux],
                         [u'PC3 - Plan en coupe', u'PC4 - Notice descriptive'])


class TestExistant(unittest.TestCase):
    """On ne touche jamais à ce qui est déjà dans la maquette."""

    def test_un_numero_deja_pris_est_signale_pas_recree(self):
        plan = service.planifier([(COUPE, [(1, u'AA')])],
                                 numeros_existants=[u'PC3'])
        self.assertTrue(plan.jeux[0].feuilles[0].existe)
        self.assertEqual(service.a_creer(plan), [])

    def test_un_jeu_deja_la_est_signale(self):
        plan = service.planifier([(COUPE, [(1, u'AA')])],
                                 jeux_existants=[u'PC3 - Plan en coupe'])
        self.assertTrue(plan.jeux[0].existe)

    def test_deux_pieces_ne_se_disputent_pas_un_numero(self):
        # Sans la mémoire des numéros attribués dans CE plan, deux pièces
        # homonymes produiraient deux feuilles du même numéro — Revit en
        # refuserait une, en silence.
        a = _piece(u'PC9', u'Un')
        b = _piece(u'PC9', u'Deux')
        plan = service.planifier([(a, []), (b, [])])
        self.assertFalse(plan.jeux[0].feuilles[0].existe)
        self.assertTrue(plan.jeux[1].feuilles[0].existe)

    def test_a_creer_ne_rend_que_le_manquant(self):
        plan = service.planifier(
            [(COUPE, [(1, u'AA'), (2, u'BB')])],
            numeros_existants=[u'PC3.1'])
        restantes = service.a_creer(plan)
        self.assertEqual([f.numero for f in restantes], [u'PC3.2'])


class TestResume(unittest.TestCase):

    def test_dit_ce_qui_a_ete_cree(self):
        texte = service.resume(3, 0, 2, [])
        self.assertIn(u'3 feuille(s)', texte)
        self.assertIn(u'2 jeu(x)', texte)

    def test_dit_ce_qui_a_manque(self):
        texte = service.resume(0, 0, 0, [u'PC3 : cartouche refusé'])
        self.assertIn(u'échec', texte)
        self.assertIn(u'cartouche refusé', texte)

    def test_rien_a_creer(self):
        self.assertEqual(service.resume(0, 0, 0, []), u'Rien à créer.')


class TestHorsRevit(unittest.TestCase):

    def test_creer_hors_revit_ne_leve_pas(self):
        plan = service.planifier([(NOTICE, [])])
        feuilles, jeux, echecs = service.creer(None, plan)
        self.assertEqual((feuilles, jeux), (0, 0))
        self.assertTrue(echecs)


if __name__ == '__main__':
    unittest.main()
