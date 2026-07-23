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

from lib.viewmodels.NamingEditorViewModel import (
    NamingEditorViewModel, TokenItemVM, PresetItemVM,
)


class FakeNamingService(object):
    """Faux NamingService, mode jetons : `load` renvoie un pattern chaîne
    fixe (contrat `(pattern, rows)`, rows toujours `[]` côté nouveau
    système), `save` capture ses arguments, `available_tokens`/
    `list_presets`/`save_preset`/`delete_preset` répliquent le contrat du
    vrai service (cf. NamingService)."""

    def __init__(self, pattern=u'{numero}_{nom}', presets=None):
        self._pattern = pattern
        self._presets = list(presets or [])
        self.save_calls = []
        self.save_preset_calls = []
        self.delete_preset_calls = []

    def load(self, kind):
        return (self._pattern, [])

    def save(self, kind, pattern, rows=None):
        self.save_calls.append((kind, pattern, rows))
        self._pattern = pattern
        return True

    def available_tokens(self):
        return [
            {'token': '{numero}', 'desc': 'Numéro de feuille'},
            {'token': '{nom}', 'desc': 'Nom de la feuille'},
        ]

    def list_presets(self):
        return list(self._presets)

    def save_preset(self, name, pattern):
        self.save_preset_calls.append((name, pattern))
        self._presets = [p for p in self._presets if p.get('name') != name]
        self._presets.append({'name': name, 'pattern': pattern})
        return True

    def delete_preset(self, name):
        self.delete_preset_calls.append(name)
        before = len(self._presets)
        self._presets = [p for p in self._presets if p.get('name') != name]
        return len(self._presets) != before


class TestNamingEditorViewModelChargement(unittest.TestCase):
    def test_charge_le_pattern_depuis_le_service(self):
        service = FakeNamingService(pattern=u'{numero}_{nom}')
        vm = NamingEditorViewModel('sheet', naming_service=service)
        self.assertEqual(vm.Pattern, u'{numero}_{nom}')

    def test_titre_selon_kind(self):
        vm_sheet = NamingEditorViewModel('sheet', naming_service=FakeNamingService())
        vm_set = NamingEditorViewModel('set', naming_service=FakeNamingService())
        self.assertIn(u'feuilles', vm_sheet.Titre.lower())
        self.assertIn(u'carnets', vm_set.Titre.lower())

    def test_kind_invalide_replie_sur_sheet(self):
        vm = NamingEditorViewModel('bogus', naming_service=FakeNamingService())
        self.assertEqual(vm.Titre, u'Nommage des feuilles')

    def test_construction_sans_service_ne_leve_pas(self):
        vm = NamingEditorViewModel('sheet', naming_service=None)
        # Le VM instancie alors le VRAI NamingService (importable hors Revit,
        # backend UserConfig en no-op) -> pattern vide, mais pas de levée.
        self.assertEqual(vm.Pattern, u'')


class TestNamingEditorViewModelPattern(unittest.TestCase):
    def test_setter_pattern_deux_voies(self):
        vm = NamingEditorViewModel('sheet', naming_service=FakeNamingService(pattern=u''))
        vm.Pattern = u'{numero}-{date}'
        self.assertEqual(vm.Pattern, u'{numero}-{date}')

    def test_setter_pattern_valeur_none_devient_chaine_vide(self):
        vm = NamingEditorViewModel('sheet', naming_service=FakeNamingService(pattern=u'X'))
        vm.Pattern = None
        self.assertEqual(vm.Pattern, u'')

    def test_apercu_reflete_le_pattern_courant(self):
        vm = NamingEditorViewModel('sheet', naming_service=FakeNamingService(pattern=u'{numero}'))
        self.assertEqual(vm.Apercu, u'{numero}')
        vm.Pattern = u'{numero}_{nom}'
        self.assertEqual(vm.Apercu, u'{numero}_{nom}')

    def test_apercu_vide_sans_service(self):
        vm = NamingEditorViewModel('sheet', naming_service=None)
        vm._naming_service = None
        vm.Pattern = u''
        self.assertEqual(vm.Apercu, u'')


class TestNamingEditorViewModelAvailableTokens(unittest.TestCase):
    def test_available_tokens_exposes_des_tokenitemvm(self):
        vm = NamingEditorViewModel('sheet', naming_service=FakeNamingService())
        tokens = vm.AvailableTokens
        self.assertTrue(len(tokens) > 0)
        for t in tokens:
            self.assertIsInstance(t, TokenItemVM)
            self.assertTrue(t.token)

    def test_available_tokens_contient_numero_et_nom(self):
        vm = NamingEditorViewModel('sheet', naming_service=FakeNamingService())
        jetons = [t.token for t in vm.AvailableTokens]
        self.assertIn('{numero}', jetons)
        self.assertIn('{nom}', jetons)

    def test_available_tokens_vide_sans_service(self):
        vm = NamingEditorViewModel('sheet', naming_service=FakeNamingService())
        vm._naming_service = None
        self.assertEqual(vm.AvailableTokens, [])


