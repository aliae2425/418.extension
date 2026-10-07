# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "PC"
__doc__ = ("Monte les feuilles et les jeux d'un dossier d'urbanisme (DP, PC, "
           "PD) DANS la maquette : on choisit le type et les pièces du "
           "bordereau, l'outil analyse le projet et crée ce qui manque.")
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
from lib.services import FeuillesService

from core.UserConfig import UserConfig
from core.transaction import revit_transaction
from core.selection import (all_sheets, cartouches, jeux_de_feuilles,
                            nom_de_type, vues_par_type, vues_sans_feuille)


def analyser(piece):
    """Les vues du projet qui alimentent cette pièce et n'ont pas de feuille.

    C'est tout « l'analyse » : on ne devine pas un besoin, on regarde ce qui
    attend une feuille. Une vue déjà posée n'en redemande pas — Revit refuse
    de la poser deux fois, et l'architecte l'a déjà traitée.
    """
    if doc is None or not piece.vues:
        return []
    vues = vues_sans_feuille(doc, vues_par_type(doc, piece.vues))
    return [(v.Id, v.Name) for v in vues]


def creer(plan, cartouche):
    """Écrit dans la maquette, en UNE transaction.

    Un seul Ctrl+Z défait tout le dossier : créer vingt feuilles et devoir
    les retirer une par une serait pire que de n'avoir rien créé.
    """
    with revit_transaction(doc, u'418 — dossier d\'urbanisme'):
        return FeuillesService.creer(doc, plan, cartouche)


if __name__ == '__main__':
    # Tout ce qui touche Revit est lu ICI et passé au VM, qui reste testable
    # hors Revit : les cartouches, les numéros déjà pris, les jeux existants.
    liste_cartouches = ([(c.Id, nom_de_type(c)) for c in cartouches(doc)]
                        if doc is not None else [])
    numeros = ([f.SheetNumber for f in all_sheets(doc)]
               if doc is not None else [])
    jeux = ([j.Name for j in jeux_de_feuilles(doc)]
            if doc is not None else [])

    vm = MainViewModel(doc=doc, uidoc=uidoc,
                       config=UserConfig('pc'),
                       cartouches=liste_cartouches,
                       analyser=analyser,
                       numeros_existants=numeros,
                       jeux_existants=jeux,
                       creer=creer if doc is not None else None)
    view = MainWindowView(vm)
    view.show()
