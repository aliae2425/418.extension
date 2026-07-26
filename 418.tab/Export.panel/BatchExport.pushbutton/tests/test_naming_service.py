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
    """Faux élément Revit : LookupParameter + .Parameters, + attributs
    directs (SheetNumber/Name) pour exercer les jetons spéciaux."""

    def __init__(self, values, sheet_number=None, name=None):
        self._values = dict(values or {})
        if sheet_number is not None:
            self.SheetNumber = sheet_number
        if name is not None:
            self.Name = name

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


class TestNamingServiceJetons(unittest.TestCase):
    """Nouveau système de nommage à jetons : `pattern` est une chaîne."""

    def setUp(self):
        self.service = NamingService(doc=None, config=FakeConfig())

    def test_jeton_numero(self):
        elem = FakeElement({}, sheet_number='A-101')
        self.assertEqual(self.service.resolve_for_element(elem, '{numero}'), 'A-101')

    def test_jeton_nom(self):
        elem = FakeElement({}, name='Plan Rez de chaussee')
        self.assertEqual(self.service.resolve_for_element(elem, '{nom}'), 'Plan Rez de chaussee')

    def test_jeton_nom_tiret(self):
        elem = FakeElement({}, name='Plan Rez de chaussee')
        self.assertEqual(
            self.service.resolve_for_element(elem, '{nom_tiret}'),
            'Plan-Rez-de-chaussee')

    def test_jeton_nom_underscore(self):
        elem = FakeElement({}, name='Plan Rez de chaussee')
        self.assertEqual(
            self.service.resolve_for_element(elem, '{nom_underscore}'),
            'Plan_Rez_de_chaussee')

    def test_jeton_date_annee_quatre_chiffres(self):
        result = self.service.resolve_for_element(None, '{date_annee}')
        self.assertTrue(re.match(r'^\d{4}$', result))

    def test_jeton_date_complete(self):
        result = self.service.resolve_for_element(None, '{date}')
        self.assertTrue(re.match(r'^\d{4}-\d{2}-\d{2}$', result))

    def test_jeton_param_nomme(self):
        elem = FakeElement({'Phase': 'DCE'})
        self.assertEqual(self.service.resolve_for_element(elem, '{param:Phase}'), 'DCE')

    def test_jeton_inconnu_devient_vide(self):
        elem = FakeElement({})
        self.assertEqual(self.service.resolve_for_element(elem, '{ce_jeton_n_existe_pas}'), '')

    def test_motif_mixte_numero_nom(self):
        elem = FakeElement({}, sheet_number='A-101', name='Plan RDC')
        self.assertEqual(
            self.service.resolve_for_element(elem, '{numero}-{nom}'),
            'A-101-Plan RDC')

    def test_elem_none_jetons_param_donnent_vide_mais_date_fonctionne(self):
        result = self.service.resolve_for_element(None, '{numero}_{date_jour}')
        self.assertTrue(re.match(r'^_\d{2}$', result))

    def test_pattern_liste_rows_toujours_supporte(self):
        """Compat : `pattern` peut toujours être une liste de rows (ancien
        système) -- convertie en chaîne à jetons puis résolue."""
        rows = [{'Name': 'Date: Année', 'Prefix': '', 'Suffix': ''}]
        elem = FakeElement({})
        result = self.service.resolve_for_element(elem, rows)
        self.assertTrue(re.match(r'^\d{4}$', result))

    def test_available_tokens_contient_les_jetons_speciaux(self):
        tokens = [t['token'] for t in self.service.available_tokens()]
        for attendu in ('{numero}', '{nom}', '{date}', '{param:NOM}', '{param_projet:NOM}'):
            self.assertIn(attendu, tokens)

    def test_available_tokens_porte_un_label_court(self):
        """`label` : nom court sans qualifier de source (la couleur du badge
        indique déjà l'origine) -- `{nom}` et `{projet_nom}` partagent
        volontairement le même label 'nom'."""
        entrees = self.service.available_tokens()
        for entree in entrees:
            self.assertIn('label', entree)
            self.assertTrue(entree['label'])

        par_token = dict((e['token'], e['label']) for e in entrees)
        self.assertEqual(par_token['{numero}'], 'numéro')
        self.assertEqual(par_token['{nom}'], 'nom')
        self.assertEqual(par_token['{projet_nom}'], 'nom')
        self.assertEqual(par_token['{date_annee}'], 'année')


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

    def test_round_trip_save_load_motif_chaine_sans_rows(self):
        """Nouveau système : `save(kind, pattern)` sans rows -- `load` doit
        retourner le même pattern, et `has_saved` doit le reconnaître même
        si `rows` reste vide (pas de dépendance à `rows` pour ce diagnostic)."""
        pattern = '{numero}_{nom}_{param:Phase}'
        self.service.save('sheet', pattern)

        loaded_pattern, loaded_rows = self.service.load('sheet')
        self.assertEqual(loaded_pattern, pattern)
        self.assertEqual(loaded_rows, [])
        self.assertTrue(self.service.has_saved('sheet'))

    def test_round_trip_preset(self):
        self.assertTrue(self.service.save_preset('Standard PDF', '{numero}_{nom}'))
        presets = self.service.list_presets()
        self.assertEqual(len(presets), 1)
        self.assertEqual(presets[0]['name'], 'Standard PDF')
        self.assertEqual(presets[0]['pattern'], '{numero}_{nom}')

        self.assertTrue(self.service.save_preset('Autre', '{titre}'))
        self.assertEqual(len(self.service.list_presets()), 2)

        self.assertTrue(self.service.delete_preset('Standard PDF'))
        presets = self.service.list_presets()
        self.assertEqual(len(presets), 1)
        self.assertEqual(presets[0]['name'], 'Autre')

    def test_delete_preset_absent_retourne_false(self):
        self.assertFalse(self.service.delete_preset('Inexistant'))


if __name__ == '__main__':
    unittest.main()
