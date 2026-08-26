# -*- coding: utf-8 -*-
"""Modale de saisie de la largeur d'import, à la DA du socle.

Charge GUI/Modals/TailleSvg.xaml sur la coquille commune (`BaseWindow`, qui
fusionne Colors/Styles et câble TitleBar + CloseButton).

Pas de ViewModel : un seul champ texte, la vue le lit au clic sur « Importer ».
Un VM avec INotifyPropertyChanged pour une valeur unique n'apporterait rien.
"""
from __future__ import unicode_literals
import os

try:
    from ui.base.BaseWindow import BaseWindow
except ImportError:
    from lib.ui.base.BaseWindow import BaseWindow


def _chemin_xaml():
    ici = os.path.dirname(os.path.abspath(__file__))
    bouton = os.path.abspath(os.path.join(ici, '..', '..'))
    return os.path.join(bouton, 'GUI', 'Modals', 'TailleSvg.xaml')


class TailleSvgView(BaseWindow):
    """`valeur` vaut le texte saisi après « Importer », None si annulé."""

    def __init__(self, defaut='100', info=''):
        super(TailleSvgView, self).__init__(_chemin_xaml(), None)
        self._defaut = defaut
        self._info = info
        self.valeur = None

    def _load(self):
        super(TailleSvgView, self)._load()
        if self._window is None:
            return

        champ = self._window.FindName('ValeurTextBox')
        if champ is not None:
            champ.Text = self._defaut
            champ.SelectAll()

        info = self._window.FindName('InfoTextBlock')
        if info is not None:
            info.Text = self._info

        bouton_ok = self._window.FindName('OkButton')
        if bouton_ok is not None:
            def _sur_import(expediteur, args):
                self.valeur = champ.Text if champ is not None else None
                self._window.Close()
            bouton_ok.Click += _sur_import
        # Annuler et la croix ferment sans rien écrire : IsCancel="True" (WPF)
        # et le câblage CloseButton de BaseWindow suffisent, `valeur` reste None.
