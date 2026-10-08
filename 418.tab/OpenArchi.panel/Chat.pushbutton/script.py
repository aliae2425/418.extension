# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Chat"
__doc__ = ("Ouvre le panneau OpenArchi ancré dans l'interface Revit.\n\n"
           "Interface web (WebView2) : texte en flux, Markdown rendu, appels "
           "d'outils et accord sur les irréversibles dans le fil.\n\n"
           "L'agent est encore FICTIF — aucun modèle appelé, maquette intacte.")
__author__ = 'Aliae'
__min_revit_ver__ = 2026

from pyrevit import forms

from ui.ProtoChatPanel import ProtoChatPanel

if __name__ == '__main__':
    # On tente l'ouverture sans pré-contrôle : `PaneIsRegistered` répond « oui »
    # dès que RegisterDockablePane a été appelé, y compris quand Revit a refusé
    # de créer le volet (appel hors OnStartup, cas d'un Reload pyRevit qui
    # rejoue startup.py). Seul GetDockablePane dit la vérité.
    try:
        forms.open_dockable_panel(ProtoChatPanel)
    except Exception:
        forms.alert("Le volet OpenArchi n'a pas été créé par Revit.\n"
                    "Redémarrez Revit : un volet ancrable ne peut "
                    "s'enregistrer qu'au démarrage.", title='OpenArchi')
