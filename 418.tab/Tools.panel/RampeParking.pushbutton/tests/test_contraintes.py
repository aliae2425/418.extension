# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division
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

from lib.services import contraintes


# ----------------------------------------------------------------------
# Doublures : le service ne voit de Revit que ce qu'il appelle réellement.
# ----------------------------------------------------------------------

class FauxNiveau(object):
    """`Level` : un nom et une élévation en PIEDS (unités internes Revit)."""

    def __init__(self, nom, elevation_pieds, parametres=None):
        self.Name = nom
        self.Elevation = elevation_pieds
        self.Parameters = list(parametres or [])


class FauxParametre(object):
    def __init__(self, nom, valeur_affichee=None, texte=None):
        self.Definition = type('Def', (object,), {'Name': nom})()
        self._valeur = valeur_affichee
        self._texte = texte

    def AsValueString(self):
        return self._valeur

    def AsString(self):
        return self._texte


class TestNombre(unittest.TestCase):
    """La saisie vient d'un TextBox : virgule décimale et champ vide compris."""

    def test_virgule_acceptee(self):
        self.assertAlmostEqual(contraintes.nombre('3,20'), 3.20)

    def test_point_accepte(self):
        self.assertAlmostEqual(contraintes.nombre(' 3.20 '), 3.20)

    def test_vide_et_texte_donnent_none(self):
        for saisie in ('', '   ', 'abc', None):
            self.assertIsNone(contraintes.nombre(saisie))

    def test_zero_et_negatif_donnent_none(self):
        # Une hauteur nulle ou négative n'a pas de sens et ferait diviser
        # par zéro plus loin.
        self.assertIsNone(contraintes.nombre('0'))
        self.assertIsNone(contraintes.nombre('-2'))


class TestPente(unittest.TestCase):

    def test_pente_nominale(self):
        self.assertAlmostEqual(contraintes.pente_pct(3.0, 20.0), 15.0)

    def test_termes_manquants(self):
        self.assertIsNone(contraintes.pente_pct(None, 20.0))
        self.assertIsNone(contraintes.pente_pct(3.0, None))
        self.assertIsNone(contraintes.pente_pct(3.0, 0))


class TestVerdict(unittest.TestCase):
    """Les BORNES, parce que c'est là que les seuils réglementaires se
    trompent : 15 est conforme, 15,1 est seulement toléré."""

    def test_bornes_inclusives(self):
        self.assertEqual(contraintes.verdict(15.0)[0], 'ok')
        self.assertEqual(contraintes.verdict(17.0)[0], 'warning')
        self.assertEqual(contraintes.verdict(20.0)[0], 'warning')

    def test_juste_au_dessus_des_bornes(self):
        self.assertEqual(contraintes.verdict(15.01)[0], 'warning')
        self.assertEqual(contraintes.verdict(20.01)[0], 'error')

    def test_bruit_de_conversion_absorbe(self):
        # 3,00 m repassés par les pieds Revit donnent 15,00000005 % : il
        # faut « conforme », pas « toléré », sinon la fenêtre affiche
        # « 15,0 % — toléré ».
        self.assertEqual(contraintes.verdict(15.00000005)[0], 'ok')
        # Mais l'arrondi ne doit pas avaler un vrai dépassement.
        self.assertEqual(contraintes.verdict(15.006)[0], 'warning')

    def test_libelles_distincts_entre_17_et_20(self):
        self.assertNotEqual(contraintes.verdict(16.0)[1],
                            contraintes.verdict(19.0)[1])

    def test_sans_pente(self):
        self.assertEqual(contraintes.verdict(None), ('', ''))


