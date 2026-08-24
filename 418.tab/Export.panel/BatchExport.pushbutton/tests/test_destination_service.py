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
# Meme racine que pyRevit expose : <bouton>/lib.
_BUTTON_LIB = os.path.abspath(os.path.join(_HERE, '..', 'lib'))
if _BUTTON_LIB not in os.sys.path:
    os.sys.path.insert(0, _BUTTON_LIB)

# Isole la persistance UserConfig dans un dossier temporaire (jamais le config réel).
import tempfile as _tf
os.environ['PY418_CONFIG_DIR'] = _tf.mkdtemp(prefix='418test_')

from services.DestinationService import DestinationService


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


class TestDestinationServiceFlagsRobustes(unittest.TestCase):
    """Les flags de séparation doivent être lus de façon ROBUSTE : la valeur
    persistée peut revenir de pyRevit sous diverses représentations selon la
    sérialisation ('1', 1, True, '"1"', 'true'...). Une comparaison stricte
    `str(val) == '1'` casse pour True/'"1"'/'true' -> séparation non appliquée
    alors que l'utilisateur a activé le toggle (cause candidate du bug #2)."""

    def _svc(self, raw_sub, raw_sep):
        cfg = FakeConfig()
        cfg.set('create_subfolders', raw_sub)
        cfg.set('separate_format_folders', raw_sep)
        return DestinationService(doc=None, config=cfg)

    def test_valeurs_vraies_diverses(self):
        for v in (u'1', 1, True, u'"1"', u'true', u'True', u'YES', u' 1 '):
            svc = self._svc(v, v)
            self.assertTrue(svc.get_create_subfolders(), 'sub pour %r' % (v,))
            self.assertTrue(svc.get_separate_formats(), 'sep pour %r' % (v,))

    def test_valeurs_fausses_diverses(self):
        for v in (u'0', 0, False, u'', None, u'"0"', u'false', u'no'):
            svc = self._svc(v, v)
            self.assertFalse(svc.get_create_subfolders(), 'sub pour %r' % (v,))
            self.assertFalse(svc.get_separate_formats(), 'sep pour %r' % (v,))

    def test_absent_par_defaut_faux(self):
        svc = DestinationService(doc=None, config=FakeConfig())
        self.assertFalse(svc.get_create_subfolders())
        self.assertFalse(svc.get_separate_formats())


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


if __name__ == '__main__':
    unittest.main()
