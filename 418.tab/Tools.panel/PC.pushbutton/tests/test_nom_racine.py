# -*- coding: utf-8 -*-
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

from lib.services.NomRacineService import MOTIF_DEFAUT, resoudre, infos_projet
from core.token_expander import sans_jetons_restants

INFOS = {u'projet_numero': u'2431', u'projet_nom': u'Maison Dupont'}


class TestResoudre(unittest.TestCase):

    def test_le_motif_par_defaut(self):
        self.assertEqual(resoudre(MOTIF_DEFAUT, u'PC', INFOS),
                         u'2431 - Maison Dupont - PC')

    def test_un_jeton_vide_disparait_avec_son_separateur(self):
        # La doctrine de nommage du dépôt : jamais de « {…} » brut en sortie,
        # et pas de « 2431 -  - PC » non plus.
        self.assertEqual(
            resoudre(MOTIF_DEFAUT, u'PC', {u'projet_numero': u'2431'}),
            u'2431 - PC')

    def test_un_jeton_inconnu_ne_survit_pas(self):
        self.assertEqual(resoudre(u'{inexistant}-{type}', u'DP', INFOS),
                         u'DP')

    def test_tous_les_jetons_vides_laissent_le_type(self):
        # Mieux vaut « PC » qu'un dossier sans titre.
        self.assertEqual(resoudre(u'{projet_nom}', u'PC', {}), u'PC')

    def test_les_caracteres_interdits_sont_retires(self):
        nom = resoudre(u'{projet_nom}', u'PC',
                       {u'projet_nom': u'Lot 3/4 : tranche*1'})
        for interdit in u'\\/:*?"<>|':
            self.assertNotIn(interdit, nom)

    def test_le_motif_absent_retombe_sur_le_defaut(self):
        self.assertEqual(resoudre(u'', u'PC', INFOS),
                         u'2431 - Maison Dupont - PC')

    def test_les_jetons_de_date_du_socle_marchent(self):
        self.assertNotIn(u'{annee}', resoudre(u'{annee} - {type}', u'PC',
                                              INFOS))


class TestSansJetonsRestants(unittest.TestCase):

    def test_retire_le_jeton_et_recolle(self):
        self.assertEqual(sans_jetons_restants(u'2431 - {x} - PC'),
                         u'2431 - PC')

    def test_ne_touche_pas_a_un_texte_propre(self):
        self.assertEqual(sans_jetons_restants(u'2431 - Maison - PC'),
                         u'2431 - Maison - PC')

    def test_chaine_vide(self):
        self.assertEqual(sans_jetons_restants(u''), u'')


class TestInfosProjet(unittest.TestCase):

    def test_hors_revit_les_infos_sont_vides_sans_lever(self):
        infos = infos_projet(None)
        self.assertEqual(infos[u'projet_numero'], u'')
        self.assertEqual(infos[u'projet_nom'], u'')


if __name__ == '__main__':
    unittest.main()
