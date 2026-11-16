# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in sys.path:
    sys.path.insert(0, _BUTTON)

from lib.services.formats.base import (
    SURCHARGES_PDF, SURCHARGES_DWG, appliquer_surcharges)


class _Enums(object):
    """Faux espace DB : énumérations réduites à des chaînes repérables."""

    class ColorDepthType(object):
        Color = 'enum:Color'
        GrayScale = 'enum:GrayScale'
        BlackLine = 'enum:BlackLine'

    class RasterQualityType(object):
        High = 'enum:High'

    class ACADVersion(object):
        R2018 = 'enum:R2018'


class _Options(object):
    """Options d'export factices : valeurs « du setup » déjà posées."""

    def __init__(self):
        self.ColorDepth = 'setup'
        self.RasterQuality = 'setup'
        self.AlwaysUseRaster = 'setup'
        self.HideCropBoundaries = 'setup'
        self.FileVersion = 'setup'
        self.SharedCoords = 'setup'


class _Log(object):
    def __init__(self):
        self.messages = []

    def warning(self, *args):
        self.messages.append(args)


class TestAppliquerSurcharges(unittest.TestCase):

    def _appliquer(self, cfg, table=SURCHARGES_PDF):
        self.log = _Log()
        return appliquer_surcharges(_Options(), cfg, table,
                                    enums=_Enums, log=self.log)

    def test_valeur_vide_laisse_le_setup(self):
        opt = self._appliquer({'pdf_couleur': '', 'pdf_raster': ''})
        self.assertEqual('setup', opt.ColorDepth)
        self.assertEqual('setup', opt.AlwaysUseRaster)
        self.assertEqual([], self.log.messages)

    def test_enum_et_booleens_convertis(self):
        opt = self._appliquer({'pdf_couleur': 'GrayScale',
                               'pdf_qualite': 'High',
                               'pdf_raster': '1',
                               'pdf_masquer_cadrage': '0'})
        self.assertEqual('enum:GrayScale', opt.ColorDepth)
        self.assertEqual('enum:High', opt.RasterQuality)
        self.assertIs(True, opt.AlwaysUseRaster)
        self.assertIs(False, opt.HideCropBoundaries)

    def test_dwg(self):
        opt = self._appliquer({'dwg_version': 'R2018',
                               'dwg_coords_partagees': '1'}, SURCHARGES_DWG)
        self.assertEqual('enum:R2018', opt.FileVersion)
        self.assertIs(True, opt.SharedCoords)

    def test_valeur_inconnue_ignoree_et_journalisee(self):
        opt = self._appliquer({'pdf_couleur': 'Fluo', 'pdf_raster': 'oui',
                               'pdf_qualite': 'High'})
        self.assertEqual('setup', opt.ColorDepth)
        self.assertEqual('setup', opt.AlwaysUseRaster)
        # Les autres surcharges passent quand même.
        self.assertEqual('enum:High', opt.RasterQuality)
        self.assertEqual(2, len(self.log.messages))

    def test_options_ou_config_absentes(self):
        self.assertIsNone(appliquer_surcharges(None, {'pdf_raster': '1'},
                                               SURCHARGES_PDF, enums=_Enums))
        opt = _Options()
        self.assertIs(opt, appliquer_surcharges(opt, None, SURCHARGES_PDF))


if __name__ == '__main__':
    unittest.main()
