# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
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

from lib.services import reperage
from lib.viewmodels.CoupesPageVM import CoupesPageVM
from lib.viewmodels.MainViewModel import MainViewModel

_TYPE = 42


class _ServiceFactice(object):
    """Le contrat que l'onglet attend d'un FiltresService.

    « Coupe AA » est sur A01 (jeu PC, avec PDR), « Façade Sud » sur A02 (même
    jeu, avec PDR), « Coupe libre » n'est posée sur aucune feuille.
    """

    def __init__(self):
        self.recu = None

    def collecter_coupes(self):
        return [{'id': 1, 'nom': u'Coupe AA', 'type': 'Section',
                 'feuille': u'A01', 'jeu': u'PC'},
                {'id': 2, 'nom': u'Façade Sud', 'type': 'Elevation',
                 'feuille': u'A02', 'jeu': u'PC'},
                {'id': 3, 'nom': u'Coupe libre', 'type': 'Section',
                 'feuille': u'', 'jeu': u''}]

    def collecter_filtres(self):
        return []

    def types_de_plan(self):
        return [{'id': _TYPE, 'nom': u'Plan de repérage'},
                {'id': 7, 'nom': u'Plan de niveau'}]

    def collecter_pdr(self, type_id):
        if int(type_id) != _TYPE:
            return []
        return [{'id': 11, 'nom': u'PDR 01', 'feuille': u'A01', 'jeu': u'PC'},
                {'id': 12, 'nom': u'PDR 02', 'feuille': u'A02', 'jeu': u'PC'},
                {'id': 13, 'nom': u'PDR 10', 'feuille': u'B01', 'jeu': u'DCE'}]

    def titre_document(self):
        return u'Projet test'

    def appliquer_reperage(self, cibles):
        self.recu = cibles
        return [u'%d plan(s) traité(s)' % len(cibles)]


class _ConfigFactice(object):
    """UserConfig réduit à ce que l'onglet utilise, valeurs stringifiées
    comme le vrai (`data/*.json` ne contient que des chaînes)."""

    def __init__(self, valeurs=None):
        self.valeurs = dict(valeurs or {})

    def get(self, key, default=None):
        return self.valeurs.get(key.lower(), default)

    def set(self, key, value):
        self.valeurs[key.lower()] = u'{}'.format(value)


def _page(config=None, service=None):
    service = service or _ServiceFactice()
    config = config if config is not None else _ConfigFactice(
        {'type_plan_reperage': u'%d' % _TYPE})
    return CoupesPageVM(service.collecter_coupes(), service=service,
                        config=config)


class TestReglageDuType(unittest.TestCase):
    def test_sans_type_memorise_aucun_plan(self):
        page = _page(config=_ConfigFactice())
        self.assertTrue(page.AucunPlan)
        self.assertEqual(page.Pdrs, [])

    def test_type_memorise_absent_du_modele_est_ignore(self):
        page = _page(config=_ConfigFactice({'type_plan_reperage': u'999'}))
        self.assertTrue(page.AucunPlan)

    def test_choisir_un_type_memorise_et_recharge(self):
        config = _ConfigFactice()
        page = _page(config=config)
        page.TypeChoisi = [t for t in page.Types if t.Id == _TYPE][0]
        self.assertEqual(config.get('type_plan_reperage'), u'%d' % _TYPE)
        self.assertEqual(len(page.Pdrs), 3)
        self.assertEqual(page.Resume, u'3 vues · 3 plans de repérage')


class TestReglesParDefaut(unittest.TestCase):
    def test_libelle_de_type_traduit(self):
        self.assertEqual([l.TypeVue for l in _page().Lignes],
                         [u'Coupe', u'Élévation', u'Coupe'])

    def test_defaut_est_le_plan_de_sa_feuille(self):
        ligne = _page().Lignes[0]
        self.assertEqual([r.Mode for r in ligne.Regles], [u'plan'])
        self.assertEqual(ligne.Regles[0].PlanChoisi, u'PDR 01')
        self.assertEqual(ligne.Resume, u'visible sur 1 plan')

    def test_coupe_hors_feuille_retombe_sur_par_jeu(self):
        ligne = _page().Lignes[2]
        self.assertEqual(ligne.Regles[0].Mode, u'jeu')
        # Sans jeu, « le jeu de la coupe » ne désigne aucun plan : le repère
        # sera masqué partout, et l'en-tête le dit.
        self.assertEqual(ligne.Resume, u'masquée sur tous les plans')

    def test_sans_plan_de_reperage_aucune_regle_ne_contraint(self):
        ligne = _page(config=_ConfigFactice()).Lignes[0]
        self.assertEqual(ligne.Regles[0].Mode, u'jeu')
        self.assertEqual(ligne.Resume, u'masquée sur tous les plans')


