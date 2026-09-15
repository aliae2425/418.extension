# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Chat"
__doc__ = "Ouvre le panneau OpenArchi ancré dans l'interface Revit."
__author__ = 'Aliae'
__min_revit_ver__ = 2026

from pyrevit import forms

from ui.OpenArchiPanel import OpenArchiPanel

if __name__ == '__main__':
    if forms.is_registered_dockable_panel(OpenArchiPanel):
        forms.open_dockable_panel(OpenArchiPanel)
    else:
        forms.alert("Le panneau OpenArchi n'est pas enregistré.\n"
                    "Redémarrez Revit : un panneau ancrable ne peut "
                    "s'enregistrer qu'au démarrage.", title='OpenArchi')
