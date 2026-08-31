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

from lib.services import reperage
from lib.viewmodels.ReperagePageVM import ReperagePageVM


def plan(nom, uid, feuille=u'', jeu=u'', type_vue=u'Plan de repérage'):
    return {'id': uid, 'uid': uid, 'nom': nom, 'type': type_vue,
            'feuille': feuille, 'jeu': jeu}


def coupe(nom, feuille=u'', jeu=u''):
    return {'nom': nom, 'feuille': feuille, 'jeu': jeu}


PLANS = [plan(u'PDR RDC', u'u1', u'A01', u'PC'),
         plan(u'PDR R+1', u'u2', u'A02', u'PC'),
         plan(u'Plan masse', u'u3', u'A10', u'DCE', type_vue=u'Plan d\'étage'),
         plan(u'PDR Détail', u'u4')]

COUPES = [coupe(u'Coupe AA', u'A01', u'PC'),
          coupe(u'Coupe BB', u'A02', u'PC'),
          coupe(u'Coupe ZZ')]


class ServiceFactice(object):
    """Le service tel que le VM l'attend, sans Revit."""

    def __init__(self, regles=None, poses=None, parametres=None):
        self._regles = regles or {}
        self._poses = poses or {}
        self._parametres = (parametres if parametres is not None
                            else {reperage.FEUILLE: 1, reperage.JEU: 2,
                                  reperage.NOM: 3})
        self.recu = None
        self.retraits = 0

    def lire_regles(self):
        return dict(self._regles)

    def filtres_poses(self):
        return dict(self._poses)

    def parametres(self):
        return dict(self._parametres)

    def appliquer(self, cibles):
        self.recu = cibles
        return [u'ok']

    def retirer_tout(self):
        self.retraits += 1
        return [u'0 filtre retiré.']


def page(service=None):
    return ReperagePageVM(PLANS, COUPES, service=service or ServiceFactice())


def cocher(vm, *noms):
    for item in vm.Items:
        item.IsSelected = item.Nom in noms


def mode(vm, cle):
    for entree in vm.Modes:
        if entree.Cle == cle:
            vm.ModeChoisi = entree
            return
    raise AssertionError(u'mode inconnu : %s' % cle)


class TestRienDeGereAuDepart(unittest.TestCase):
    """Aucun plan n'est géré d'office : l'outil ne décide pas à la place de
    l'utilisateur, et un premier « Appliquer » n'écrit donc aucun filtre."""

    def test_tous_les_plans_sont_listes_et_aucun_gere(self):
        vm = page()
        self.assertEqual(len(vm.Items), 4)
        self.assertFalse(any(it.Geree for it in vm.Items))
        for item in vm.Items:
            self.assertEqual(item.Phrase, u'affichage natif de Revit')

    def test_les_plans_hors_convention_restent_visibles(self):
        """Le type de vue ne DÉFINIT plus ce qu'est un plan de repérage : un
        plan d'étage reste dans la liste au lieu d'y être introuvable."""
        vm = page()
        self.assertIn(u'Plan masse', [it.Nom for it in vm.Items])

    def test_editeur_inactif_sans_selection(self):
        vm = page()
        self.assertFalse(vm.EditeurActif)
        self.assertIn(u'Sélectionne', vm.Entete)


class TestEditionSurLaSelection(unittest.TestCase):
    def test_un_plan_recoit_la_regle(self):
        vm = page()
        cocher(vm, u'PDR RDC')
        mode(vm, reperage.MODE_FEUILLE)
        item = vm.Items[0]
        self.assertTrue(item.Geree)
        self.assertEqual(item.Phrase, u'les coupes de la feuille A01')

    def test_la_regle_va_sur_TOUS_les_plans_selectionnes(self):
        """C'est ce qui rachète l'absence de pré-cochage : une décision pour
        quarante plans au lieu de quarante décisions."""
        vm = page()
        cocher(vm, u'PDR RDC', u'PDR R+1')
        mode(vm, reperage.MODE_JEU)
        self.assertEqual([it.Phrase for it in vm.Items[:2]],
                         [u'les coupes du jeu PC'] * 2)
        self.assertFalse(vm.Items[2].Geree)

    def test_mode_non_gere_retire_la_regle(self):
        vm = page()
        cocher(vm, u'PDR RDC')
        mode(vm, reperage.MODE_FEUILLE)
        mode(vm, reperage.MODE_AUCUN)
        self.assertFalse(vm.Items[0].Geree)
        self.assertEqual(vm.Items[0].Phrase, u'affichage natif de Revit')

    def test_jeu_nomme_puis_retour_au_jeu_du_plan(self):
        vm = page()
        cocher(vm, u'PDR RDC')
        mode(vm, reperage.MODE_JEU)
        vm.JeuChoisi = u'DCE'
        self.assertEqual(vm.Items[0].Phrase, u'les coupes du jeu DCE')
        vm.JeuChoisi = reperage.JEU_DU_PLAN
        self.assertEqual(vm.Items[0].Phrase, u'les coupes du jeu PC')

    def test_mode_inapplicable_le_dit_au_lieu_de_masquer_tout(self):
        vm = page()
        cocher(vm, u'PDR Détail')
        mode(vm, reperage.MODE_FEUILLE)
        self.assertIn(u'aucune feuille', vm.Items[3].Phrase)

    def test_selection_puis_deselection_recharge_l_editeur(self):
        vm = page()
        cocher(vm, u'PDR RDC')
        mode(vm, reperage.MODE_JEU)
        cocher(vm, u'PDR R+1')
        self.assertEqual(vm.ModeChoisi.Cle, reperage.MODE_AUCUN)
        cocher(vm, u'PDR RDC')
        self.assertEqual(vm.ModeChoisi.Cle, reperage.MODE_JEU)


