# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import io
import json
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

os.environ['PY418_CONFIG_DIR'] = tempfile.mkdtemp(prefix='418test_')

from lib.services.ProfileService import ProfileService, NOM_DEFAUT, DEFAUT
from lib.viewmodels.MainViewModel import MainViewModel


class FakeConfig(object):
    """Faux UserConfig en mémoire (même contrat get/set)."""

    def __init__(self, store=None):
        self._store = dict(store or {})

    def get(self, key, default=None):
        return self._store.get(key, default)

    def set(self, key, value):
        self._store[key] = value
        return True


class TestProfileService(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp(prefix='418profils_')
        self.cfg = FakeConfig({
            'pattern_sheet': u'{numero}-{nom}',
            'pdf_setup_name': u'PDA_Export',
            'create_subfolders': u'1',
            # Hors profil : ne doit jamais être écrit ni relu.
            'pathdossier': u'C:\\local',
            'jeux_badges': u'{}',
            'manual_pdf_combine_title': u'Un export precis',
        })
        self.svc = ProfileService(config=self.cfg, dossier=self.dossier)

    def tearDown(self):
        shutil.rmtree(self.dossier, ignore_errors=True)

    def test_aller_retour_enregistrer_puis_appliquer(self):
        self.svc.save(u'Agence')
        self.assertEqual([NOM_DEFAUT, u'Agence'], self.svc.list())

        # Réglages modifiés depuis : appliquer le profil doit les restaurer.
        self.cfg.set('pattern_sheet', u'autre')
        self.cfg.set('pdf_setup_name', u'autre')
        self.svc.apply(u'Agence')
        self.assertEqual(u'{numero}-{nom}', self.cfg.get('pattern_sheet'))
        self.assertEqual(u'PDA_Export', self.cfg.get('pdf_setup_name'))

    def test_cles_hors_profil_exclues(self):
        snap = self.svc.snapshot()
        for cle in ('pathdossier', 'jeux_badges', 'manual_pdf_combine_title'):
            self.assertNotIn(cle, snap)
        self.assertIn('pattern_sheet', snap)

    def test_accents_conserves(self):
        self.cfg.set('pattern_set', u'{param_projet:Numéro de projet}')
        chemin = self.svc.save(u'Été')
        with io.open(chemin, 'r', encoding='utf-8') as f:
            self.assertIn(u'Numéro', f.read())
        self.assertEqual([NOM_DEFAUT, u'Été'], self.svc.list())

    def test_import_filtre_les_cles_inconnues(self):
        externe = os.path.join(self.dossier, '..', 'Recu.json')
        with io.open(externe, 'w', encoding='utf-8') as f:
            f.write(json.dumps({
                'pattern_sheet': u'{numero}',
                'pathdossier': u'C:\\chez_quelqu_un_dautre',
                'nimporte_quoi': 42,
            }, ensure_ascii=False))
        try:
            nom = self.svc.importer(externe)
            self.assertEqual(u'Recu', nom)
            self.svc.apply(nom)
            self.assertEqual(u'{numero}', self.cfg.get('pattern_sheet'))
            # La destination locale n'a PAS été écrasée par le fichier reçu.
            self.assertEqual(u'C:\\local', self.cfg.get('pathdossier'))
        finally:
            os.remove(externe)

    def test_import_fichier_sans_cle_connue_leve(self):
        externe = os.path.join(self.dossier, '..', 'Vide.json')
        with io.open(externe, 'w', encoding='utf-8') as f:
            f.write(u'{"rien": 1}')
        try:
            self.assertRaises(ValueError, self.svc.importer, externe)
        finally:
            os.remove(externe)

    def test_supprimer(self):
        self.svc.save(u'Agence')
        self.svc.delete(u'Agence')
        self.assertEqual([NOM_DEFAUT], self.svc.list())
        # Supprimer un profil absent ne lève pas.
        self.svc.delete(u'Agence')


class TestProfilDefaut(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp(prefix='418profils_')
        self.cfg = FakeConfig({'pattern_sheet': u'autre chose',
                               'pdf_setup_name': u'PDA_Export'})
        self.svc = ProfileService(config=self.cfg, dossier=self.dossier)

    def tearDown(self):
        shutil.rmtree(self.dossier, ignore_errors=True)

    def test_toujours_present_et_en_tete(self):
        self.assertEqual([NOM_DEFAUT], self.svc.list())
        self.svc.save(u'AAA')
        self.assertEqual(NOM_DEFAUT, self.svc.list()[0])

    def test_applique_nommage_minimal_et_setups_revit(self):
        self.svc.apply(NOM_DEFAUT)
        self.assertEqual(u'{numero}_{nom}', self.cfg.get('pattern_sheet'))
        self.assertEqual(u'{titre}', self.cfg.get('pattern_set'))
        # Setups vides -> Revit utilise ses réglages par défaut.
        self.assertEqual(u'', self.cfg.get('pdf_setup_name'))
        self.assertEqual(u'', self.cfg.get('dwg_setup_name'))

    def test_indelebile_et_nom_reserve(self):
        self.assertRaises(ValueError, self.svc.delete, NOM_DEFAUT)
        self.assertRaises(ValueError, self.svc.save, NOM_DEFAUT)
        self.assertEqual([NOM_DEFAUT], self.svc.list())

    def test_import_dun_fichier_homonyme_est_decale(self):
        externe = os.path.join(self.dossier, '..', NOM_DEFAUT + '.json')
        with io.open(externe, 'w', encoding='utf-8') as f:
            f.write(json.dumps({'pattern_sheet': u'{nom}'}, ensure_ascii=False))
        try:
            nom = self.svc.importer(externe)
            self.assertNotEqual(NOM_DEFAUT, nom)
            self.assertIn(nom, self.svc.list())
            # Le vrai « Défaut » est intact.
            self.svc.apply(NOM_DEFAUT)
            self.assertEqual(DEFAUT['pattern_sheet'],
                             self.cfg.get('pattern_sheet'))
        finally:
            os.remove(externe)


class TestMainViewModelProfils(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp(prefix='418profils_')
        self.cfg = FakeConfig({'pattern_sheet': u'{numero}',
                               'pdf_setup_name': u'A'})
        self.vm = MainViewModel(
            doc=None, config=self.cfg,
            profile_service=ProfileService(config=self.cfg,
                                           dossier=self.dossier))

    def tearDown(self):
        shutil.rmtree(self.dossier, ignore_errors=True)

    def test_choisir_un_profil_lapplique(self):
        self.vm.enregistrer_profil(u'A')
        self.assertEqual([NOM_DEFAUT, u'A'], self.vm.Profils)
        self.assertEqual(u'A', self.vm.ProfilActif)

        self.cfg.set('pdf_setup_name', u'B')
        self.vm.enregistrer_profil(u'B')

        self.vm.ProfilActif = u'A'          # setter -> applique
        self.assertEqual(u'A', self.cfg.get('pdf_setup_name'))

    def test_supprimer_bascule_sur_un_autre_profil(self):
        self.vm.enregistrer_profil(u'A')
        self.vm.supprimer_profil()
        self.assertEqual([NOM_DEFAUT], self.vm.Profils)
        # Un profil est toujours chargé derrière : jamais de ComboBox vide.
        self.assertEqual(NOM_DEFAUT, self.vm.ProfilActif)
        self.assertEqual(DEFAUT['pattern_sheet'], self.cfg.get('pattern_sheet'))

    def test_profil_defaut_non_supprimable(self):
        self.vm.ProfilActif = NOM_DEFAUT
        self.vm.supprimer_profil()
        self.assertEqual([NOM_DEFAUT], self.vm.Profils)
        self.assertEqual(NOM_DEFAUT, self.vm.ProfilActif)
        self.assertIn(u'non supprimé', self.vm.StatusText)

    def test_profil_illisible_ne_leve_pas(self):
        with io.open(os.path.join(self.dossier, 'Casse.json'), 'w',
                     encoding='utf-8') as f:
            f.write(u'pas du json')
        self.vm.ProfilActif = u'Casse'
        self.assertIn(u'non appliqué', self.vm.StatusText)


if __name__ == '__main__':
    unittest.main()
