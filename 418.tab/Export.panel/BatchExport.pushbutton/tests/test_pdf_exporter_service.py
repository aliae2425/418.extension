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

from lib.services.formats.PdfExporterService import PdfExporterService


class TestPdfExporterServiceBuildOptionsHorsRevit(unittest.TestCase):
    """Hors Revit, DB est None : build_options() doit rester silencieux
    (aucune exception) et renvoyer None, quel que soit setup_name."""

    def setUp(self):
        self.service = PdfExporterService()

    def test_build_options_sans_doc_renvoie_none(self):
        self.assertIsNone(self.service.build_options(None))

    def test_build_options_avec_setup_name_sans_doc_renvoie_none(self):
        self.assertIsNone(self.service.build_options(None, setup_name='MonSetup'))

    def test_build_options_avec_doc_mais_sans_api_revit_renvoie_none(self):
        # doc factice non-None, mais DB reste None (import Revit absent) :
        # build_options() doit quand même ne pas lever et renvoyer None
        # (garde `if DB is None or doc is None: return None`).
        class FakeDoc(object):
            pass
        self.assertIsNone(self.service.build_options(FakeDoc(), setup_name='MonSetup'))


class TestPdfExporterServiceCustomSetupApplyHorsRevit(unittest.TestCase):
    """_apply_custom_setup_data() est pure Python (pas d'appel Revit) et
    donc testable hors Revit avec un faux objet options."""

    def setUp(self):
        self.service = PdfExporterService()

    def test_apply_custom_setup_data_recopie_champs_connus(self):
        class FakeOptions(object):
            def __init__(self):
                self.StopOnError = False
                self.ColorDepth = None

        opts = FakeOptions()
        data = {'StopOnError': True, 'ColorDepth': 'Color', 'ChampInconnu': 'ignore-moi'}
        result = self.service._apply_custom_setup_data(opts, data)

        self.assertTrue(result.StopOnError)
        self.assertEqual(result.ColorDepth, 'Color')
        self.assertFalse(hasattr(result, 'ChampInconnu'))

    def test_apply_custom_setup_data_none_options_renvoie_none(self):
        self.assertIsNone(self.service._apply_custom_setup_data(None, {'StopOnError': True}))

    def test_apply_custom_setup_data_data_non_dict_renvoie_options_inchange(self):
        class FakeOptions(object):
            pass
        opts = FakeOptions()
        self.assertIs(self.service._apply_custom_setup_data(opts, None), opts)
        self.assertIs(self.service._apply_custom_setup_data(opts, 'pas-un-dict'), opts)

    def test_apply_custom_setup_data_ignore_champs_filename_et_combine(self):
        # FileName/Combine sont volontairement exclus de _PDF_OPTION_FIELDS
        # car gérés par ExportOrchestrator juste avant Document.Export.
        self.assertNotIn('FileName', self.service._PDF_OPTION_FIELDS)
        self.assertNotIn('Combine', self.service._PDF_OPTION_FIELDS)


class TestPdfExporterServiceFindRevitSetupElementHorsRevit(unittest.TestCase):
    def setUp(self):
        self.service = PdfExporterService()

    def test_find_revit_setup_element_sans_db_renvoie_none(self):
        self.assertIsNone(self.service._find_revit_setup_element(None, 'MonSetup'))

    def test_find_revit_setup_element_sans_nom_renvoie_none(self):
        class FakeDoc(object):
            pass
        self.assertIsNone(self.service._find_revit_setup_element(FakeDoc(), ''))
        self.assertIsNone(self.service._find_revit_setup_element(FakeDoc(), None))


if __name__ == '__main__':
    unittest.main()
