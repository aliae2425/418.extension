# -*- coding: utf-8 -*-
"""Le rangement des secrets, éprouvé hors Revit et hors %LOCALAPPDATA%."""
from __future__ import unicode_literals
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from harnais import secrets                                     # noqa: E402


class _Bac(unittest.TestCase):
    """Détourne LOCALAPPDATA vers un dossier jetable.

    Sans ça, les tests écriraient dans les vrais réglages de la machine —
    et effaceraient la clé de celui qui les lance.
    """

    def setUp(self):
        self._bac = tempfile.mkdtemp()
        self._avant = os.environ.get('LOCALAPPDATA')
        self._cle_avant = os.environ.get('OPENAI_API_KEY')
        os.environ['LOCALAPPDATA'] = self._bac
        os.environ.pop('OPENAI_API_KEY', None)

    def tearDown(self):
        for nom, valeur in (('LOCALAPPDATA', self._avant),
                            ('OPENAI_API_KEY', self._cle_avant)):
            if valeur is None:
                os.environ.pop(nom, None)
            else:
                os.environ[nom] = valeur
        shutil.rmtree(self._bac, ignore_errors=True)


class TestRangement(_Bac):

    def test_sans_rien_la_cle_est_vide(self):
        self.assertEqual('', secrets.cle())

    def test_poser_puis_relire(self):
        self.assertTrue(secrets.poser_cle('sk-essai'))
        self.assertEqual('sk-essai', secrets.cle())

    def test_les_espaces_sont_rognes(self):
        # Une clé collée depuis un navigateur traîne souvent un retour ligne.
        secrets.poser_cle('  sk-essai\n')
        self.assertEqual('sk-essai', secrets.cle())

    def test_poser_du_vide_ne_fait_rien(self):
        self.assertFalse(secrets.poser_cle(''))
        self.assertFalse(secrets.poser_cle('   '))
        self.assertFalse(secrets.poser_cle(None))
        self.assertEqual('', secrets.cle())

    def test_hors_du_depot(self):
        # Le point entier de ce module : data/ finit poussé.
        depot = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(secrets.__file__))))
        self.assertFalse(secrets.dossier().startswith(depot))


class TestPrecedence(_Bac):

    def test_lenvironnement_sert_de_repli(self):
        os.environ['OPENAI_API_KEY'] = 'sk-env'
        self.assertEqual('sk-env', secrets.cle())

    def test_le_reglage_gagne_sur_lenvironnement(self):
        # Taper /connect et ne rien voir changer parce qu'une variable
        # traîne serait incompréhensible.
        os.environ['OPENAI_API_KEY'] = 'sk-env'
        secrets.poser_cle('sk-reglage')
        self.assertEqual('sk-reglage', secrets.cle())

    def test_oublier_retombe_sur_lenvironnement(self):
        os.environ['OPENAI_API_KEY'] = 'sk-env'
        secrets.poser_cle('sk-reglage')
        self.assertTrue(secrets.oublier_cle())
        self.assertEqual('sk-env', secrets.cle())

    def test_oublier_ne_touche_pas_a_lenvironnement(self):
        # On n'a pas le droit d'effacer un réglage posé par l'IT.
        os.environ['OPENAI_API_KEY'] = 'sk-env'
        secrets.oublier_cle()
        self.assertEqual('sk-env', os.environ.get('OPENAI_API_KEY'))

    def test_oublier_deux_fois_ne_leve_pas(self):
        secrets.poser_cle('sk-x')
        self.assertTrue(secrets.oublier_cle())
        self.assertFalse(secrets.oublier_cle())


class TestRobustesse(_Bac):

    def test_un_fichier_illisible_ne_leve_pas(self):
        # Un JSON corrompu ne doit pas empêcher le volet de s'ouvrir.
        with open(os.path.join(secrets.dossier(), secrets.FICHIER), 'wb') as f:
            f.write(b'{pas du json')
        self.assertEqual('', secrets.cle())
        self.assertTrue(secrets.poser_cle('sk-neuve'))
        self.assertEqual('sk-neuve', secrets.cle())

    def test_les_autres_cles_du_fichier_survivent(self):
        # J7 y rangera des jetons OAuth : /logout ne doit pas les emporter.
        secrets.poser_cle('sk-x')
        charge = secrets._lire()
        charge['jeton'] = 'a-garder'
        secrets._ecrire(charge)
        secrets.oublier_cle()
        self.assertEqual('a-garder', secrets._lire().get('jeton'))


if __name__ == '__main__':
    unittest.main()
