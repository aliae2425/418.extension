# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in os.sys.path:
    os.sys.path.insert(0, _SHARED_LIB)
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in os.sys.path:
    os.sys.path.insert(0, _BUTTON)

# Isole la persistance UserConfig dans un dossier temporaire (jamais le config réel).
import tempfile as _tf
os.environ['PY418_CONFIG_DIR'] = _tf.mkdtemp(prefix='418test_')

from lib.services.SheetCollectionService import SheetCollectionService


class TestSheetCollectionServiceDocNone(unittest.TestCase):
    """Sans document (hors Revit), toutes les listes doivent être vides sans lever.

    Le service est en LECTURE SEULE du document : il n'a ni config ni
    lecture de paramètres, son seul argument est `doc`."""

    def setUp(self):
        self.service = SheetCollectionService(doc=None)

    def test_list_collections_vide(self):
        self.assertEqual(self.service.list_collections(), [])

    def test_list_sheets_vide(self):
        self.assertEqual(self.service.list_sheets(), [])

    def test_list_sheets_avec_collection_id_vide(self):
        self.assertEqual(self.service.list_sheets(collection_id='fake-id'), [])

    def test_construction_sans_argument_ne_leve_pas(self):
        service = SheetCollectionService()
        self.assertEqual(service.list_collections(), [])
        self.assertEqual(service.list_sheets(), [])
        self.assertEqual(service.list_all_sheets(), [])
        self.assertEqual(service.list_view_sheet_sets(), [])

    def test_list_all_sheets_vide(self):
        self.assertEqual(self.service.list_all_sheets(), [])

    def test_list_view_sheet_sets_vide(self):
        self.assertEqual(self.service.list_view_sheet_sets(), [])


if __name__ == '__main__':
    unittest.main()
