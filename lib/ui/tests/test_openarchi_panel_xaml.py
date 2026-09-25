# -*- coding: utf-8 -*-
"""La grille du panneau OpenArchi : une ligne déclarée par ligne occupée.

Ajouter un bandeau en tête oblige à décaler tous les ``Grid.Row`` d'un cran,
à la main, dans quatre balises. En oublier un ne lève rien : WPF empile
silencieusement deux contrôles sur la même ligne, ou en pose un hors grille.
"""
from __future__ import unicode_literals
import os
import re
import sys
import unittest
import xml.etree.ElementTree as ET

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

PANNEAU = os.path.join(_LIB, 'ui', 'GUI', 'pages', 'OpenArchiPanel.xaml')

_WPF = '{http://schemas.microsoft.com/winfx/2006/xaml/presentation}'


class TestGrilleDuPanneau(unittest.TestCase):
    def setUp(self):
        self.racine = ET.parse(PANNEAU).getroot()
        self.grille = self.racine.find(_WPF + 'Grid')
        self.assertIsNotNone(self.grille, 'grille racine introuvable')

    def _lignes_declarees(self):
        definitions = self.grille.find(_WPF + 'Grid.RowDefinitions')
        return len(list(definitions))

    def _lignes_occupees(self):
        # Enfants DIRECTS seulement : un Grid.Row dans une grille imbriquée
        # parle d'une autre grille.
        rangs = []
        for enfant in self.grille:
            rang = enfant.get('Grid.Row')
            if rang is not None:
                rangs.append(int(rang))
        return rangs

    def test_chaque_rang_utilise_est_declare(self):
        declarees = self._lignes_declarees()
        for rang in self._lignes_occupees():
            self.assertLess(rang, declarees,
                            'Grid.Row={0} hors des {1} lignes déclarées'.format(
                                rang, declarees))

    def test_aucun_rang_partage(self):
        rangs = self._lignes_occupees()
        self.assertEqual(sorted(rangs), sorted(set(rangs)),
                         'deux contrôles empilés sur la même ligne')

    def test_aucune_ligne_declaree_pour_rien(self):
        self.assertEqual(sorted(self._lignes_occupees()),
                         list(range(self._lignes_declarees())))

    def _source(self):
        with open(PANNEAU, 'rb') as fichier:
            return re.sub(r'<!--.*?-->', '',
                          fichier.read().decode('utf-8'), flags=re.S)

    def test_le_richtextbox_vit_sous_un_gabarit_nomme(self):
        """Il ne doit jamais être posé en vrac dans la liste de messages :
        sa propriété Document refuse null, et le gabarit ne doit exister que
        quand MiseEnForme est vrai."""
        source = self._source()
        self.assertIn('x:Key="BulleRiche"', source)
        self.assertIn('x:Key="BulleBrute"', source)
        self.assertLess(source.index('x:Key="BulleRiche"'),
                        source.index('RichTextBox'))

    def test_la_bascule_passe_par_miseenforme(self):
        self.assertIn('Binding MiseEnForme', self._source())

    def test_l_etiquette_d_auteur_a_disparu(self):
        self.assertNotIn('Binding Auteur', self._source())

    def test_le_bandeau_d_alerte_est_en_tete(self):
        # Au-dessus de la conversation : c'est ce qui explique les réponses
        # sans outils, le lire après coup ne sert à rien.
        premier = [e for e in self.grille if e.get('Grid.Row') == '0']
        self.assertEqual(len(premier), 1)
        self.assertIn('AlerteVisible', premier[0].get('Visibility', ''))


if __name__ == '__main__':
    unittest.main()
