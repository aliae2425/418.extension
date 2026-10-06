# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Chat"
__doc__ = "Ouvre le panneau OpenArchi ancré dans l'interface Revit."
__author__ = 'Aliae'
__min_revit_ver__ = 2026

from pyrevit import forms

from ui.OpenArchiPanel import OpenArchiPanel

if __name__ == '__main__':
    # On tente l'ouverture sans pré-contrôle : `PaneIsRegistered` répond « oui »
    # dès que RegisterDockablePane a été appelé, y compris quand Revit a refusé
    # de créer le volet (appel hors OnStartup, cas d'un Reload pyRevit qui
    # rejoue startup.py). Seul GetDockablePane dit la vérité.
    try:
        forms.open_dockable_panel(OpenArchiPanel)
    except Exception:
        forms.alert("Le volet OpenArchi n'a pas été créé par Revit.\n"
                    "Redémarrez Revit : un volet ancrable ne peut "
                    "s'enregistrer qu'au démarrage.", title='OpenArchi')
