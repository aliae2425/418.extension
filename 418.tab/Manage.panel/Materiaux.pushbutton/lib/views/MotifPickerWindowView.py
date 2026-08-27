# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

try:
    from ui.base.BaseWindow import BaseWindow
except Exception:
    try:
        from lib.ui.base.BaseWindow import BaseWindow
    except Exception:
        BaseWindow = object

_XAML = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'GUI', 'Views', 'MotifPickerWindow.xaml')


class MotifPickerWindowView(BaseWindow):
    """Modale de choix d'un motif. Le résultat se lit dans `vm.Resultat`.

    `Annuler` porte IsCancel et se ferme seul ; `Choisir` ne ferme que si une
    ligne est sélectionnée, et le double-clic vaut validation.
    """

    def __init__(self, view_model, proprietaire=None):
        super(MotifPickerWindowView, self).__init__(_XAML, view_model)
        self._proprietaire = proprietaire

    def _load(self):
        super(MotifPickerWindowView, self)._load()
        if self._window is None:
            return
        if self._proprietaire is not None:
            try:
                self._window.Owner = self._proprietaire
            except Exception:
                pass
        bouton = self._window.FindName('ChoisirButton')
        if bouton is not None:
            bouton.Click += lambda envoyeur, args: self._valider()
        liste = self._window.FindName('MotifsList')
        if liste is not None:
            liste.MouseDoubleClick += lambda envoyeur, args: self._valider()
        # Curseur dans la recherche à l'ouverture : on vient là pour chercher.
        recherche = self._window.FindName('SearchBox')
        if recherche is not None:
            recherche.Focus()

    def _valider(self):
        if self._vm.valider():
            self._window.Close()
