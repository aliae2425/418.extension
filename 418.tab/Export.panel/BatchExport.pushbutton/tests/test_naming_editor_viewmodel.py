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
    NamingEditorViewModel, TokenItemVM, SourceItemVM,
)


class FakeNamingService(object):
    """Faux NamingService, mode jetons : `load` renvoie un pattern chaîne
    fixe (contrat `(pattern, rows)`, rows toujours `[]` côté nouveau
    système), `save` capture ses arguments, `available_tokens` réplique le
    contrat du vrai service (cf. NamingService.available_tokens -> inclut
    désormais 'source')."""

    def __init__(self, pattern=u'{numero}_{nom}'):
        self._pattern = pattern
        self.save_calls = []

    def load(self, kind):
        return (self._pattern, [])

    def save(self, kind, pattern, rows=None):
        self.save_calls.append((kind, pattern, rows))
        self._pattern = pattern
        return True

    def available_tokens(self):
        return [
            {'token': '{date}', 'desc': 'Date du jour', 'source': 'systeme', 'label': 'date'},
            {'token': '{numero}', 'desc': 'Numéro de feuille', 'source': 'feuille', 'label': 'numéro'},
            {'token': '{nom}', 'desc': 'Nom de la feuille', 'source': 'feuille', 'label': 'nom'},
            {'token': '{titre}', 'desc': 'Titre du carnet (jeu)', 'source': 'jeu', 'label': 'titre'},
        ]

    def project_param_tokens(self):
        return [
            {'token': '{param_projet:Client}', 'label': 'Client',
             'desc': 'Projet — ACME', 'source': 'projet', 'value': 'ACME'},
        ]

    def resolve_project_values(self, pattern):
        # Aperçu « projet seulement » : substitue {param_projet:Client} par sa
        # valeur, laisse tout autre jeton littéral.
        return (pattern or u'').replace(u'{param_projet:Client}', u'ACME')


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

    def test_apercu_laisse_les_jetons_non_projet_litteraux(self):
        # « Projet seulement » : {numero}/{nom} restent littéraux dans l'aperçu.
        vm = NamingEditorViewModel('sheet', naming_service=FakeNamingService(pattern=u'{numero}'))
        self.assertEqual(vm.Apercu, u'{numero}')
        vm.Pattern = u'{numero}_{nom}'
        self.assertEqual(vm.Apercu, u'{numero}_{nom}')

    def test_apercu_resout_la_valeur_des_params_projet(self):
        vm = NamingEditorViewModel('sheet', naming_service=FakeNamingService(pattern=u''))
        vm.Pattern = u'{numero}_{param_projet:Client}'
        # Seul le param projet est résolu en valeur ; {numero} reste littéral.
        self.assertEqual(vm.Apercu, u'{numero}_ACME')

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

    def test_available_tokens_fusionne_les_params_projet_dynamiques(self):
        """AvailableTokens = jetons statiques + params projet dynamiques
        (project_param_tokens())."""
        vm = NamingEditorViewModel('sheet', naming_service=FakeNamingService())
        jetons = [t.token for t in vm.AvailableTokens]
        self.assertIn(u'{param_projet:Client}', jetons)

    def test_available_tokens_porte_la_source(self):
        vm = NamingEditorViewModel('sheet', naming_service=FakeNamingService())
        par_token = dict((t.token, t.source) for t in vm.AvailableTokens)
        self.assertEqual(par_token['{date}'], u'systeme')
        self.assertEqual(par_token['{numero}'], u'feuille')
        self.assertEqual(par_token['{titre}'], u'jeu')
        self.assertEqual(par_token['{param_projet:Client}'], u'projet')

    def test_available_tokens_porte_une_couleur_brush(self):
        vm = NamingEditorViewModel('sheet', naming_service=FakeNamingService())
        par_token = dict((t.token, t.CouleurBrush) for t in vm.AvailableTokens)
        self.assertEqual(par_token['{date}'], u'MediumGrayBrush')
        self.assertEqual(par_token['{numero}'], u'AccentBrush')
        self.assertEqual(par_token['{titre}'], u'SuccessBrush')
        self.assertEqual(par_token['{param_projet:Client}'], u'WarningBrush')

    def test_available_tokens_porte_un_label_court(self):
        """`.label` : nom court affiché sur le badge (sans qualifier de
        source). Pour un param projet, le label est le nom réel du paramètre."""
        vm = NamingEditorViewModel('sheet', naming_service=FakeNamingService())
        par_token = dict((t.token, t.label) for t in vm.AvailableTokens)
        self.assertEqual(par_token['{numero}'], u'numéro')
        self.assertEqual(par_token['{nom}'], u'nom')
        self.assertEqual(par_token['{titre}'], u'titre')
        self.assertEqual(par_token['{param_projet:Client}'], u'Client')