class TestEdition(unittest.TestCase):
    def test_ajouter_puis_retirer(self):
        ligne = _page().Lignes[0]
        ligne.ajouter()
        self.assertEqual(len(ligne.Regles), 2)
        ligne.retirer(ligne.Regles[1])
        self.assertEqual(len(ligne.Regles), 1)

    def test_tout_retirer_laisse_la_coupe_libre(self):
        ligne = _page().Lignes[0]
        ligne.effacer()
        self.assertFalse(ligne.ARegles)
        self.assertEqual(ligne.Resume,
                         u'aucune règle · visible sur tous les plans')

    def test_par_jeu_prend_le_jeu_de_la_coupe_par_defaut(self):
        ligne = _page().Lignes[0]
        regle = ligne.Regles[0]
        regle.ModeChoisi = [m for m in regle.Modes if m.Cle == u'jeu'][0]
        self.assertEqual(regle.JeuChoisi, reperage.JEU_DE_LA_COUPE)
        # Le jeu PC porte deux plans : le repère apparaît sur les deux.
        self.assertEqual(ligne.Resume, u'visible sur 2 plans')

    def test_passer_de_plan_a_jeu_jette_la_cible(self):
        regle = _page().Lignes[0].Regles[0]
        self.assertEqual(regle.regle().cibles, [u'PDR 01'])
        regle.ModeChoisi = [m for m in regle.Modes if m.Cle == u'jeu'][0]
        self.assertEqual(regle.regle().cibles, [])

    def test_passer_de_plan_a_specifique_garde_la_cible(self):
        regle = _page().Lignes[0].Regles[0]
        regle.PlanChoisi = u'PDR 02'
        regle.ModeChoisi = [m for m in regle.Modes
                            if m.Cle == u'specifique'][0]
        self.assertEqual(regle.regle().cibles, [u'PDR 02'])
        self.assertEqual([c.Nom for c in regle.Cibles if c.Coche], [u'PDR 02'])

    def test_cocher_une_case_alimente_la_regle(self):
        regle = _page().Lignes[0].Regles[0]
        regle.ModeChoisi = [m for m in regle.Modes
                            if m.Cle == u'specifique'][0]
        for cible in regle.Cibles:
            if cible.Nom in (u'PDR 02', u'PDR 10'):
                cible.Coche = True
        # PDR 01 était la cible du mode `plan`, la case est donc déjà cochée :
        # changer de mode ne perd pas le choix précédent.
        self.assertEqual(regle.regle().cibles,
                         [u'PDR 01', u'PDR 02', u'PDR 10'])
        self.assertEqual(regle.Resume,
                         u'3 plans : PDR 01 · PDR 02 · PDR 10')

    def test_plusieurs_regles_cumulent_sans_doublon(self):
        ligne = _page().Lignes[0]
        ligne.ajouter()
        seconde = ligne.Regles[1]
        seconde.ModeChoisi = [m for m in seconde.Modes if m.Cle == u'jeu'][0]
        # règle 1 : PDR 01 ; règle 2 : le jeu PC = PDR 01 + PDR 02.
        self.assertEqual(ligne.Resume, u'visible sur 2 plans')


class TestPersistance(unittest.TestCase):
    def test_enregistrer_puis_relire(self):
        config = _ConfigFactice({'type_plan_reperage': u'%d' % _TYPE})
        page = _page(config=config)
        page.Lignes[0].effacer()
        page.Lignes[1].Regles[0].PlanChoisi = u'PDR 10'
        page.enregistrer()

        relu = _page(config=config)
        self.assertEqual(relu.Lignes[0].Regles, [])
        self.assertEqual(relu.Lignes[1].Regles[0].PlanChoisi, u'PDR 10')

    def test_les_regles_sont_rangees_par_document(self):
        config = _ConfigFactice({'type_plan_reperage': u'%d' % _TYPE})
        page = _page(config=config)
        page.enregistrer()
        stocke = json.loads(config.get('reperage'))
        self.assertEqual(list(stocke.keys()), [u'Projet test'])
        self.assertEqual(stocke[u'Projet test'][u'Coupe AA'],
                         [{'mode': u'plan', 'cibles': [u'PDR 01']}])


class TestApplication(unittest.TestCase):
    def test_sans_plan_rien_n_est_ecrit(self):
        service = _ServiceFactice()
        page = _page(config=_ConfigFactice(), service=service)
        messages = page.appliquer()
        self.assertIsNone(service.recu)
        self.assertIn(u'Aucun plan de repérage', messages[0])

    def test_appliquer_passe_les_visibles_plan_par_plan(self):
        service = _ServiceFactice()
        page = _page(service=service)
        # La coupe sans feuille n'est contrainte par rien d'utile : on la
        # libère pour vérifier qu'une coupe sans règle passe partout.
        page.Lignes[2].effacer()
        page.appliquer()
        visibles = dict((c['nom'], c['visibles']) for c in service.recu)
        self.assertEqual(visibles[u'PDR 01'],
                         [u'Coupe AA', u'Coupe libre'])
        self.assertEqual(visibles[u'PDR 02'],
                         [u'Façade Sud', u'Coupe libre'])
        self.assertEqual(visibles[u'PDR 10'], [u'Coupe libre'])
        # L'id de la vue suit : c'est ce que le service va chercher.
        self.assertEqual([c['id'] for c in service.recu], [11, 12, 13])


class TestMainViewModel(unittest.TestCase):
    def test_mode_initial_audit(self):
        self.assertEqual(MainViewModel().Mode, u'audit')

    def test_charger_alimente_l_onglet_coupes(self):
        vm = MainViewModel(service=_ServiceFactice(),
                           config=_ConfigFactice(
                               {'type_plan_reperage': u'%d' % _TYPE}))
        vm.charger()
        self.assertEqual(len(vm.CoupesVM.Lignes), 3)
        self.assertEqual(len(vm.CoupesVM.Pdrs), 3)

    def test_charger_sans_service_ne_casse_pas(self):
        vm = MainViewModel(config=_ConfigFactice())
        vm.charger()
        self.assertEqual(vm.CoupesVM.Lignes, [])
        self.assertEqual(vm.lancer(), [u'Service indisponible : rien n\'a '
                                       u'été écrit.'])


if __name__ == '__main__':
    unittest.main()
