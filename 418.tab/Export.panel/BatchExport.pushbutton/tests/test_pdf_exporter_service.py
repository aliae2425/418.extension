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

# Isole la persistance UserConfig dans un dossier temporaire (jamais le config réel).
import tempfile as _tf
os.environ['PY418_CONFIG_DIR'] = _tf.mkdtemp(prefix='418test_')

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