class TestUrlToolbox(unittest.TestCase):

    def test_contrat_des_trois_parametres(self):
        url = contraintes.url_toolbox(3.2, 3.0, 15.0)
        self.assertEqual(
            url, contraintes.BASE_TOOLBOX + '?h=3.20&w=3.00&p=15.00')

    def test_valeurs_absentes_omises(self):
        # La page web garde ses propres défauts pour ce qu'on ne dit pas.
        self.assertEqual(contraintes.url_toolbox(3.2),
                         contraintes.BASE_TOOLBOX + '?h=3.20')

    def test_sans_rien_url_nue(self):
        self.assertEqual(contraintes.url_toolbox(), contraintes.BASE_TOOLBOX)

    def test_valeurs_non_numeriques_ignorees(self):
        self.assertEqual(contraintes.url_toolbox('', None, 0),
                         contraintes.BASE_TOOLBOX)


class TestParametresLisibles(unittest.TestCase):

    def test_tri_par_nom_insensible_a_la_casse(self):
        element = FauxNiveau('N', 0, [
            FauxParametre('Zone', valeur_affichee='A'),
            FauxParametre('altitude', valeur_affichee='0,00'),
        ])
        noms = [nom for nom, _ in contraintes.parametres_lisibles(element)]
        self.assertEqual(noms, ['altitude', 'Zone'])

    def test_repli_sur_asstring_pour_les_textes(self):
        element = FauxNiveau('N', 0, [FauxParametre('Commentaires', texte='RAS')])
        self.assertEqual(contraintes.parametres_lisibles(element),
                         [('Commentaires', 'RAS')])

    def test_parametre_illisible_ignore_sans_planter(self):
        casse = FauxParametre('X')
        del casse.Definition
        element = FauxNiveau('N', 0, [casse, FauxParametre('Ok', 'v')])
        self.assertEqual(contraintes.parametres_lisibles(element),
                         [('Ok', 'v')])


class TestLireSansRevit(unittest.TestCase):
    """Hors Revit, `Level` vaut None : `lire` doit rendre l'aide de sélection
    au lieu de lever. C'est aussi le garde-fou du cas « rien de sélectionné ».
    """

    def test_selection_vide(self):
        resultat = contraintes.lire([], None)
        self.assertIsNone(resultat.Denivelee)
        self.assertEqual(resultat.Avertissement, contraintes.AIDE_SELECTION)

    def test_none_filtres(self):
        self.assertEqual(contraintes.lire([None, None], None).Avertissement,
                         contraintes.AIDE_SELECTION)


class TestDeniveleeEntreNiveaux(unittest.TestCase):
    """`_depuis_niveaux` est testable directement : c'est là que se joue la
    conversion pieds -> mètres et le choix du couple bas/haut."""

    def test_conversion_et_ordre(self):
        # 10,50 pieds = 3,2004 m. Niveaux donnés dans le désordre exprès.
        resultat = contraintes._depuis_niveaux(
            [FauxNiveau('R+1', 10.5), FauxNiveau('RDC', 0.0)])
        self.assertAlmostEqual(resultat.Denivelee, 3.2004, places=4)
        self.assertIn('RDC', resultat.Source)
        self.assertIn('R+1', resultat.Source)
        self.assertEqual(resultat.Avertissement, '')

    def test_plus_de_deux_niveaux_avertit(self):
        resultat = contraintes._depuis_niveaux([
            FauxNiveau('RDC', 0.0), FauxNiveau('R+1', 10.0),
            FauxNiveau('R+2', 20.0)])
        self.assertAlmostEqual(resultat.Denivelee, 20.0 * 0.3048, places=4)
        self.assertIn('3 niveaux', resultat.Avertissement)

    def test_pente_bout_en_bout(self):
        # Le parcours réel : deux niveaux -> dénivelée -> pente -> verdict.
        resultat = contraintes._depuis_niveaux(
            [FauxNiveau('RDC', 0.0), FauxNiveau('R-1', -9.84252)])  # -3,00 m
        pente = contraintes.pente_pct(resultat.Denivelee, 20.0)
        self.assertAlmostEqual(pente, 15.0, places=3)
        self.assertEqual(contraintes.verdict(pente)[0], 'ok')


if __name__ == '__main__':
    unittest.main()
