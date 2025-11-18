# -*- coding: utf-8 -*-

"""Facade GUI minimaliste: délègue l'UI au contrôleur ui/windows/MainWindowController.

API publique:
    - GUI.show(): ouvre la fenêtre principale via MainWindowController.
"""

from __future__ import unicode_literals


class GUI(object):
    @staticmethod
    def show():
        try:
            from .ui.windows.MainWindowController import MainWindowController
            ctrl = MainWindowController()
            return bool(ctrl.show())
        except Exception as e:
            print('[info] Erreur ouverture UI:', e)
            return False


# Compat UI helpers pour l'orchestrateur (statuts dans la grille)
def _refresh_collection_grid(win):
    try:
        from .ui.components.CollectionPreviewComponent import CollectionPreviewComponent
        CollectionPreviewComponent().refresh_grid(win)
    except Exception:
        pass


def _set_collection_status(win, collection_name, state):
    try:
        from .ui.components.CollectionPreviewComponent import CollectionPreviewComponent
        CollectionPreviewComponent().set_collection_status(win, collection_name, state)
    except Exception:
        pass


def _set_detail_status(win, collection_name, detail_name, detail_format, state):
    try:
        from .ui.components.CollectionPreviewComponent import CollectionPreviewComponent
        CollectionPreviewComponent().set_detail_status(win, collection_name, detail_name, detail_format, state)
    except Exception:
        pass