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


class TestEffacementCible(_Bac):
    """Effacer une clé ne doit jamais en effacer une autre."""

    def setUp(self):
        _Bac.setUp(self)
        os.environ.pop('ANTHROPIC_API_KEY', None)
        secrets.poser_cle('sk-aaa', 'openai')
        secrets.poser_cle('sk-ant-bbb', 'anthropic')

    def test_un_seul_fournisseur(self):
        self.assertTrue(secrets.oublier_cle('anthropic'))
        self.assertEqual('', secrets.cle('anthropic'))
        # L'autre tient : on peut rester branché à plusieurs maisons.
        self.assertEqual('sk-aaa', secrets.cle('openai'))

    def test_sans_argument_efface_tout(self):
        self.assertTrue(secrets.oublier_cle())
        self.assertEqual('', secrets.cle('openai'))
        self.assertEqual('', secrets.cle('anthropic'))

    def test_un_fournisseur_inconnu_n_efface_rien(self):
        # `_fiche()` retomberait sur OpenAI : une coquille effacerait la
        # mauvaise clé, sans rien dire.
        self.assertFalse(secrets.oublier_cle('anthropc'))
        self.assertEqual('sk-aaa', secrets.cle('openai'))
        self.assertEqual('sk-ant-bbb', secrets.cle('anthropic'))


class TestMaisonParPrefixe(_Bac):
    """Une clé mal adressée part au mauvais serveur, qui répond 401 sans
    dire pourquoi. Le préfixe, lui, est sans appel."""

    def setUp(self):
        _Bac.setUp(self)
        os.environ.pop('ANTHROPIC_API_KEY', None)

    def test_poser_rend_le_fournisseur_retenu(self):
        self.assertEqual('openai', secrets.poser_cle('sk-zzz'))
        self.assertEqual('anthropic',
                         secrets.poser_cle('sk-ant-zzz', 'anthropic'))

    def test_une_cle_ant_demandee_chez_openai_va_chez_anthropic(self):
        # Le défaut vécu : le volet n'envoyait pas de fournisseur, donc tout
        # atterrissait dans la case OpenAI.
        self.assertEqual('anthropic', secrets.poser_cle('sk-ant-zzz', 'openai'))
        self.assertEqual('', secrets.cle('openai'))
        self.assertEqual('sk-ant-zzz', secrets.cle('anthropic'))

    def test_une_cle_openai_n_est_PAS_deplacee(self):
        # `sk-` tout court ne prouve rien : beaucoup de maisons l'emploient.
        self.assertEqual('openai', secrets.poser_cle('sk-proj-zzz', 'openai'))
        self.assertEqual('sk-proj-zzz', secrets.cle('openai'))

    def test_une_valeur_vide_ne_range_rien(self):
        self.assertEqual('', secrets.poser_cle('  '))


class TestReparer(_Bac):
    """Les clés déjà mal rangées se remettent seules en place."""

    def setUp(self):
        _Bac.setUp(self)
        os.environ.pop('ANTHROPIC_API_KEY', None)

    def _ecrire_brut(self, charge):
        # On contourne `poser_cle` exprès : on reproduit le fichier tel que
        # l'ancienne version l'a laissé sur les postes.
        secrets._ecrire(charge)

    def test_une_cle_ant_dans_la_case_openai_est_deplacee(self):
        self._ecrire_brut({'cle': 'sk-ant-zzz'})
        self.assertEqual(['openai -> anthropic'], secrets.reparer())
        self.assertEqual('', secrets.cle('openai'))
        self.assertEqual('sk-ant-zzz', secrets.cle('anthropic'))

    def test_rien_a_faire_ne_touche_a_rien(self):
        self._ecrire_brut({'cle': 'sk-zzz', 'cle_anthropic': 'sk-ant-zzz'})
        self.assertEqual([], secrets.reparer())
        self.assertEqual('sk-zzz', secrets.cle('openai'))
        self.assertEqual('sk-ant-zzz', secrets.cle('anthropic'))

    def test_une_cle_anthropic_deja_posee_n_est_PAS_ecrasee(self):
        # Celle-là a été posée exprès ; la mal rangée reste où elle est
        # plutôt que de détruire une clé valide.
        self._ecrire_brut({'cle': 'sk-ant-vieille',
                           'cle_anthropic': 'sk-ant-bonne'})
        self.assertEqual([], secrets.reparer())
        self.assertEqual('sk-ant-bonne', secrets.cle('anthropic'))

    def test_un_fichier_vide_ne_leve_pas(self):
        self.assertEqual([], secrets.reparer())



if __name__ == '__main__':
    unittest.main()
