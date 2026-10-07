# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "PC"
__doc__ = ("Monte l'arborescence d'un dossier d'urbanisme (DP, PC, PD) : "
           "on choisit le type, les pièces du bordereau et le jeu de feuilles "
           "qui alimente chacune, puis on génère les dossiers.")
__author__ = 'Aliae'
__min_revit_ver__ = 2026
__beta__ = True

try:
    uidoc = __revit__.ActiveUIDocument  # type: ignore # noqa: F821
    doc = uidoc.Document
except Exception:
    uidoc = doc = None

from lib.viewmodels.MainViewModel import MainViewModel
from lib.views.MainWindowView import MainWindowView
from lib.services.NomRacineService import infos_projet

from core.UserConfig import UserConfig
from core.selection import jeux_de_feuilles

if __name__ == '__main__':
    # Les jeux de feuilles ne sont lus QU'ICI : le VM n'en garde que les noms,
    # ce qui le laisse testable hors Revit. Retrouver l'élément au moment
    # d'exporter sera l'affaire de l'étape suivante.
    jeux = [j.Name for j in jeux_de_feuilles(doc)] if doc is not None else []

    vm = MainViewModel(doc=doc, uidoc=uidoc,
                       config=UserConfig('pc'),
                       infos=infos_projet(doc),
                       jeux=jeux)
    view = MainWindowView(vm)
    view.show()
