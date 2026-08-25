# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Aligner\nen haut"
__doc__ = "Aligne les éléments sélectionnés sur le bord haut de la vue active."
__author__ = 'Aliae'
__min_revit_ver__ = 2026

from core.align import executer

if __name__ == '__main__':
    executer(__revit__.ActiveUIDocument, 'haut')  # type: ignore # noqa: F821
