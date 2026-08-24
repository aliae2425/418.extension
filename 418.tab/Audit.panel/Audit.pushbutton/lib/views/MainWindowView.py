# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

from ui.base.BaseWindow import BaseWindow

# Chemin : lib/views/ -> lib/ -> pushbutton/
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_XAML = os.path.join(_ROOT, 'GUI', 'Views', 'MainWindow.xaml')


class MainWindowView(object):
    def __init__(self, view_model):
        self._vm = view_model
        self._win = BaseWindow(_XAML, view_model) if BaseWindow is not None else None

    def show(self):
        if self._win is None:
            print('MainWindowView: BaseWindow non disponible')
            return
        # Câble la fermeture programmatique AVANT ShowDialog() (bloquant) :
        # au moment de l'appel de on_fermer (clic utilisateur sur une ligne),
        # la fenêtre est déjà chargée par BaseWindow._load(), donc _window
        # est renseignée. Résolution paresseuse : évite de dépendre de
        # l'ordre de chargement au moment du câblage.
        if self._vm is not None:
            def _fermer():
                win = getattr(self._win, '_window', None)
                if win is not None:
                    try:
                        win.Close()
                    except Exception:
                        pass
            self._vm.on_fermer = _fermer
        self._win.show()
