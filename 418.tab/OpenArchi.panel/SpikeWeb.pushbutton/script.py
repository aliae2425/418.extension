# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Spike\nWebView2"
__doc__ = ("Banc d'essai : un WebView2 dans un volet ancrable, branché sur "
           "rien. Mesure ce que RampeParking ne pouvait pas trancher — "
           "survie du HWND à l'ancrage, CoreWebView2, mapping virtuel, "
           "latence postMessage. Jetable.")
__author__ = 'Aliae'
__min_revit_ver__ = 2026

from pyrevit import forms

from ui.SpikeWebPanel import SpikeWebPanel

if __name__ == '__main__':
    # Même prudence que Chat.pushbutton : `PaneIsRegistered` répond « oui » dès
    # que RegisterDockablePane a été appelé, y compris quand Revit a refusé de
    # créer le volet (Reload pyRevit, qui rejoue startup.py hors OnStartup).
    try:
        forms.open_dockable_panel(SpikeWebPanel)
    except Exception:
        forms.alert("Le volet du banc n'a pas été créé par Revit.\n"
                    "Redémarrez Revit : un volet ancrable ne peut "
                    "s'enregistrer qu'au démarrage.", title='Spike WebView2')
