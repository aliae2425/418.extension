# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in os.sys.path:
    os.sys.path.insert(0, _SHARED_LIB)
# Meme racine que pyRevit expose : <bouton>/lib.
_BUTTON_LIB = os.path.abspath(os.path.join(_HERE, '..', 'lib'))
if _BUTTON_LIB not in os.sys.path:
    os.sys.path.insert(0, _BUTTON_LIB)

# Isole la persistance UserConfig dans un dossier temporaire (jamais le config réel).
import tempfile as _tf
os.environ['PY418_CONFIG_DIR'] = _tf.mkdtemp(prefix='418test_')

from services.SheetCollectionService import SheetCollectionService


class FakeConfig(object):
    """Faux UserConfig en mémoire."""

    def __init__(self):
        self._store = {}

    def get(self, key, default=None):
        return self._store.get(key, default)

    def set(self, key, value):
        self._store[key] = value
        return True


class FakeParam(object):
    """Faux paramètre Revit Oui/Non."""

    def __init__(self, value):
        self._value = value

    def AsInteger(self):
        return self._value


class FakeParamRaises(object):
    """Faux paramètre dont AsInteger() lève (valeur non entière)."""

    def AsInteger(self):
        raise Exception('StorageType invalide')


class FakeElem(object):
    """Faux élément Revit exposant LookupParameter."""

    def __init__(self, params=None):
        self._params = params or {}

    def LookupParameter(self, name):
        return self._params.get(name)


class TestSheetCollectionServiceDocNone(unittest.TestCase):
    """Sans document (hors Revit), toutes les listes doivent être vides sans lever."""

    def setUp(self):
        self.service = SheetCollectionService(doc=None, config=FakeConfig())

    def test_list_collections_vide(self):
        self.assertEqual(self.service.list_collections(), [])

    def test_list_sheets_vide(self):
        self.assertEqual(self.service.list_sheets(), [])

    def test_list_sheets_avec_collection_id_vide(self):
        self.assertEqual(self.service.list_sheets(collection_id='fake-id'), [])

    def test_list_boolean_params_vide(self):
        self.assertEqual(self.service.list_boolean_params(), [])

    def test_construction_sans_config_ne_leve_pas(self):
        # Ni doc ni config -> repli UserConfig réel (indisponible hors Revit/pyRevit)
        # ou None : ne doit jamais lever.
        service = SheetCollectionService()
        self.assertEqual(service.list_collections(), [])
        self.assertEqual(service.list_sheets(), [])
        self.assertEqual(service.list_boolean_params(), [])

    def test_list_all_sheets_vide(self):
        self.assertEqual(self.service.list_all_sheets(), [])

    def test_list_view_sheet_sets_vide(self):
        self.assertEqual(self.service.list_view_sheet_sets(), [])


class TestSheetCollectionServiceReadFlag(unittest.TestCase):
    def setUp(self):
        self.service = SheetCollectionService(doc=None, config=FakeConfig())

    def test_read_flag_true_si_as_integer_1(self):
        elem = FakeElem({'P': FakeParam(1)})
        self.assertTrue(self.service.read_flag(elem, 'P'))

    def test_read_flag_false_si_as_integer_0(self):
        elem = FakeElem({'P': FakeParam(0)})
        self.assertFalse(self.service.read_flag(elem, 'P'))

    def test_read_flag_false_si_param_absent(self):
        elem = FakeElem({})
        self.assertFalse(self.service.read_flag(elem, 'Inexistant'))

    def test_read_flag_false_si_elem_none(self):
        self.assertFalse(self.service.read_flag(None, 'P'))

    def test_read_flag_false_si_param_name_vide(self):
        elem = FakeElem({'P': FakeParam(1)})
        self.assertFalse(self.service.read_flag(elem, ''))
        self.assertFalse(self.service.read_flag(elem, None))

    def test_read_flag_false_si_as_integer_leve(self):
        elem = FakeElem({'P': FakeParamRaises()})
        self.assertFalse(self.service.read_flag(elem, 'P'))

    def test_read_flag_false_si_lookup_parameter_leve(self):
        class FakeElemBoom(object):
            def LookupParameter(self, name):
                raise Exception('Elément invalide')

        self.assertFalse(self.service.read_flag(FakeElemBoom(), 'P'))


if __name__ == '__main__':
    unittest.main()
