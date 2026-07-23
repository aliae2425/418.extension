# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import shutil
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in os.sys.path:
    os.sys.path.insert(0, _SHARED_LIB)
_BUTTON = os.path.abspath(os.path.join(_HERE, '..'))
if _BUTTON not in os.sys.path:
    os.sys.path.insert(0, _BUTTON)

from lib.services.DestinationService import DestinationService


class FakeConfig(object):
    """Faux UserConfig en mémoire."""

    def __init__(self):
        self._store = {}

    def get(self, key, default=None):
        return self._store.get(key, default)

    def set(self, key, value):
        self._store[key] = value
        return True


class TestDestinationServiceSanitize(unittest.TestCase):
    def setUp(self):
        self.service = DestinationService(doc=None, config=FakeConfig())

    def test_sanitize_retire_caracteres_interdits(self):
        result = self.service.sanitize('a/b:c*?"<>|')
        for ch in '\\/:*?"<>|':
            self.assertNotIn(ch, result)

    def test_sanitize_tronque_a_180(self):
        result = self.service.sanitize('x' * 300)
        self.assertLessEqual(len(result), 180)

    def test_sanitize_vide_donne_untitled(self):
        self.assertEqual(self.service.sanitize(''), 'untitled')
        self.assertEqual(self.service.sanitize(None), 'untitled')


class TestDestinationServiceUniquePath(unittest.TestCase):
    def setUp(self):
        self.service = DestinationService(doc=None, config=FakeConfig())
        self.tmpdir = tempfile.mkdtemp(prefix='destservice_')

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_unique_path_suffixe_si_collision(self):
        path = os.path.join(self.tmpdir, 'fichier.pdf')
        with open(path, 'w') as f:
            f.write('x')

        result = self.service.unique_path(path)
        expected = os.path.join(self.tmpdir, 'fichier (1).pdf')
        self.assertEqual(result, expected)
        self.assertFalse(os.path.exists(result))

    def test_unique_path_sans_collision_inchange(self):
        path = os.path.join(self.tmpdir, 'absent.pdf')
        self.assertEqual(self.service.unique_path(path), path)

    def test_unique_path_double_collision(self):
        path = os.path.join(self.tmpdir, 'double.pdf')
        with open(path, 'w') as f:
            f.write('x')
        with open(os.path.join(self.tmpdir, 'double (1).pdf'), 'w') as f:
            f.write('x')

        result = self.service.unique_path(path)
        expected = os.path.join(self.tmpdir, 'double (2).pdf')
        self.assertEqual(result, expected)


class TestDestinationServiceFolder(unittest.TestCase):
    def setUp(self):
        self.config = FakeConfig()
        self.service = DestinationService(doc=None, config=self.config)

    def test_get_fallback_documents_exports(self):
        result = self.service.get()
        self.assertTrue(result)
        self.assertIn('Exports', result)

    def test_set_puis_get_round_trip(self):
        tmpdir = tempfile.mkdtemp(prefix='destservice_folder_')
        try:
            self.assertTrue(self.service.set(tmpdir))
            self.assertEqual(self.service.get(), tmpdir)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_ensure_cree_dossier_absent(self):
        parent = tempfile.mkdtemp(prefix='destservice_ensure_')
        try:
            target = os.path.join(parent, 'sous_dossier')
            self.assertFalse(os.path.exists(target))
            result = self.service.ensure(target)
            self.assertEqual(result, target)
            self.assertTrue(os.path.exists(target))
        finally:
            shutil.rmtree(parent, ignore_errors=True)

    def test_flags_create_subfolders_round_trip(self):
        self.assertFalse(self.service.get_create_subfolders())
        self.service.set_create_subfolders(True)
        self.assertTrue(self.service.get_create_subfolders())
        self.service.set_create_subfolders(False)
        self.assertFalse(self.service.get_create_subfolders())

    def test_flags_separate_formats_round_trip(self):
        self.assertFalse(self.service.get_separate_formats())
        self.service.set_separate_formats(True)
        self.assertTrue(self.service.get_separate_formats())


class TestDestinationServiceBuildExportPath(unittest.TestCase):
    def setUp(self):
        self.config = FakeConfig()
        self.service = DestinationService(doc=None, config=self.config)

    def test_build_export_path_utilise_pattern_et_extension(self):
        rows = [{'Name': 'Numero_Feuille', 'Prefix': '', 'Suffix': '-'}]
        tmpdir = tempfile.mkdtemp(prefix='destservice_build_')
        try:
            result = self.service.build_export_path(
                rows=rows, folder=tmpdir, ext='pdf')
            self.assertTrue(result.startswith(tmpdir))
            self.assertTrue(result.endswith('.pdf'))
            self.assertIn('Numero_Feuille', result)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_build_export_path_ensure_dir_cree_dossier(self):
        parent = tempfile.mkdtemp(prefix='destservice_build_ensure_')
        try:
            target_folder = os.path.join(parent, 'nouveau')
            rows = [{'Name': 'X', 'Prefix': '', 'Suffix': ''}]
            self.service.build_export_path(
                rows=rows, folder=target_folder, ext='pdf', ensure_dir=True)
            self.assertTrue(os.path.exists(target_folder))
        finally:
            shutil.rmtree(parent, ignore_errors=True)

    def test_build_export_path_unique_evite_collision(self):
        tmpdir = tempfile.mkdtemp(prefix='destservice_build_unique_')
        try:
            rows = [{'Name': 'X', 'Prefix': '', 'Suffix': ''}]
            first = self.service.build_export_path(
                rows=rows, folder=tmpdir, ext='pdf')
            with open(first, 'w') as f:
                f.write('x')
            second = self.service.build_export_path(
                rows=rows, folder=tmpdir, ext='pdf', unique=True)
            self.assertNotEqual(first, second)
            self.assertTrue(second.endswith(' (1).pdf'))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
