# -*- coding: utf-8 -*-
"""Tests du pont chat ↔ outils Revit. Aucun réseau, aucun Revit.

Le catalogue n'est plus écrit ici : il vient de ``/418/outils/``. Ces tests
le simulent, et vérifient surtout ce qui a cassé en vrai — un chemin en dur
qui diverge, un échec caché dans un HTTP 200, une sortie non tronquée.
"""
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

CATALOGUE = {'outils': [
    {'nom': 'revit_etat', 'description': 'état', 'ecrit': False,
     'irreversible': False,
     'parametres': {'type': 'object', 'properties': {}}},
    {'nom': 'revit_familles', 'description': 'familles', 'ecrit': False,
     'irreversible': False,
     'parametres': {'type': 'object',
                    'properties': {'categorie': {'type': 'string'}}}},
    {'nom': 'revit_executer_code', 'description': 'DANGER', 'ecrit': True,
     'irreversible': True,
     'parametres': {'type': 'object',
                    'properties': {'code': {'type': 'string'}}}},
]}


class _Pont(unittest.TestCase):
    """Base commune : serveur joignable, catalogue servi, rien en vol."""

    def setUp(self):
        self.appels = []
        self._vrai = revit_outils._appeler
        self._base = revit_outils.routes418.base
        revit_outils.routes418.base = lambda: 'http://127.0.0.1:48884'
        revit_outils.oublier_catalogue()
        revit_outils._appeler = self._faux

    def tearDown(self):
        revit_outils._appeler = self._vrai
        revit_outils.routes418.base = self._base
        revit_outils.oublier_catalogue()
        revit_outils._echec['texte'] = ''

    def _faux(self, route, methode, corps, timeout=None):
        self.appels.append((route, methode, corps))
        if route == '/418/outils/':
            return json.dumps(CATALOGUE, ensure_ascii=False)
        return json.dumps({'ok': True}, ensure_ascii=False)


class TestCatalogueServi(_Pont):
    def test_le_catalogue_vient_du_serveur(self):
        # Il n'est plus écrit à la main : c'est ce qui avait diverge deux fois.
        noms = [o['nom'] for o in revit_outils.outils()]
        self.assertEqual(noms, ['revit_etat', 'revit_familles',
                                'revit_executer_code'])

    def test_il_n_est_demande_qu_une_fois(self):
        revit_outils.outils()
        revit_outils.outils()
        self.assertEqual(self.appels.count(('/418/outils/', 'GET', None)), 1)

    def test_les_irreversibles_viennent_du_serveur(self):
        self.assertEqual(revit_outils.irreversibles(),
                         ('revit_executer_code',))

    def test_un_serveur_muet_donne_un_catalogue_vide(self):
        # Pas de tools envoyés = le chat marche comme avant, sans outils.
        revit_outils.oublier_catalogue()
        revit_outils._appeler = lambda *a, **k: (_ for _ in ()).throw(
            ValueError('injoignable'))
        self.assertEqual(revit_outils.outils(), [])


class TestExecution(_Pont):
    def test_outil_inconnu_rend_une_erreur_lisible(self):
        sortie = json.loads(revit_outils.executer('revit_inexistant'))
        self.assertIn('erreur', sortie)
        # Le catalogue a été demandé, mais aucun outil appelé.
        self.assertNotIn('/418/outil/revit_inexistant',
                         [a[0] for a in self.appels])

    def test_l_outil_est_appele_sur_sa_route(self):
        revit_outils.executer('revit_familles', {'categorie': 'Portes'})
        route, methode, corps = self.appels[-1]
        self.assertEqual((route, methode),
                         ('/418/outil/revit_familles', 'POST'))
        self.assertEqual(corps, {'categorie': 'Portes'})

    def test_arguments_non_dict_ignores(self):
        # Le modèle peut renvoyer n'importe quoi ; ça ne doit pas lever.
        revit_outils.executer('revit_etat', 'nawak')
        self.assertEqual(self.appels[-1][2], {})

    def test_echec_reseau_devient_une_erreur_pour_le_modele(self):
        revit_outils.outils()          # catalogue d'abord
        def casse(*_a, **_k):
            raise ValueError('socket fermée')
        revit_outils._appeler = casse
        sortie = json.loads(revit_outils.executer('revit_etat'))
        self.assertIn('socket fermée', sortie['erreur'])

    def test_un_echec_cache_dans_un_200_est_retenu(self):
        # Plusieurs routes rendent {"erreur": …} sans toucher au code HTTP :
        # sans ce contrôle, l'architecte ne voyait jamais ces échecs-là.
        revit_outils.outils()
        revit_outils._appeler = lambda *a, **k: json.dumps(
            {'erreur': 'aucune vue active'})
        revit_outils.executer('revit_etat')
        self.assertIn('aucune vue active', revit_outils.dernier_echec())

    def test_l_echec_ne_se_lit_qu_une_fois(self):
        revit_outils._echec['texte'] = 'x'
        self.assertEqual(revit_outils.dernier_echec(), 'x')
        self.assertEqual(revit_outils.dernier_echec(), '')


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


class TestDisponible(_Pont):
    def _repond(self, charge):
        revit_outils._appeler = lambda *a, **k: charge

    def test_sans_serveur_pyrevit_on_dit_quoi_faire(self):
        # Pas d'erreur réseau : il n'y a rien à joindre, et la sortie est une
        # case à cocher dans pyRevit — l'utilisateur doit pouvoir la trouver.
        revit_outils.routes418.base = lambda: ''
        ouvert, raison = revit_outils.disponible()
        self.assertFalse(ouvert)
        self.assertIn('Routes', raison)

    def test_le_controle_interroge_la_route_d_etat(self):
        revit_outils.disponible()
        self.assertEqual(self.appels[-1][0], '/418/etat/')

    def test_document_ouvert(self):
        self._repond(json.dumps({'revit_disponible': True}))
        self.assertEqual(revit_outils.disponible(), (True, ''))

    def test_revit_sans_document(self):
        self._repond(json.dumps({'revit_disponible': False}))
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
