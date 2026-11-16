# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Presse-\npapiers"
__doc__ = ("Historique des copies Revit, façon Win+V : chaque Ctrl+C y ajoute "
           "une entrée, qu'on recolle au même emplacement (1 / Entrée), "
           "alignée sur la vue courante (2) ou à un point cliqué (3).\n\n"
           "Assignez-lui un raccourci clavier Revit (Fichier > Options > "
           "Interface utilisateur > Raccourcis clavier), par exemple "
           "Ctrl+Shift+V : la liste s'ouvre alors sous le curseur.")
__author__ = 'Aliae'
__version__ = '0.1.0'
__min_revit_ver__ = 2026
__beta__ = True

from core.presse_papiers import historique
from ui.PressePapiersVM import PressePapiersVM
from ui.PressePapiersPopup import PressePapiersPopup

if __name__ == '__main__':
    uidoc = __revit__.ActiveUIDocument
    # Exécuteur direct : la commande du bouton EST le contexte API.
    vm = PressePapiersVM(historique(), lambda fn: fn(uidoc), suivre=False)
    PressePapiersPopup(vm, proprietaire=__revit__.MainWindowHandle).ouvrir()
    if vm.Etat:
        # La popup est fermée : le compte rendu part dans la barre d'état.
        from pyrevit import forms
        forms.show_balloon('Presse-papiers', vm.Etat)
