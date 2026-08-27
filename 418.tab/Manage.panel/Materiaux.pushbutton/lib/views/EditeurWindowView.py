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
    'GUI', 'Views', 'EditeurWindow.xaml')


class EditeurWindowView(BaseWindow):
    """Fenêtre modale d'édition d'un matériau.

    `Annuler` porte IsCancel et se ferme tout seul ; `Enregistrer` est câblé
    ici parce qu'il ne doit fermer QUE si Revit a tout accepté — sinon la
    fenêtre reste ouverte avec la liste des propriétés refusées en pied.
    """

    def __init__(self, view_model, proprietaire=None):
        super(EditeurWindowView, self).__init__(_XAML, view_model)
        self._proprietaire = proprietaire

    def _load(self):
        super(EditeurWindowView, self)._load()
        if self._window is None:
            return
        # Owner : rend la modale vraiment modale par rapport à la fenêtre
        # Matériaux, et donne son sens à WindowStartupLocation=CenterOwner.
        if self._proprietaire is not None:
            try:
                self._window.Owner = self._proprietaire
            except Exception:
                pass
        bouton = self._window.FindName('EnregistrerButton')
        if bouton is not None:
            bouton.Click += self._on_enregistrer

    def _on_enregistrer(self, sender, args):
        if self._vm.enregistrer():
            self._window.Close()
