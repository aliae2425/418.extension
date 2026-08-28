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

from lib.viewmodels.AuditPageVM import AuditPageVM, _cle_nom


def filtre(nom, categories=(), vues=(), gabarits=(), effets=None,
           genre='parametrique'):
    """Un dictionnaire de filtre tel que le renvoie FiltresService.

    `effets` par défaut = nombre d'applications, c'est-à-dire « toutes ont un
    effet » : le cas sain. Passer 0 pour un filtre inerte.
    """
    vues, gabarits = list(vues), list(gabarits)
    return {'nom': nom, 'genre': genre, 'categories': list(categories),
            'vues': vues, 'gabarits': gabarits,
            'effets': len(vues) + len(gabarits) if effets is None else effets}


class TestCleNom(unittest.TestCase):
    def test_casse_accents_ponctuation_et_copie(self):
        self.assertEqual(_cle_nom(u'Murs béton'), _cle_nom(u'murs_beton'))
        self.assertEqual(_cle_nom(u'Murs béton (1)'), _cle_nom(u'Murs béton'))
        self.assertEqual(_cle_nom(u'Murs - copie'), _cle_nom(u'Murs'))

    def test_noms_distincts_restent_distincts(self):
        self.assertNotEqual(_cle_nom(u'Murs'), _cle_nom(u'Sols'))


class TestClassement(unittest.TestCase):
    def test_non_utilise_quand_aucune_vue_ni_gabarit(self):
        vm = AuditPageVM([filtre(u'Mort'),
                          filtre(u'Vivant', gabarits=[u'Gabarit A'])])
        self.assertEqual([f['nom'] for f in vm.NonUtilises], [u'Mort'])

    def test_sans_effet_quand_applique_mais_aucun_effet(self):
        vm = AuditPageVM([filtre(u'Inerte', vues=[u'Vue 1'], effets=0),
                          filtre(u'Actif', vues=[u'Vue 1'])])
        self.assertEqual([f['nom'] for f in vm.SansEffet], [u'Inerte'])

    def test_un_filtre_non_applique_n_est_pas_sans_effet(self):
        # Sinon il serait compté deux fois : les deux postes sont exclusifs.
        vm = AuditPageVM([filtre(u'Mort', effets=0)])
        self.assertEqual([f['nom'] for f in vm.SansEffet], [])
        self.assertEqual([f['nom'] for f in vm.NonUtilises], [u'Mort'])

    def test_hors_gabarit_seulement_si_aucun_gabarit(self):
        vm = AuditPageVM([
            filtre(u'Vue seule', vues=[u'Vue 1']),
            filtre(u'Les deux', vues=[u'Vue 1'], gabarits=[u'Gabarit A']),
            filtre(u'Gabarit seul', gabarits=[u'Gabarit A'])])
        self.assertEqual([f['nom'] for f in vm.HorsGabarit], [u'Vue seule'])


class TestGroupes(unittest.TestCase):
    def test_noms_proches(self):
        vm = AuditPageVM([filtre(u'Murs béton'), filtre(u'murs_beton'),
                          filtre(u'Sols')])
        self.assertEqual(len(vm.NomsProches), 1)
        titre, membres = vm.NomsProches[0]
        self.assertEqual(titre, u'Murs béton')
        self.assertEqual(len(membres), 2)

    def test_memes_categories(self):
        vm = AuditPageVM([filtre(u'A', categories=[u'Murs', u'Sols']),
                          filtre(u'B', categories=[u'Murs', u'Sols']),
                          filtre(u'C', categories=[u'Murs'])])
        self.assertEqual(len(vm.MemesCategories), 1)
        _, membres = vm.MemesCategories[0]
        self.assertEqual(sorted(f['nom'] for f in membres), [u'A', u'B'])

    def test_sans_categorie_ne_fait_pas_groupe(self):
        # Clé vide : deux filtres sans catégorie ne sont pas « mêmes cibles ».
        vm = AuditPageVM([filtre(u'A'), filtre(u'B')])
        self.assertEqual(vm.MemesCategories, [])


