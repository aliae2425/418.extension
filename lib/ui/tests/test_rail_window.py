# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import importlib
import os
import sys
import unittest
import xml.etree.ElementTree as ElementTree

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.abspath(os.path.join(_HERE, '..', '..'))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)
_EXT = os.path.dirname(_LIB)

from core.AppPaths import AppPaths
from ui.base.RailWindow import RailWindow

# Les outils à rail du dépôt. Aucun ne porte plus sa propre coquille : ils
# doivent tous retomber sur celle du socle.
BOUTONS = [
    os.path.join('418.tab', 'Tools.panel', 'col1.stack',
                 'duplicate_sheets.pushbutton'),
    os.path.join('418.tab', 'Tools.panel', 'col1.stack',
                 'views_duplicate.pushbutton'),
    os.path.join('418.tab', 'Tools.panel', 'col1.stack', 'Rename.pulldown',
                 'FindReplace_Sheets.pushbutton'),
    os.path.join('418.tab', 'Tools.panel', 'col1.stack', 'Rename.pulldown',
                 'FindReplace - Views.pushbutton'),
    os.path.join('418.tab', 'Manage.panel', 'Materiaux.pushbutton'),
]


def _charger_vue(bouton):
    """Importe le MainWindowView d'un bouton, isolé des précédents.

    Purge `lib` LUI-MÊME et pas seulement `lib.*` : sans ça le paquet reste
    lié au dossier du premier bouton et les suivants relisent ses ONGLETS.
    """
    sys.path.insert(0, bouton)
    try:
        for nom in [m for m in list(sys.modules)
                    if m == 'lib' or m.startswith('lib.')]:
            del sys.modules[nom]
        return importlib.import_module('lib.views.MainWindowView').MainWindowView
    finally:
        sys.path.remove(bouton)


class TestCoquillePartagee(unittest.TestCase):
    """La coquille du socle sert tous les outils à rail.

    Hors Revit, WPF n'existe pas : on ne vérifie pas le rendu mais le
    contrat qui le précède — chemins résolus, onglets déclarés, cibles de
    navigation cohérentes. C'est ce qui casse quand on renomme une page ou
    qu'on ajoute un onglet.
    """

    def setUp(self):
        self.socle = os.path.join(AppPaths().ui_gui_dir(), 'MainWindow.xaml')

    def test_la_coquille_du_socle_existe_et_est_bien_formee(self):
        self.assertTrue(os.path.exists(self.socle))
        ElementTree.parse(self.socle)

    def test_la_coquille_expose_les_noms_attendus(self):
        with open(self.socle, 'rb') as f:
            contenu = f.read().decode('utf-8')
        for nom in ('TitleBar', 'MinimizeButton', 'MaximizeRestoreButton',
                    'CloseButton', 'NavItems', 'PageHost'):
            self.assertIn('x:Name="%s"' % nom, contenu)

    def test_aucun_outil_ne_porte_plus_sa_propre_coquille(self):
        for rel in BOUTONS:
            bouton = os.path.join(_EXT, rel)
            self.assertEqual(RailWindow._chemin_fenetre(bouton), self.socle,
                             u'%s ne retombe pas sur la coquille du socle' % rel)

    def test_chaque_onglet_resout_sa_page_et_declare_son_icone(self):
        for rel in BOUTONS:
            bouton = os.path.join(_EXT, rel)
            classe = _charger_vue(bouton)
            fenetre = RailWindow(bouton, None)
            self.assertTrue(classe.ONGLETS, u'%s sans onglet' % rel)
            for onglet in classe.ONGLETS:
                self.assertTrue(os.path.exists(fenetre._chemin_page(onglet.xaml)),
                                u'%s : page %s introuvable' % (rel, onglet.xaml))
                self.assertTrue(onglet.icone,
                                u'%s : onglet %s sans icône' % (rel, onglet.mode))

    def test_toutes_les_cles_dicones_existent(self):
        """Une clé mal tapée ne lève rien : elle vide le bouton en silence.

        `TryFindResource` ne proteste pas, et ces clés-ci sont des chaînes
        Python : `test_theme_resources`, qui couvre les DynamicResource des
        rails écrits en XAML, ne les voit pas.
        """
        icones = ElementTree.parse(AppPaths().resource_path('Icons.xaml'))
        cle = '{http://schemas.microsoft.com/winfx/2006/xaml}Key'
        connues = set(n.get(cle) for n in icones.getroot())
        self.assertTrue(connues)
        for rel in BOUTONS:
            for onglet in _charger_vue(os.path.join(_EXT, rel)).ONGLETS:
                self.assertIn(onglet.icone, connues,
                              u'%s : onglet %s' % (rel, onglet.mode))

    def test_les_cibles_de_navigation_existent(self):
        for rel in BOUTONS:
            classe = _charger_vue(os.path.join(_EXT, rel))
            modes = set(o.mode for o in classe.ONGLETS)
            for (depuis, _nom_bouton, vers) in classe.SUIVANTS:
                self.assertIn(depuis, modes, u'%s : SUIVANTS' % rel)
                self.assertIn(vers, modes, u'%s : SUIVANTS' % rel)
            if classe.RUN:
                self.assertIn(classe.RUN[0], modes, u'%s : RUN' % rel)
            if classe.RADIOS:
                self.assertIn(classe.RADIOS[0], modes, u'%s : RADIOS' % rel)


if __name__ == '__main__':
    unittest.main()
