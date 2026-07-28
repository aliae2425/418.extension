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

import tempfile as _tf
os.environ['PY418_CONFIG_DIR'] = _tf.mkdtemp(prefix='418test_')

from lib.services.core.ExportOrchestrator import ExportOrchestrator


class FakeNaming(object):
    """Faux NamingService : `load(kind)` -> (pattern_chaine, []) ;
    `resolve_for_element` résout les jetons {titre}/{numero}/{nom} contre
    l'élément (comme le vrai NamingService pour ces jetons)."""

    def __init__(self, patterns):
        self._patterns = patterns  # {'sheet': '{numero}', 'set': '{titre}'}

    def load(self, kind):
        return (self._patterns.get(kind, u''), [])

    def resolve_for_element(self, elem, pattern):
        out = pattern or u''
        out = out.replace(u'{titre}', getattr(elem, 'Name', u'') or u'')
        out = out.replace(u'{numero}', getattr(elem, 'SheetNumber', u'') or u'')
        out = out.replace(u'{nom}', getattr(elem, 'Name', u'') or u'')
        return out


class FakeDest(object):
    def sanitize(self, name, replacement=u'_'):
        return name if name else u'untitled'


class FakeColl(object):
    def __init__(self, name):
        self.Name = name


class FakeSheet(object):
    def __init__(self, numero, name):
        self.SheetNumber = numero
        self.Name = name


class TestResolveName(unittest.TestCase):
    def setUp(self):
        self.orch = ExportOrchestrator()
        self.orch._dest = FakeDest()

    def test_carnet_resout_le_motif_set_en_titre_de_collection(self):
        # RÉGRESSION #3 : motif carnet à jetons -> nom = titre du jeu, PAS 'untitled'.
        self.orch._naming = FakeNaming({'set': u'{titre}'})
        nom = self.orch._resolve_name(FakeColl(u'Mon Carnet'), 'set', fallback=u'FB')
        self.assertEqual(nom, u'Mon Carnet')

    def test_carnet_motif_vide_utilise_le_fallback(self):
        self.orch._naming = FakeNaming({'set': u''})
        nom = self.orch._resolve_name(FakeColl(u'Carnet A'), 'set', fallback=u'Carnet A')
        self.assertEqual(nom, u'Carnet A')

    def test_carnet_resolution_vide_utilise_le_fallback_pas_untitled(self):
        # Motif présent mais résout vide (ex. titre vide) -> fallback, pas 'untitled'.
        self.orch._naming = FakeNaming({'set': u'{titre}'})
        nom = self.orch._resolve_name(FakeColl(u''), 'set', fallback=u'Jeu 1')
        self.assertEqual(nom, u'Jeu 1')

    def test_feuille_resout_le_motif_sheet(self):
        self.orch._naming = FakeNaming({'sheet': u'{numero}_{nom}'})
        nom = self.orch._resolve_name(FakeSheet(u'A101', u'RDC'), 'sheet', fallback=u'x')
        self.assertEqual(nom, u'A101_RDC')

    def test_sans_naming_service_utilise_le_fallback(self):
        self.orch._naming = None
        nom = self.orch._resolve_name(FakeColl(u'C'), 'set', fallback=u'FB')
        self.assertEqual(nom, u'FB')


class TestConfigInjection(unittest.TestCase):
    """RÉGRESSION #2 + #3 : l'orchestrateur DOIT lire les flags de séparation
    et les motifs de nommage depuis la config INJECTÉE (celle du VM), pas
    depuis une config propre '<absent>'. Reproduit le bug observé en Revit :
    le VM voit SousDossiers=True mais l'orchestrateur lisait '<absent>'."""

    def _shared_cfg(self):
        cfg = FakeConfigStore()
        # Valeurs écrites par le VM / la modale :
        cfg.set('create_subfolders', '1')
        cfg.set('separate_format_folders', '1')
        # Motif distinct du simple titre pour prouver qu'il est bien APPLIQUÉ
        # (et pas seulement le repli titre de collection) :
        cfg.set('pattern_set', 'CARNET_{titre}')
        return cfg

    def test_flags_separation_lus_depuis_config_injectee(self):
        import tempfile
        orch = ExportOrchestrator(config=self._shared_cfg())
        self.assertTrue(orch._dest.get_create_subfolders())
        self.assertTrue(orch._dest.get_separate_formats())
        # base = destination + <jeu> + <format> quand les flags sont vrais.
        orch._destination_override = tempfile.mkdtemp(prefix='418dest_')
        base = orch._get_destination_base('PDF', 'MonJeu')
        self.assertTrue(base.endswith(os.path.join('MonJeu', 'PDF')),
                        'base=%r' % (base,))

    def test_motif_carnet_lu_depuis_config_injectee(self):
        # NamingService injecté avec la même config -> load('set') = '{titre}'.
        cfg = self._shared_cfg()
        from lib.services.NamingService import NamingService
        orch = ExportOrchestrator(config=cfg)
        orch._naming = NamingService(config=cfg)
        nom = orch._resolve_name(FakeColl(u'02.1_Plans'), 'set', fallback=u'FB')
        # Motif 'CARNET_{titre}' appliqué -> distinct du repli titre nu.
        self.assertEqual(nom, u'CARNET_02.1_Plans')


class FakeConfigStore(object):
    def __init__(self):
        self._s = {}

    def get(self, k, d=None):
        return self._s.get(k, d)

    def set(self, k, v):
        self._s[k] = u"{}".format(v)
        return True


if __name__ == '__main__':
    unittest.main()
