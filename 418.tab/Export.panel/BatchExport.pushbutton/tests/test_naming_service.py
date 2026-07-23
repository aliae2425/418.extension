# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import re
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

from lib.services.NamingService import NamingService


class FakeParameter(object):
    """Faux paramètre Revit exposant AsString/AsValueString/Definition."""

    def __init__(self, name, value):
        self.Definition = FakeDefinition(name)
        self._value = value

    def AsString(self):
        return self._value

    def AsValueString(self):
        return self._value

    @property
    def StorageType(self):
        return None

    def AsInteger(self):
        return 0

    def AsDouble(self):
        return 0.0

    def AsElementId(self):
        return None


class FakeDefinition(object):
    def __init__(self, name):
        self.Name = name


class FakeElement(object):
    """Faux élément Revit : LookupParameter + .Parameters."""

    def __init__(self, values):
        self._values = dict(values or {})

    def LookupParameter(self, name):
        if name in self._values:
            return FakeParameter(name, self._values[name])
        return None

    @property
    def Parameters(self):
        return [FakeParameter(n, v) for n, v in self._values.items()]


class FakeConfig(object):
    """Faux UserConfig en mémoire pour exercer le round-trip save/load."""

    def __init__(self):
        self._store = {}

    def get(self, key, default=None):
        return self._store.get(key, default)

    def set(self, key, value):
        self._store[key] = value
        return True


class TestNamingServiceResolution(unittest.TestCase):
    def setUp(self):
        self.service = NamingService(doc=None, config=FakeConfig())

    def test_resolution_pattern_simple(self):
        rows = [{'Name': 'X', 'Prefix': 'a-', 'Suffix': '-b'}]
        elem = FakeElement({'X': '42'})
        self.assertEqual(self.service.resolve_for_element(elem, rows), 'a-42-b')

    def test_date_annee_quatre_chiffres(self):
        rows = [{'Name': 'Date: Année', 'Prefix': '', 'Suffix': ''}]
        elem = FakeElement({})
        result = self.service.resolve_for_element(elem, rows)
        self.assertRegexpMatches(result, r'^\d{4}$') if hasattr(
            self, 'assertRegexpMatches') else self.assertTrue(
            re.match(r'^\d{4}$', result))

    def test_valeur_dotnet_invalide_nettoyee(self):
        rows = [{'Name': 'X', 'Prefix': 'a-', 'Suffix': '-b'}]
        elem = FakeElement({
            'X': '<Autodesk.Revit.DB.WallType object at 0x00000123456789AB>'
        })
        result = self.service.resolve_for_element(elem, rows)
        self.assertNotIn('Autodesk.Revit.DB', result)
        self.assertNotIn('object at', result)
        # Valeur nettoyée -> vide, donc uniquement prefix+suffix restent.
        self.assertEqual(result, 'a--b')

    def test_build_pattern(self):
        rows = [
            {'Name': 'Numero_Feuille', 'Prefix': '', 'Suffix': '-'},
            {'Name': 'date_day', 'Prefix': '', 'Suffix': ''},
        ]
        self.assertEqual(
            self.service.build_pattern(rows),
            '{Numero_Feuille}-{date_day}')

    def test_row_sans_name_ignoree(self):
        rows = [{'Name': '', 'Prefix': 'x', 'Suffix': 'y'}]
        elem = FakeElement({})
        self.assertEqual(self.service.resolve_for_element(elem, rows), '')


class TestNamingServicePersistence(unittest.TestCase):
    def setUp(self):
        self.config = FakeConfig()
        self.service = NamingService(doc=None, config=self.config)

    def test_round_trip_save_load_sheet(self):
        rows = [{'Name': 'Numero_Feuille', 'Prefix': '', 'Suffix': '-'}]
        pattern = self.service.build_pattern(rows)
        self.service.save('sheet', pattern, rows)

        loaded_pattern, loaded_rows = self.service.load('sheet')
        self.assertEqual(loaded_pattern, pattern)
        self.assertEqual(loaded_rows, rows)

    def test_round_trip_save_load_set(self):
        rows = [
            {'Name': 'Date: Jour', 'Prefix': '', 'Suffix': '_'},
            {'Name': 'Date: Mois', 'Prefix': '', 'Suffix': ''},
        ]
        pattern = self.service.build_pattern(rows)
        self.service.save('set', pattern, rows)

        loaded_pattern, loaded_rows = self.service.load('set')
        self.assertEqual(loaded_pattern, pattern)
        self.assertEqual(loaded_rows, rows)

    def test_has_saved_false_par_defaut(self):
        self.assertFalse(self.service.has_saved('sheet'))

    def test_has_saved_true_apres_save(self):
        rows = [{'Name': 'X', 'Prefix': '', 'Suffix': ''}]
        self.service.save('sheet', self.service.build_pattern(rows), rows)
        self.assertTrue(self.service.has_saved('sheet'))

    def test_kind_inconnu_ne_leve_pas(self):
        self.assertFalse(self.service.save('bogus', 'p', []))
        pattern, rows = self.service.load('bogus')
        self.assertEqual(pattern, '')
        self.assertEqual(rows, [])

    def test_config_none_reste_utilisable(self):
        # config=None : le service instancie un UserConfig réel (persistance
        # propre via fichier JSON, indépendante de pyRevit). Le service doit
        # rester utilisable sans lever, quel que soit l'environnement.
        service = NamingService(doc=None, config=None)
        try:
            rows = [{'Name': 'X', 'Prefix': '', 'Suffix': ''}]
            service.save('sheet', service.build_pattern(rows), rows)
            service.load('sheet')
            service.has_saved('sheet')
        except Exception as e:
            self.fail('NamingService(config=None) a leve: {!r}'.format(e))


if __name__ == '__main__':
    unittest.main()
