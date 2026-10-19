# -*- coding: utf-8 -*-
# Vue de la modale « Ordre d'impression » : charge GUI/Modals/OrdreImpression.xaml
# sur la coquille commune (BaseWindow) et câble les 5 boutons.
#
# Rien d'autre : le déplacement, le tri et la validation sont dans
# `OrdreImpressionViewModel`, donc testables hors WPF.
from __future__ import unicode_literals
import os

try:
    from ui.base.BaseWindow import BaseWindow
except Exception:
    BaseWindow = object


def _xaml_path():
    here = os.path.dirname(os.path.abspath(__file__))
    button = os.path.abspath(os.path.join(here, '..', '..'))
    return os.path.join(button, 'GUI', 'Modals', 'OrdreImpression.xaml')


class OrdreImpressionView(BaseWindow):
    def __init__(self, view_model):
        super(OrdreImpressionView, self).__init__(_xaml_path(), view_model)
        self._vm = view_model

    def _load(self):
        super(OrdreImpressionView, self)._load()
        self.wire_boutons()

    def wire_boutons(self):
        """Câblage best-effort, comme le reste de l'outil : un bouton absent
        du XAML (FindName -> None) laisse la fenêtre charger sans lever."""
        if self._window is None:
            return
        vm = self._vm

        def _fermer():
            try:
                self._window.Close()
            except Exception:
                pass

        def _valider():
            # `valider()` d'abord : c'est le drapeau que l'appelant lit au
            # retour de ShowDialog pour savoir s'il doit appliquer l'ordre.
            try:
                vm.valider()
            except Exception:
                pass
            _fermer()

        actions = (
            (u'MonterButton', lambda: vm.monter()),
            (u'DescendreButton', lambda: vm.descendre()),
            (u'TrierButton', lambda: vm.trier_numero()),
            (u'ValiderButton', _valider),
            (u'AnnulerButton', _fermer),
        )
        for nom, action in actions:
            btn = self._window.FindName(nom)
            if btn is None:
                continue
            self._brancher(btn, action)

    @staticmethod
    def _brancher(btn, action):
        def _handler(sender, args):
            try:
                action()
            except Exception:
                pass
        try:
            btn.Click += _handler
        except Exception:
            pass
