# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import io
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
# 418.extension/lib (tests -> pushbutton -> Audit.panel -> 418.tab -> 418.extension)
_SHARED_LIB = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..', 'lib'))
if _SHARED_LIB not in sys.path:
    sys.path.insert(0, _SHARED_LIB)
# Dossier du bouton (pour 'from config...')
# Meme racine que pyRevit expose : <bouton>/lib.
_BUTTON_LIB = os.path.abspath(os.path.join(_HERE, '..', 'lib'))
if _BUTTON_LIB not in sys.path:
    sys.path.insert(0, _BUTTON_LIB)

from config.AuditRules import AuditRules, DEFAULTS
from models import OK, A_REVOIR, CRITIQUE


class TestAuditRules(unittest.TestCase):

    def test_data_vide_donne_tous_les_defauts(self):
        r = AuditRules(data={})
        self.assertEqual(r.score_points()[u'critique'], 10)
        self.assertEqual(r.score_points()[u'a_revoir'], 4)
        self.assertEqual(r.score_poids()[u'purge'], 0.6)
        self.assertEqual(r.score_volume()[u'max'], 8)
        self.assertIn(u'dupliqu', r.mots_critiques())
        self.assertEqual(r.vue_regex(), DEFAULTS[u'nommage'][u'vue_regex'])
        self.assertEqual(r.purge_gravite(), A_REVOIR)
        self.assertEqual(r.cad_gravite_import(), CRITIQUE)
        self.assertEqual(r.cad_gravite_lien(), A_REVOIR)

    def test_remplacement_par_section(self):
        # On ne surcharge que 'score' ; les autres sections gardent leurs défauts.
        r = AuditRules(data={u'score': {
            u'points_critique': 50, u'points_a_revoir': 1,
            u'poids_theme': {u'cad': 2.0},
            u'volume_facteur': 0.0, u'volume_max': 0}})
        self.assertEqual(r.score_points()[u'critique'], 50)
        self.assertEqual(r.score_poids().get(u'cad'), 2.0)
        # section nommage absente -> défaut
        self.assertEqual(r.vue_regex(), DEFAULTS[u'nommage'][u'vue_regex'])
        self.assertIn(u'dupliqu', r.mots_critiques())

    def test_mapping_gravite(self):
        r = AuditRules(data={u'purge': {u'gravite': u'critique'},
                             u'cad': {u'gravite_import_explose': u'a_revoir',
                                      u'gravite_lien': u'ok'}})
        self.assertEqual(r.purge_gravite(), CRITIQUE)
        self.assertEqual(r.cad_gravite_import(), A_REVOIR)
        self.assertEqual(r.cad_gravite_lien(), OK)

    def test_gravite_inconnue_retombe_sur_defaut(self):
        r = AuditRules(data={u'purge': {u'gravite': u'bizarre'}})
        self.assertEqual(r.purge_gravite(), A_REVOIR)

    def test_mots_critiques_normalises_en_minuscules(self):
        r = AuditRules(data={u'avertissements': {u'mots_critiques': [u'DUPLIQU', u'FooBar']}})
        self.assertEqual(r.mots_critiques(), [u'dupliqu', u'foobar'])

    def test_regex_nommage_surchargeables(self):
        r = AuditRules(data={u'nommage': {u'vue_regex': u'^Z_', u'famille_regex': u'^F_'}})
        self.assertEqual(r.vue_regex(), u'^Z_')
        self.assertEqual(r.famille_regex(), u'^F_')

    def test_chemin_inexistant_donne_defauts(self):
        r = AuditRules(chemin=os.path.join(_HERE, 'inexistant_audit_rules.json'))
        self.assertEqual(r.score_points()[u'critique'], 10)

    def test_json_malforme_donne_defauts_sans_crash(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, 'audit_rules.json')
        with io.open(path, 'w', encoding='utf-8') as f:
            f.write(u'{ ceci n\'est pas du JSON valide ')
        r = AuditRules(chemin=path)
        self.assertEqual(r.score_points()[u'critique'], 10)
        self.assertEqual(r.purge_gravite(), A_REVOIR)


if __name__ == '__main__':
    unittest.main()
