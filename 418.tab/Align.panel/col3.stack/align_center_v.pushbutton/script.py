# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Centrer\nvertical."
__doc__ = "Centre verticalement les éléments sélectionnés sur le milieu de l'étendue de la sélection."
__author__ = 'Aliae'
__min_revit_ver__ = 2026

from core.align import executer

if __name__ == '__main__':
    executer(__revit__.ActiveUIDocument, 'centre_v')  # type: ignore # noqa: F821