class TestNamingEditorViewModelFiltreSource(unittest.TestCase):
    def setUp(self):
        self.vm = NamingEditorViewModel('sheet', naming_service=FakeNamingService())

    def test_filtre_source_defaut_est_tout(self):
        self.assertEqual(self.vm.FiltreSource, u'tout')

    def test_tokens_filtres_tout_retourne_tous_les_tokens(self):
        self.assertEqual(len(self.vm.TokensFiltres), len(self.vm.AvailableTokens))

    def test_tokens_filtres_selon_systeme(self):
        self.vm.FiltreSource = u'systeme'
        jetons = [t.token for t in self.vm.TokensFiltres]
        self.assertEqual(jetons, [u'{date}'])

    def test_tokens_filtres_selon_feuille(self):
        self.vm.FiltreSource = u'feuille'
        jetons = [t.token for t in self.vm.TokensFiltres]
        self.assertEqual(set(jetons), {u'{numero}', u'{nom}'})

    def test_tokens_filtres_selon_jeu(self):
        self.vm.FiltreSource = u'jeu'
        jetons = [t.token for t in self.vm.TokensFiltres]
        self.assertEqual(jetons, [u'{titre}'])

    def test_tokens_filtres_selon_projet(self):
        self.vm.FiltreSource = u'projet'
        jetons = [t.token for t in self.vm.TokensFiltres]
        self.assertEqual(jetons, [u'{param_projet:Client}'])

    def test_filtre_source_valeur_none_replie_sur_tout(self):
        self.vm.FiltreSource = u'jeu'
        self.vm.FiltreSource = None
        self.assertEqual(self.vm.FiltreSource, u'tout')
        self.assertEqual(len(self.vm.TokensFiltres), len(self.vm.AvailableTokens))

    def test_sources_disponibles_expose_des_sourceitemvm(self):
        sources = self.vm.SourcesDisponibles
        self.assertTrue(len(sources) > 0)
        for s in sources:
            self.assertIsInstance(s, SourceItemVM)
            self.assertTrue(s.valeur)
            self.assertTrue(s.libelle)
        valeurs = [s.valeur for s in sources]
        self.assertIn(u'tout', valeurs)
        self.assertIn(u'systeme', valeurs)
        self.assertIn(u'feuille', valeurs)
        self.assertIn(u'jeu', valeurs)
        self.assertIn(u'projet', valeurs)

    def test_tokens_filtres_vide_sans_service(self):
        self.vm._naming_service = None
        self.vm.FiltreSource = u'feuille'
        self.assertEqual(self.vm.TokensFiltres, [])


class TestNamingEditorViewModelInsererToken(unittest.TestCase):
    def test_inserer_token_ajoute_en_fin_de_motif(self):
        vm = NamingEditorViewModel('sheet', naming_service=FakeNamingService(pattern=u'{numero}'))
        vm.inserer_token(u'_{nom}')
        self.assertEqual(vm.Pattern, u'{numero}_{nom}')

    def test_inserer_token_vide_ne_change_rien(self):
        vm = NamingEditorViewModel('sheet', naming_service=FakeNamingService(pattern=u'{numero}'))
        vm.inserer_token(u'')
        self.assertEqual(vm.Pattern, u'{numero}')


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

        vm = NamingEditorViewModel('sheet', naming_service=ServiceQuiLeve())
        self.assertFalse(vm.enregistrer())


class TestTokenItemVMEtSourceItemVM(unittest.TestCase):
    def test_tokenitemvm_valeurs_none_deviennent_chaine_vide(self):
        item = TokenItemVM(None, None, None)
        self.assertEqual(item.token, u'')
        self.assertEqual(item.desc, u'')
        self.assertEqual(item.source, u'')

    def test_tokenitemvm_source_inconnue_replie_sur_couleur_defaut(self):
        item = TokenItemVM(u'{x}', u'desc', u'source_bidon')
        self.assertEqual(item.CouleurBrush, u'AccentBrush')

    def test_tokenitemvm_label_explicite(self):
        item = TokenItemVM(u'{numero}', u'desc', u'feuille', u'numéro')
        self.assertEqual(item.label, u'numéro')
        # Le jeton complet reste inchangé et distinct du label affiché.
        self.assertEqual(item.token, u'{numero}')

    def test_tokenitemvm_label_absent_replie_sur_token(self):
        """Compat : un ancien contrat de service sans clé 'label' ne doit
        jamais produire un badge vide -- repli sur `.token`."""
        item = TokenItemVM(u'{numero}', u'desc', u'feuille')
        self.assertEqual(item.label, u'{numero}')

    def test_sourceitemvm_valeurs_none_deviennent_chaine_vide(self):
        item = SourceItemVM(None, None)
        self.assertEqual(item.valeur, u'')
        self.assertEqual(item.libelle, u'')


if __name__ == '__main__':
    unittest.main()
