# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Centrer\nhorizont."
__doc__ = "Centre horizontalement les éléments sélectionnés sur le milieu de l'étendue de la sélection."
__author__ = 'Aliae'
__min_revit_ver__ = 2026

from core.align import executer

if __name__ == '__main__':
    executer(__revit__.ActiveUIDocument, 'centre_h')  # type: ignore # noqa: F821
