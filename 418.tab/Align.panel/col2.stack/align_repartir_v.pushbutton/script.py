# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__title__ = "Répartir\nvertical."
__doc__ = "Répartit verticalement les éléments sélectionnés : centres également espacés entre les deux extrêmes."
__author__ = 'Aliae'
__min_revit_ver__ = 2026

from core.align import executer

if __name__ == '__main__':
    executer(__revit__.ActiveUIDocument, 'repartir_v')  # type: ignore # noqa: F821
