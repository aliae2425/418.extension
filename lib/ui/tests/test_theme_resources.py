# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import io
import os
import re
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)
_EXT = os.path.dirname(_LIB)
_RES = os.path.join(_LIB, 'ui', 'GUI', 'resources')

CLE = re.compile(r'x:Key="([^"]+)"')
DYNAMIQUE = re.compile(r'\{DynamicResource\s+([A-Za-z0-9_.]+)\s*\}')
COULEUR_EN_DUR = re.compile(r'="#[0-9A-Fa-f]{3,8}"')


def _lire(chemin):
    with io.open(chemin, encoding='utf-8') as f:
        return f.read()


def _sans_commentaires(texte):
    return re.sub(r'<!--.*?-->', '', texte, flags=re.S)


def _tous_les_xaml():
    for dossier, _, fichiers in os.walk(_EXT):
        if '.git' in dossier or '__pycache__' in dossier:
            continue
        for nom in fichiers:
            if nom.endswith('.xaml'):
                yield os.path.join(dossier, nom)


class TestRessourcesDeTheme(unittest.TestCase):
    """Un seul dictionnaire de STYLES, deux dictionnaires de COULEURS.

    Ce découpage n'est sûr que si deux invariants tiennent : aucune couleur
    en dur dans les styles, et les deux palettes exposent exactement les
    mêmes clés. Sinon un DynamicResource se résout dans un thème et pas
    dans l'autre — WPF n'émet alors aucune erreur, le contrôle est
    simplement rendu avec la valeur par défaut (typiquement du noir sur
    fond sombre).
    """

    def setUp(self):
        self.styles = _sans_commentaires(_lire(os.path.join(_RES, 'Styles.xaml')))
        self.clair = _sans_commentaires(_lire(os.path.join(_RES, 'Colors.xaml')))
        self.sombre = _sans_commentaires(_lire(os.path.join(_RES, 'ColorsDark.xaml')))

    def test_il_ny_a_plus_de_dictionnaire_de_styles_sombre(self):
        self.assertFalse(os.path.exists(os.path.join(_RES, 'StylesDark.xaml')),
                         u'StylesDark.xaml est revenu : les styles doivent '
                         u'rester uniques, seules les couleurs varient')

    def test_aucune_couleur_en_dur_dans_les_styles(self):
        trouvees = COULEUR_EN_DUR.findall(self.styles)
        self.assertEqual(trouvees, [],
                         u'couleurs littérales dans Styles.xaml : %s' % trouvees)

    def test_les_deux_palettes_exposent_les_memes_cles(self):
        clair = set(CLE.findall(self.clair))
        sombre = set(CLE.findall(self.sombre))
        self.assertEqual(clair - sombre, set(),
                         u'clés absentes de ColorsDark.xaml')
        self.assertEqual(sombre - clair, set(),
                         u'clés absentes de Colors.xaml')

    def test_chaque_dynamicresource_du_depot_est_defini(self):
        definies = set(CLE.findall(self.styles)) | set(CLE.findall(self.clair))
        manquantes = {}
        for chemin in _tous_les_xaml():
            texte = _sans_commentaires(_lire(chemin))
            for nom in DYNAMIQUE.findall(texte):
                if nom not in definies:
                    manquantes.setdefault(nom, os.path.basename(chemin))
        self.assertEqual(manquantes, {},
                         u'DynamicResource sans définition : %s' % manquantes)


if __name__ == '__main__':
    unittest.main()
