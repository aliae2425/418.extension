# -*- coding: utf-8 -*-
"""Tests du registre d'outils et du catalogue qu'il dérive.

Les gestionnaires eux-mêmes touchent l'API Revit : ils ne se testent qu'en
vrai (cf. TESTS.md). Ce qui se teste ici, c'est la déclaration — et c'est
elle qui a cassé deux fois quand elle était tenue en double.
"""
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from rvt import registre


class TestDeclaration(unittest.TestCase):
    def setUp(self):
        self._sauve = dict(registre.OUTILS)
        registre.vider()

    def tearDown(self):
        registre.vider()
        registre.OUTILS.update(self._sauve)

    def test_le_prefixe_est_pose_une_seule_fois(self):
        registre.outil('vues', 'les vues')(lambda doc, donnees=None: None)
        self.assertIn('revit_vues', registre.OUTILS)

    def test_un_nom_deja_prefixe_n_est_pas_double(self):
        registre.outil('revit_vues', 'les vues')(lambda doc, donnees=None: None)
        self.assertIn('revit_vues', registre.OUTILS)
        self.assertNotIn('revit_revit_vues', registre.OUTILS)

    def test_deux_declarations_du_meme_nom_levent(self):
        # Un doublon silencieux, c'est un outil qui en masque un autre.
        registre.outil('a', 'x')(lambda doc, donnees=None: None)
        try:
            registre.outil('a', 'y')(lambda doc, donnees=None: None)
            self.fail('aurait dû lever')
        except ValueError as e:
            self.assertIn('deux fois', '{0}'.format(e))

    def test_un_besoin_inconnu_leve(self):
        try:
            registre.outil('a', 'x', besoins=('uiapp',))(lambda: None)
            self.fail('aurait dû lever')
        except ValueError as e:
            self.assertIn('besoin inconnu', '{0}'.format(e))

    def test_irreversible_implique_ecrit(self):
        registre.outil('a', 'x', irreversible=True)(
            lambda doc, donnees=None: None)
        self.assertTrue(registre.OUTILS['revit_a'].ecrit)
        self.assertTrue(registre.OUTILS['revit_a'].irreversible)


class TestSchema(unittest.TestCase):
    def setUp(self):
        self._sauve = dict(registre.OUTILS)
        registre.vider()

    def tearDown(self):
        registre.vider()
        registre.OUTILS.update(self._sauve)

    def test_schema_minimal_utilisable_par_un_fournisseur(self):
        registre.outil('a', 'x')(lambda doc, donnees=None: None)
        schema = registre.OUTILS['revit_a'].schema
        self.assertEqual(schema['type'], 'object')
        # Sans « properties », le backend refuse le schéma.
        self.assertEqual(schema['properties'], {})
        self.assertNotIn('required', schema)

    def test_les_requis_passent_dans_le_schema(self):
        registre.outil('a', 'x', proprietes={'n': {'type': 'string'}},
                       requis=('n',))(lambda doc, donnees=None: None)
        self.assertEqual(registre.OUTILS['revit_a'].schema['required'], ['n'])


class TestCatalogue(unittest.TestCase):
    def setUp(self):
        self._sauve = dict(registre.OUTILS)
        registre.vider()
        registre.outil('zz_lire', 'lit')(lambda doc, donnees=None: None)
        registre.outil('aa_ecrit', 'écrit', ecrit=True)(
            lambda doc, donnees=None: None)
        registre.outil('aa_casse', 'casse', irreversible=True)(
            lambda doc, donnees=None: None)

    def tearDown(self):
        registre.vider()
        registre.OUTILS.update(self._sauve)

    def test_la_lecture_vient_avant_l_ecriture(self):
        # L'ordre fait office de hiérarchie implicite pour le modèle.
        noms = [o['nom'] for o in registre.catalogue()]
        self.assertEqual(noms.index('revit_zz_lire'), 0)
        self.assertEqual(noms[-1], 'revit_aa_casse')

    def test_chaque_entree_porte_ce_que_le_chat_attend(self):
        for entree in registre.catalogue():
            for cle in ('nom', 'description', 'parametres', 'ecrit',
                        'irreversible'):
                self.assertIn(cle, entree)

    def test_les_irreversibles_sont_listables(self):
        self.assertEqual(registre.irreversibles(), ('revit_aa_casse',))


class TestOutilsReels(unittest.TestCase):
    """Le vrai catalogue, chargé depuis rvt/outils/. Hors Revit, DB est None
    mais les DÉCLARATIONS s'exécutent quand même : c'est tout l'intérêt de
    les avoir sorties du corps des fonctions."""

    @classmethod
    def setUpClass(cls):
        import rvt
        rvt.charger_outils()

    def test_le_catalogue_n_est_pas_vide(self):
        self.assertGreater(len(registre.catalogue()), 15)

    def test_tous_les_noms_sont_prefixes_et_uniques(self):
        noms = [o['nom'] for o in registre.catalogue()]
        self.assertEqual(len(noms), len(set(noms)))
        for nom in noms:
            self.assertTrue(nom.startswith('revit_'), nom)

    def test_un_outil_qui_ecrit_le_dit_dans_sa_description(self):
        # Le modèle ne lit que la description : si elle ne distingue pas
        # regarder de modifier, il colorera la maquette pour « voir ».
        for entree in registre.catalogue():
            if entree['ecrit'] and not entree['irreversible']:
                self.assertIn('MODIFIE', entree['description'], entree['nom'])

    def test_un_outil_irreversible_crie_dans_sa_description(self):
        for entree in registre.catalogue():
            if entree['irreversible']:
                self.assertIn('DANGER', entree['description'], entree['nom'])
                self.assertIn('explicite', entree['description'], entree['nom'])

    def test_la_parite_avec_l_ancien_serveur_est_tenue(self):
        # Rien de ce que le chat savait faire ne doit avoir disparu.
        noms = set(o['nom'] for o in registre.catalogue())
        for attendu in ('revit_etat', 'revit_infos_maquette', 'revit_niveaux',
                        'revit_vue_active', 'revit_vues', 'revit_familles',
                        'revit_elements_de_la_vue', 'revit_colorer',
                        'revit_effacer_couleurs', 'revit_placer',
                        'revit_executer_code', 'revit_enregistrer',
                        'revit_synchroniser', 'revit_selection'):
            self.assertIn(attendu, noms, attendu)

    def test_les_manques_du_vendor_sont_combles(self):
        noms = set(o['nom'] for o in registre.catalogue())
        for neuf in ('revit_feuilles',            # noyées dans « other »
                     'revit_vues_hors_feuille',
                     'revit_lire_parametre',      # valeurs, avec leur unité
                     'revit_definir_parametre',   # écriture, impossible avant
                     'revit_details',
                     'revit_categories',
                     'revit_avertissements',
                     'revit_unites'):
            self.assertIn(neuf, noms, neuf)


if __name__ == '__main__':
    unittest.main()