class TestIndicateurs(unittest.TestCase):
    def test_douze_tuiles_dont_la_premiere_compte_tout(self):
        vm = AuditPageVM([filtre(u'A', vues=[u'Vue 1']), filtre(u'B')])
        self.assertEqual(len(vm.Indicateurs), 12)
        self.assertEqual(vm.Indicateurs[0].Valeur, u'2')
        self.assertEqual(vm.Indicateurs[1].Valeur, u'1')      # utilisés
        self.assertEqual(vm.Indicateurs[2].Valeur, u'1')      # non utilisés
        self.assertTrue(vm.Indicateurs[2].Alerte)

    def test_vues_et_gabarits_distincts(self):
        vm = AuditPageVM([filtre(u'A', vues=[u'Vue 1', u'Vue 2']),
                          filtre(u'B', vues=[u'Vue 1'],
                                 gabarits=[u'Gabarit A'])])
        libelles = dict((i.Libelle, i.Valeur) for i in vm.Indicateurs)
        self.assertEqual(libelles[u'Vues filtrées'], u'2')
        self.assertEqual(libelles[u'Gabarits filtrés'], u'1')
        self.assertEqual(libelles[u'Applications'], u'4')

    def test_modele_sans_filtre(self):
        vm = AuditPageVM([])
        self.assertEqual(vm.Resume, u'Aucun filtre dans le modèle.')
        self.assertEqual(vm.Score, 0)
        self.assertEqual(vm.ScoreNiveau, u'vide')
        self.assertTrue(vm.ARienASignaler)


class TestAnneauEtScore(unittest.TestCase):
    def test_les_parts_forment_une_partition(self):
        vm = AuditPageVM([
            filtre(u'Mort'),
            filtre(u'Inerte', vues=[u'Vue 1'], effets=0),
            filtre(u'Murs béton', gabarits=[u'Gabarit A']),
            filtre(u'murs_beton', gabarits=[u'Gabarit A']),
            filtre(u'Sain', gabarits=[u'Gabarit A'])])
        self.assertEqual(sum(s.Nombre for s in vm.Segments), 5)
        parts = dict((s.Libelle, s.Nombre) for s in vm.Segments)
        self.assertEqual(parts[u'Non utilisés'], 1)
        self.assertEqual(parts[u'Sans effet'], 1)
        self.assertEqual(parts[u'En doublon'], 2)
        self.assertEqual(parts[u'Sains'], 1)

    def test_un_defaut_grave_prime_sur_le_doublon(self):
        # « Mort » est aussi un doublon de nom, mais il ne compte QUE comme
        # non utilisé — sinon les parts de l'anneau ne bouclent plus.
        vm = AuditPageVM([filtre(u'Mort'), filtre(u'mort')])
        parts = dict((s.Libelle, s.Nombre) for s in vm.Segments)
        self.assertEqual(parts[u'Non utilisés'], 2)
        self.assertEqual(parts[u'En doublon'], 0)

    def test_modele_propre_note_100(self):
        vm = AuditPageVM([filtre(u'Murs', gabarits=[u'Gabarit A']),
                          filtre(u'Sols', gabarits=[u'Gabarit A'])])
        self.assertEqual(vm.Score, 100)
        self.assertEqual(vm.ScoreNiveau, u'bon')
        self.assertEqual(vm.ScoreDetail, u'aucune pénalité')

    def test_tout_non_utilise_perd_le_poste_entier(self):
        vm = AuditPageVM([filtre(u'A'), filtre(u'B')])
        self.assertEqual(vm.Score, 50)          # 100 − 50 (poste complet)
        self.assertEqual(vm.ScoreNiveau, u'critique')


class TestSections(unittest.TestCase):
    def test_les_sections_vides_ne_sont_pas_construites(self):
        vm = AuditPageVM([filtre(u'Sain', gabarits=[u'Gabarit A'])])
        self.assertEqual(vm.Sections, [])
        self.assertTrue(vm.ARienASignaler)

    def test_premiere_section_deployee_les_autres_non(self):
        vm = AuditPageVM([filtre(u'Mort'),
                          filtre(u'Inerte', vues=[u'Vue 1'], effets=0)])
        self.assertEqual([s.Titre for s in vm.Sections],
                         [u'Non utilisés', u'Sans effet', u'Hors gabarit'])
        self.assertTrue(vm.Sections[0].EstDeployee)
        self.assertFalse(vm.Sections[1].EstDeployee)

    def test_ligne_de_filtre_porte_ses_categories(self):
        vm = AuditPageVM([filtre(u'Mort', categories=[u'Murs', u'Sols'])])
        ligne = vm.Sections[0].Lignes[0]
        self.assertEqual(ligne.Titre, u'Mort')
        self.assertEqual(ligne.Detail, u'Murs · Sols')

    def test_compteur_accorde_le_pluriel(self):
        vm = AuditPageVM([filtre(u'A'), filtre(u'B'),
                          filtre(u'C', gabarits=[u'Gabarit A'])])
        self.assertEqual(vm.Sections[0].Compteur, u'2 filtres')
        vm = AuditPageVM([filtre(u'A'), filtre(u'B', gabarits=[u'Gabarit A'])])
        self.assertEqual(vm.Sections[0].Compteur, u'1 filtre')


if __name__ == '__main__':
    unittest.main()