class TestExceptions(unittest.TestCase):
    def test_montrer_et_masquer_sont_exclusifs(self):
        vm = page()
        item = vm.CoupesItems[0]
        item.Forcee = True
        item.Exclue = True
        self.assertFalse(item.Forcee)
        self.assertTrue(item.Exclue)

    def test_un_retrait_arrive_dans_la_phrase(self):
        vm = page()
        cocher(vm, u'PDR RDC')
        mode(vm, reperage.MODE_JEU)
        vm.CoupesItems[0].Exclue = True
        self.assertEqual(vm.Items[0].Phrase,
                         u'les coupes du jeu PC, sauf Coupe AA')

    def test_un_ajout_arrive_dans_la_phrase(self):
        vm = page()
        cocher(vm, u'PDR RDC')
        mode(vm, reperage.MODE_FEUILLE)
        vm.CoupesItems[2].Forcee = True
        self.assertEqual(vm.Items[0].Phrase,
                         u'les coupes de la feuille A01, plus Coupe ZZ')

    def test_coupes_choisies_compte_les_cochees(self):
        vm = page()
        cocher(vm, u'PDR RDC')
        mode(vm, reperage.MODE_CHOIX)
        vm.CoupesItems[0].Forcee = True
        vm.CoupesItems[1].Forcee = True
        self.assertEqual(vm.Items[0].Phrase, u'2 coupes choisies')
        self.assertEqual(vm.TitreCoupes, u'Coupes à montrer')
        self.assertEqual(vm.VisibiliteMasquer, u'Hidden')

    def test_recherche_de_coupes(self):
        vm = page()
        vm.FiltreCoupes = u'zz'
        self.assertEqual([c.Nom for c in vm.CoupesFiltrees], [u'Coupe ZZ'])
        vm.FiltreCoupes = u''
        self.assertEqual(len(vm.CoupesFiltrees), 3)


class TestDivergence(unittest.TestCase):
    def test_deux_regles_differentes_sont_signalees(self):
        service = ServiceFactice(regles={
            u'u1': reperage.Regle(reperage.MODE_FEUILLE),
            u'u2': reperage.Regle(reperage.MODE_JEU)})
        vm = page(service)
        cocher(vm, u'PDR RDC', u'PDR R+1')
        self.assertTrue(vm.Divergent)
        self.assertIn(u'pas la même règle', vm.Avertissement)

    def test_deux_regles_identiques_ne_divergent_pas(self):
        service = ServiceFactice(regles={
            u'u1': reperage.Regle(reperage.MODE_JEU),
            u'u2': reperage.Regle(reperage.MODE_JEU)})
        vm = page(service)
        cocher(vm, u'PDR RDC', u'PDR R+1')
        self.assertFalse(vm.Divergent)

    def test_toucher_un_reglage_aligne_toute_la_selection(self):
        service = ServiceFactice(regles={
            u'u1': reperage.Regle(reperage.MODE_FEUILLE),
            u'u2': reperage.Regle(reperage.MODE_JEU)})
        vm = page(service)
        cocher(vm, u'PDR RDC', u'PDR R+1')
        mode(vm, reperage.MODE_CHOIX)
        self.assertFalse(vm.Divergent)


