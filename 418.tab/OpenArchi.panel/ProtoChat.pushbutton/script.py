# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Chat\n(proto)"
__doc__ = ("Prototype de chat en interface web : streaming mot à mot, Markdown "
           "rendu, appels d'outils, accord sur un irréversible dans le fil. "
           "L'agent est FICTIF — aucun modèle appelé, maquette intacte.")
__author__ = 'Aliae'
__min_revit_ver__ = 2026

from pyrevit import forms

from ui.ProtoChatPanel import ProtoChatPanel

if __name__ == '__main__':
    # `PaneIsRegistered` répond « oui » dès que RegisterDockablePane a été
    # appelé, y compris quand Revit a refusé de créer le volet (Reload pyRevit,
    # qui rejoue startup.py hors OnStartup). Seul GetDockablePane dit la vérité.
    try:
        forms.open_dockable_panel(ProtoChatPanel)
    except Exception:
        forms.alert("Le volet du prototype n'a pas été créé par Revit.\n"
                    "Redémarrez Revit : un volet ancrable ne peut "
                    "s'enregistrer qu'au démarrage.", title='OpenArchi (proto)')
