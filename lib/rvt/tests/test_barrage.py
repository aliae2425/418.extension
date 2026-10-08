# -*- coding: utf-8 -*-
"""Le barrage des outils irréversibles, côté route.

Le serveur de routes pyRevit écoute sur ``0.0.0.0`` et n'authentifie rien.
Sans barrage, une page web ouverte dans n'importe quel onglet POSTe
``revit_executer_code`` en requête SIMPLE — ``Content-Type: text/plain``,
donc aucun préflight, donc aucun CORS pour l'arrêter. La réponse lui est
illisible, mais le code a déjà tourné dans Revit.

Ces tests ne touchent ni Revit ni le réseau : ils appellent ``_barrage``
avec de fausses requêtes.
"""
from __future__ import unicode_literals
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

import rvt                                                        # noqa: E402


class _Requete(object):
    def __init__(self, entetes=None):
        self.headers = entetes if entetes is not None else {}


class _Reponse(object):
    """Doublure de ``routes.make_response`` : pyRevit est absent hors Revit."""

    def __init__(self, data=None, status=200, headers=None):
        self.data = data
        self.status = status


class TestJeton(unittest.TestCase):

    def test_stable_dans_la_session(self):
        # Un jeton qui change à chaque lecture refuserait le volet lui-même.
        self.assertEqual(rvt.jeton(), rvt.jeton())

    def test_assez_long_pour_ne_pas_se_deviner(self):
        self.assertGreaterEqual(len(rvt.jeton()), 32)


class TestBarrage(unittest.TestCase):

    def setUp(self):
        self._vrai = rvt.routes
        # `_barrage` n'appelle `make_response` que sur le chemin du refus.
        rvt.routes = type(str('X'), (object,), {
            'make_response': staticmethod(_Reponse)})()

    def tearDown(self):
        rvt.routes = self._vrai

    def test_sans_jeton_cest_403(self):
        refus = rvt._barrage(_Requete(), 'revit_executer_code', {'code': 'x'})
        self.assertIsNotNone(refus)
        self.assertEqual(403, refus.status)

    def test_mauvais_jeton_cest_403(self):
        refus = rvt._barrage(_Requete({'X-418-Jeton': 'a' * 48}),
                             'revit_synchroniser', {})
        self.assertEqual(403, refus.status)

    def test_bon_jeton_laisse_passer(self):
        passe = rvt._barrage(_Requete({'X-418-Jeton': rvt.jeton()}),
                             'revit_synchroniser', {})
        self.assertIsNone(passe)

    def test_entete_en_minuscules_accepte(self):
        # Les en-têtes HTTP sont insensibles à la casse ; selon le serveur et
        # le client, la clé arrive dans un sens ou dans l'autre.
        passe = rvt._barrage(_Requete({'x-418-jeton': rvt.jeton()}),
                             'revit_enregistrer', {})
        self.assertIsNone(passe)

    def test_requete_sans_entetes_cest_403(self):
        # Une requête mal formée ne doit pas lever ici : elle doit être
        # refusée. Lever ferait un 500, que l'appelant lirait comme un bug
        # de l'outil plutôt que comme un refus.
        class _Nue(object):
            pass
        refus = rvt._barrage(_Nue(), 'revit_executer_code', {})
        self.assertEqual(403, refus.status)

    def test_jeton_vide_cest_403(self):
        # `hmac.compare_digest('', '')` est vrai : sans la garde `if presente`,
        # un en-tête vide passerait.
        refus = rvt._barrage(_Requete({'X-418-Jeton': ''}),
                             'revit_executer_code', {})
        self.assertEqual(403, refus.status)


class TestPerimetre(unittest.TestCase):
    """Le barrage ne vise QUE l'irréversible — la lecture reste ouverte."""

    def test_quatre_outils_irreversibles(self):
        import rvt.registre as registre
        rvt.charger_outils()
        noms = registre.irreversibles()
        self.assertIn('revit_executer_code', noms)
        self.assertIn('revit_synchroniser', noms)
        # Si ce compte bouge, c'est que quelqu'un a ajouté un outil
        # irréversible : qu'il relise ce fichier avant de le livrer.
        self.assertEqual(4, len(noms), 'irréversibles : {0}'.format(noms))


if __name__ == '__main__':
    unittest.main()
