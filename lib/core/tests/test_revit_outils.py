# -*- coding: utf-8 -*-
"""Tests du catalogue d'outils Revit. Aucun réseau, aucun Revit."""
from __future__ import unicode_literals
import json
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))  # -> lib
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)

from core import revit_outils

# Aucune transaction derrière ces routes : rien à annuler après coup, et
# sync_with_central pousse en plus sur le central. execute_code exécute de
# l'IronPython arbitraire et peut se sortir lui-même de toute transaction.
# Les rouvrir demande une décision explicite, pas un ajout de ligne distrait.
INTERDITES = ('execute_code', 'open_document', 'close_document',
              'save_document', 'sync_with_central')

# Écriture autorisée : chacune pose une transaction nommée, Ctrl+Z la défait.
ECRITURE_ADMISE = ('place_family', 'color_splash', 'clear_colors')


class TestCatalogue(unittest.TestCase):
    def test_aucune_route_irreversible(self):
        routes = [entree[1] for entree in revit_outils.CATALOGUE]
        for interdite in INTERDITES:
            for route in routes:
                self.assertNotIn(interdite, route,
                                 'route irréversible exposée : ' + route)

    def test_les_trois_routes_annulables_sont_la(self):
        routes = ' '.join(entree[1] for entree in revit_outils.CATALOGUE)
        for admise in ECRITURE_ADMISE:
            self.assertIn(admise, routes, admise)

    def test_une_route_qui_ecrit_le_dit_dans_sa_description(self):
        # Le modèle ne lit que la description : si elle ne distingue pas
        # regarder de modifier, il colorera la maquette pour « voir ».
        for nom, route, _m, description, _s in revit_outils.CATALOGUE:
            if any(admise in route for admise in ECRITURE_ADMISE):
                self.assertIn('MODIFIE', description, nom)

    def test_noms_uniques_et_prefixes(self):
        noms = [entree[0] for entree in revit_outils.CATALOGUE]
        self.assertEqual(len(noms), len(set(noms)))
        for nom in noms:
            self.assertTrue(nom.startswith('revit_'), nom)

    def test_schemas_utilisables_par_un_client(self):
        for outil in revit_outils.outils():
            self.assertTrue(outil['nom'])
            self.assertTrue(outil['description'])
            self.assertEqual(outil['parametres'].get('type'), 'object')
            # Sans 'properties', le backend refuse le schéma.
            self.assertIsInstance(outil['parametres'].get('properties'), dict)

    def test_get_sans_parametres_post_avec(self):
        for nom, _route, methode, _d, schema in revit_outils.CATALOGUE:
            if methode == 'GET':
                self.assertEqual(schema['properties'], {}, nom)


class TestExecution(unittest.TestCase):
    def setUp(self):
        self.appels = []
        self._vrai = revit_outils._appeler
        revit_outils._appeler = self._faux

    def tearDown(self):
        revit_outils._appeler = self._vrai

    def _faux(self, route, methode, corps, timeout=None):
        self.appels.append((route, methode, corps))
        return json.dumps({'ok': True}, ensure_ascii=False)

    def test_outil_inconnu_rend_une_erreur_lisible(self):
        sortie = json.loads(revit_outils.executer('revit_inexistant'))
        self.assertIn('erreur', sortie)
        self.assertEqual(self.appels, [])

    def test_appel_get_ne_porte_pas_de_corps(self):
        revit_outils.executer('revit_status')
        route, methode, corps = self.appels[0]
        self.assertEqual((route, methode), ('/status/', 'GET'))
        self.assertIsNone(corps)

    def test_arguments_transmis_au_post(self):
        revit_outils.executer('revit_list_families', {'contains': 'porte'})
        route, methode, corps = self.appels[0]
        self.assertEqual((route, methode), ('/list_families/', 'POST'))
        self.assertEqual(corps, {'contains': 'porte'})

    def test_arguments_non_dict_ignores(self):
        # Le modèle peut renvoyer n'importe quoi ; ça ne doit pas lever.
        revit_outils.executer('revit_status', 'nawak')
        self.assertIsNone(self.appels[0][2])

    def test_echec_reseau_devient_une_erreur_pour_le_modele(self):
        def casse(*_a, **_k):
            raise ValueError('socket fermée')
        revit_outils._appeler = casse
        sortie = json.loads(revit_outils.executer('revit_status'))
        self.assertIn('socket fermée', sortie['erreur'])


class TestTroncature(unittest.TestCase):
    def test_sortie_courte_intacte(self):
        self.assertEqual(revit_outils._tronquer('abc'), 'abc')

    def test_sortie_longue_coupee_et_annoncee(self):
        long = 'x' * (revit_outils.LIMITE_SORTIE + 500)
        coupe = revit_outils._tronquer(long)
        self.assertTrue(coupe.startswith('x' * revit_outils.LIMITE_SORTIE))
        self.assertIn('tronqué', coupe)
        # Le renvoi doit rester borné : c'est tout l'intérêt.
        self.assertLess(len(coupe), revit_outils.LIMITE_SORTIE + 300)

    def test_un_outil_sans_filtre_ne_se_fait_pas_conseiller_d_en_mettre(self):
        # revit_list_views a bouclé deux fois en vrai sur ce conseil absurde.
        long = 'x' * (revit_outils.LIMITE_SORTIE + 500)
        self.assertIn('aucun filtre', revit_outils._tronquer(long, False))
        self.assertIn('restreindre', revit_outils._tronquer(long, True))

    def test_le_conseil_suit_le_schema_de_l_outil(self):
        for nom, _r, _m, _d, schema in revit_outils.CATALOGUE:
            filtrable = bool(schema.get('properties'))
            attendu = 'restreindre' if filtrable else 'aucun filtre'
            self.assertIn(attendu, revit_outils._tronquer('y' * 99999,
                                                          filtrable), nom)


class TestDisponible(unittest.TestCase):
    def setUp(self):
        self._vrai = revit_outils._appeler
        self._base = revit_outils.routes418.base
        # Un serveur pyRevit joignable : c'est le cas nominal.
        revit_outils.routes418.base = lambda: 'http://127.0.0.1:48884'

    def tearDown(self):
        revit_outils._appeler = self._vrai
        revit_outils.routes418.base = self._base

    def _repond(self, charge):
        revit_outils._appeler = lambda *a, **k: charge

    def test_sans_serveur_pyrevit_on_dit_quoi_faire(self):
        # Pas d'erreur réseau : il n'y a rien à joindre, et la sortie est une
        # case à cocher dans pyRevit — l'utilisateur doit pouvoir la trouver.
        revit_outils.routes418.base = lambda: ''
        ouvert, raison = revit_outils.disponible()
        self.assertFalse(ouvert)
        self.assertIn('Routes', raison)

    def test_document_ouvert(self):
        self._repond(json.dumps({'revit_available': True}))
        self.assertEqual(revit_outils.disponible(), (True, ''))

    def test_revit_sans_document(self):
        self._repond(json.dumps({'revit_available': False}))
        ouvert, raison = revit_outils.disponible()
        self.assertFalse(ouvert)
        self.assertIn('document', raison.lower())

    def test_serveur_muet(self):
        def casse(*_a, **_k):
            raise ValueError('connexion refusée')
        revit_outils._appeler = casse
        ouvert, raison = revit_outils.disponible()
        self.assertFalse(ouvert)
        self.assertIn('injoignable', raison.lower())

    def test_reponse_illisible(self):
        self._repond('<html>pas du json</html>')
        ouvert, raison = revit_outils.disponible()
        self.assertFalse(ouvert)
        self.assertTrue(raison)


if __name__ == '__main__':
    unittest.main()