class TestNamingEditorViewModelInsererToken(unittest.TestCase):
    def test_inserer_token_ajoute_en_fin_de_motif(self):
        vm = NamingEditorViewModel('sheet', naming_service=FakeNamingService(pattern=u'{numero}'))
        vm.inserer_token(u'_{nom}')
        self.assertEqual(vm.Pattern, u'{numero}_{nom}')

    def test_inserer_token_vide_ne_change_rien(self):
        vm = NamingEditorViewModel('sheet', naming_service=FakeNamingService(pattern=u'{numero}'))
        vm.inserer_token(u'')
        self.assertEqual(vm.Pattern, u'{numero}')


class TestNamingEditorViewModelPresets(unittest.TestCase):
    def setUp(self):
        self.service = FakeNamingService(
            pattern=u'{numero}',
            presets=[{'name': u'Standard', 'pattern': u'{numero}_{nom}'}],
        )
        self.vm = NamingEditorViewModel('sheet', naming_service=self.service)

    def test_presets_exposes_des_presetitemvm(self):
        presets = self.vm.Presets
        self.assertEqual(len(presets), 1)
        self.assertIsInstance(presets[0], PresetItemVM)
        self.assertEqual(presets[0].name, u'Standard')
        self.assertEqual(presets[0].pattern, u'{numero}_{nom}')

    def test_charger_preset_remplace_le_pattern(self):
        ok = self.vm.charger_preset(u'Standard')
        self.assertTrue(ok)
        self.assertEqual(self.vm.Pattern, u'{numero}_{nom}')
        self.assertEqual(self.vm.PresetSelectionne, u'Standard')

    def test_charger_preset_introuvable_retourne_false(self):
        ok = self.vm.charger_preset(u'Inconnu')
        self.assertFalse(ok)
        self.assertEqual(self.vm.Pattern, u'{numero}')

    def test_enregistrer_preset_appelle_le_service(self):
        self.vm.Pattern = u'{numero}-{date}'
        ok = self.vm.enregistrer_preset(u'Nouveau')
        self.assertTrue(ok)
        self.assertEqual(self.service.save_preset_calls, [(u'Nouveau', u'{numero}-{date}')])
        noms = [p.name for p in self.vm.Presets]
        self.assertIn(u'Nouveau', noms)

    def test_enregistrer_preset_nom_vide_retourne_false(self):
        ok = self.vm.enregistrer_preset(u'   ')
        self.assertFalse(ok)

    def test_supprimer_preset_appelle_le_service(self):
        ok = self.vm.supprimer_preset(u'Standard')
        self.assertTrue(ok)
        self.assertEqual(self.service.delete_preset_calls, [u'Standard'])
        self.assertEqual(self.vm.Presets, [])

    def test_supprimer_preset_introuvable_retourne_false(self):
        ok = self.vm.supprimer_preset(u'Inconnu')
        self.assertFalse(ok)


class TestNamingEditorViewModelEnregistrer(unittest.TestCase):
    def test_enregistrer_appelle_save_avec_le_pattern_courant(self):
        service = FakeNamingService(pattern=u'{numero}')
        vm = NamingEditorViewModel('sheet', naming_service=service)
        vm.Pattern = u'{numero}_{nom}'

        ok = vm.enregistrer()

        self.assertTrue(ok)
        self.assertEqual(len(service.save_calls), 1)
        kind, pattern, rows = service.save_calls[0]
        self.assertEqual(kind, 'sheet')
        self.assertEqual(pattern, u'{numero}_{nom}')

    def test_enregistrer_utilise_le_kind_set(self):
        service = FakeNamingService()
        vm = NamingEditorViewModel('set', naming_service=service)
        vm.enregistrer()
        kind, _pattern, _rows = service.save_calls[0]
        self.assertEqual(kind, 'set')

    def test_enregistrer_sans_service_ne_leve_pas_et_retourne_false(self):
        vm = NamingEditorViewModel('sheet', naming_service=FakeNamingService())
        vm._naming_service = None
        self.assertFalse(vm.enregistrer())

    def test_enregistrer_service_qui_leve_ne_leve_pas_et_retourne_false(self):
        class ServiceQuiLeve(object):
            def load(self, kind):
                return (u'', [])

            def save(self, kind, pattern, rows=None):
                raise RuntimeError('boom')

            def available_tokens(self):
                return []

            def list_presets(self):
                return []

        vm = NamingEditorViewModel('sheet', naming_service=ServiceQuiLeve())
        self.assertFalse(vm.enregistrer())


class TestTokenItemVMEtPresetItemVM(unittest.TestCase):
    def test_tokenitemvm_valeurs_none_deviennent_chaine_vide(self):
        item = TokenItemVM(None, None)
        self.assertEqual(item.token, u'')
        self.assertEqual(item.desc, u'')

    def test_presetitemvm_valeurs_none_deviennent_chaine_vide(self):
        item = PresetItemVM(None, None)
        self.assertEqual(item.name, u'')
        self.assertEqual(item.pattern, u'')


if __name__ == '__main__':
    unittest.main()