class TestModeIndisponible(unittest.TestCase):
    def test_un_parametre_absent_grise_son_mode_sans_le_cacher(self):
        """Un mode absent sans explication passerait pour un bug."""
        service = ServiceFactice(parametres={reperage.FEUILLE: 1,
                                             reperage.NOM: 3})
        vm = page(service)
        par_cle = dict((m.Cle, m) for m in vm.Modes)
        self.assertTrue(par_cle[reperage.MODE_FEUILLE].Disponible)
        self.assertFalse(par_cle[reperage.MODE_JEU].Disponible)
        self.assertIn(u'Jeu de feuilles', par_cle[reperage.MODE_JEU].Raison)


class TestDerive(unittest.TestCase):
    def test_filtre_attendu_absent(self):
        """Feuille renumérotée, plan déplacé, filtre supprimé à la main : le
        nom attendu n'est plus posé sur la vue."""
        service = ServiceFactice(
            regles={u'u1': reperage.Regle(reperage.MODE_FEUILLE)},
            poses={u'u1': [u'418_PDR_Feuille_A99']})
        vm = page(service)
        self.assertTrue(vm.Items[0].ADerive)
        self.assertIn(u'périmé', vm.Items[0].Derive)
        self.assertTrue(vm.ADerive)

    def test_coupe_renommee(self):
        service = ServiceFactice(
            regles={u'u1': reperage.Regle(reperage.MODE_FEUILLE,
                                          retraits=[u'Coupe disparue'])},
            poses={u'u1': [u'418_PDR_Plan_PDR RDC']})
        vm = page(service)
        self.assertIn(u'coupe introuvable', vm.Items[0].Derive)

    def test_pas_de_derive_quand_tout_concorde(self):
        service = ServiceFactice(
            regles={u'u1': reperage.Regle(reperage.MODE_FEUILLE)},
            poses={u'u1': [u'418_PDR_Feuille_A01']})
        vm = page(service)
        self.assertFalse(vm.Items[0].ADerive)
        self.assertFalse(vm.ADerive)

    def test_un_plan_non_gere_ne_derive_pas(self):
        vm = page(ServiceFactice(poses={u'u3': [u'418_PDR_Feuille_A10']}))
        self.assertFalse(vm.Items[2].ADerive)


class TestPresets(unittest.TestCase):
    def test_les_types_et_les_jeux_sont_offerts(self):
        """Le type de vue n'est plus un réglage mémorisé : c'est un raccourci
        de sélection parmi d'autres."""
        vm = page()
        libelles = vm.Liste.Presets
        self.assertIn(u'du type Plan de repérage', libelles)
        self.assertIn(u'du jeu PC', libelles)
        self.assertIn(u'non gérés', libelles)

    def test_un_preset_coche_ce_qu_il_designe(self):
        vm = page()
        vm.Liste.Preset = u'du type Plan de repérage'
        coches = sorted(it.Nom for it in vm.Items if it.IsSelected)
        self.assertEqual(coches, [u'PDR Détail', u'PDR R+1', u'PDR RDC'])


class TestApplication(unittest.TestCase):
    def test_tous_les_plans_sont_envoyes_gere_ou_pas(self):
        """Les plans non gérés partent aussi : c'est ce qui retire les filtres
        d'un plan qu'on vient de dé-gérer."""
        service = ServiceFactice()
        vm = page(service)
        cocher(vm, u'PDR RDC')
        mode(vm, reperage.MODE_FEUILLE)
        vm.appliquer()
        self.assertEqual(len(service.recu), 4)
        par_nom = dict((c['plan']['nom'], c['regle']) for c in service.recu)
        self.assertEqual(par_nom[u'PDR RDC'].mode, reperage.MODE_FEUILLE)
        self.assertEqual(par_nom[u'Plan masse'].mode, reperage.MODE_AUCUN)

    def test_les_messages_arrivent_dans_la_page(self):
        vm = page()
        vm.appliquer()
        self.assertTrue(vm.AMessages)
        self.assertEqual(vm.Messages, [u'ok'])

    def test_retirer_tout_appelle_le_service(self):
        service = ServiceFactice()
        vm = page(service)
        vm.retirer_tout()
        self.assertEqual(service.retraits, 1)

    def test_plan_a_activer(self):
        vm = page()
        self.assertIsNone(vm.plan_selectionne())
        cocher(vm, u'PDR R+1')
        self.assertEqual(vm.plan_selectionne(), u'u2')


class TestSansService(unittest.TestCase):
    """Le VM doit tenir debout sans Revit ni service — c'est ce qui rend ces
    tests possibles, et ça garde l'outil ouvrable en cas de panne."""

    def test_construction_et_application(self):
        vm = ReperagePageVM(PLANS, COUPES, service=None)
        self.assertEqual(len(vm.Items), 4)
        vm.appliquer()
        self.assertIn(u'indisponible', vm.Messages[0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
