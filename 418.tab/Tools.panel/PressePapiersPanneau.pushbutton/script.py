# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Panneau\npresse-papiers"
__doc__ = ("Ouvre l'historique du presse-papiers dans un panneau flottant, "
           "ancrable, qui reste ouvert pendant qu'on travaille.")
__author__ = 'Aliae'
__version__ = '0.1.0'
__min_revit_ver__ = 2026
__beta__ = True

from pyrevit import forms

from ui.PressePapiersPanel import PressePapiersPanel

if __name__ == '__main__':
    # Même logique que Chat.pushbutton : seul GetDockablePane dit la vérité.
    try:
        forms.open_dockable_panel(PressePapiersPanel)
    except Exception:
        forms.alert("Le panneau Presse-papiers n'a pas été créé par Revit.\n"
                    "Redémarrez Revit : un panneau ancrable ne peut "
                    "s'enregistrer qu'au démarrage.", title='Presse-papiers')
