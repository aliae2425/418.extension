# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import io
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

from lib.services.ExportOrchestrator import ExportOrchestrator, ExportAnnule


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


class TestCollisionFichierExistant(unittest.TestCase):
    """`_unique_with_ext` face à un fichier déjà présent : les 4 réponses du
    dialogue, et la mémorisation globale (la question n'est posée qu'une fois
    sauf pour « Oui » seul). Dialogue injecté via `_demander_collision` —
    pyrevit.forms est indisponible hors Revit."""

    def setUp(self):
        self.dossier = _tf.mkdtemp(prefix='418collision_')
        self.orch = ExportOrchestrator()
        self.appels = []

    def _repondre(self, *reponses):
        """Câble un faux dialogue qui rend `reponses` dans l'ordre."""
        suite = list(reponses)

        def cb(path):
            self.appels.append(path)
            return suite.pop(0) if suite else 'renommer_tous'

        self.orch._demander_collision = cb

    def _creer(self, nom):
        f = io.open(os.path.join(self.dossier, nom), 'w', encoding='utf-8')
        f.write(u'x')
        f.close()

    def test_fichier_absent_ne_demande_rien(self):
        self._repondre('arreter')
        path = self.orch._unique_with_ext(self.dossier, u'A101', 'pdf')
        self.assertEqual(path, os.path.join(self.dossier, u'A101.pdf'))
        self.assertEqual(self.appels, [])

    def test_oui_ecrase_ce_fichier_et_redemande_pour_le_suivant(self):
        self._creer(u'A101.pdf')
        self._creer(u'A102.pdf')
        self._repondre('ecraser', 'ecraser')
        p1 = self.orch._unique_with_ext(self.dossier, u'A101', 'pdf')
        p2 = self.orch._unique_with_ext(self.dossier, u'A102', 'pdf')
        self.assertEqual(p1, os.path.join(self.dossier, u'A101.pdf'))
        self.assertEqual(p2, os.path.join(self.dossier, u'A102.pdf'))
        self.assertEqual(len(self.appels), 2)  # « Oui » n'est pas mémorisé

    def test_oui_pour_tous_ne_demande_qu_une_fois(self):
        self._creer(u'A101.pdf')
        self._creer(u'A102.pdf')
        self._repondre('ecraser_tous')
        p1 = self.orch._unique_with_ext(self.dossier, u'A101', 'pdf')
        p2 = self.orch._unique_with_ext(self.dossier, u'A102', 'pdf')
        self.assertEqual(p1, os.path.join(self.dossier, u'A101.pdf'))
        self.assertEqual(p2, os.path.join(self.dossier, u'A102.pdf'))
        self.assertEqual(len(self.appels), 1)

    def test_non_puis_renommer_suffixe_et_vaut_pour_tous(self):
        self._creer(u'A101.pdf')
        self._creer(u'A102.pdf')
        self._repondre('renommer_tous')
        p1 = self.orch._unique_with_ext(self.dossier, u'A101', 'pdf')
        p2 = self.orch._unique_with_ext(self.dossier, u'A102', 'pdf')
        self.assertEqual(p1, os.path.join(self.dossier, u'A101 (1).pdf'))
        self.assertEqual(p2, os.path.join(self.dossier, u'A102 (1).pdf'))
        self.assertEqual(len(self.appels), 1)

    def test_non_puis_arreter_leve_export_annule(self):
        self._creer(u'A101.pdf')
        self._repondre('arreter')
        self.assertRaises(ExportAnnule, self.orch._unique_with_ext,
                          self.dossier, u'A101', 'pdf')

    def test_run_manual_annule_rend_false_et_ne_leve_pas(self):
        # `arreter` remonte jusqu'à run_manual, qui le convertit en False.
        self._creer(u'A101.pdf')
        self._repondre('arreter')
        feuille = FakeSheet(u'A101', u'RDC')
        vm = FakeSheet(u'A101', u'RDC')
        vm.ExportPdf, vm.ExportDwg, vm.Elem, vm.Numero = True, False, feuille, u'A101'
        self.orch._naming = FakeNaming({'sheet': u'{numero}'})
        res = self.orch.run_manual(None, [vm], destination=self.dossier)
        self.assertFalse(res)

    def test_sans_dialogue_disponible_renomme_jamais_ecrase(self):
        # Hors Revit, pyrevit.forms lève -> repli 'renommer_tous' : aucun
        # fichier existant n'est écrasé sans un oui explicite.
        self._creer(u'A101.pdf')
        path = self.orch._unique_with_ext(self.dossier, u'A101', 'pdf')
        self.assertEqual(path, os.path.join(self.dossier, u'A101 (1).pdf'))

    def test_politique_remise_a_zero_a_chaque_run(self):
        self.orch._politique_collision = 'ecraser_tous'
        self.orch.run_manual(None, [], destination=self.dossier)
        self.assertIsNone(self.orch._politique_collision)


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
