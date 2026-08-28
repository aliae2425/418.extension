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
from lib.viewmodels.MaterialCardVM import Couche, MaterialCardVM, Motif
from ui.helpers import donut_image


class FakeUsages(object):
    """Tient lieu de `MaterialService.LigneRapport`."""

    def __init__(self, types=0, instances=0):
        self.Types = types
        self.Instances = instances

    @property
    def Total(self):
        return self.Types + self.Instances

    @property
    def Detail(self):
        return u'%d types · %d instances' % (self.Types, self.Instances)


def _carte(item_id, nom, apparence=u'', classe=u'Béton', usages=None,
           coupe=None, surface=None):
    return MaterialCardVM(item_id, nom, classe=classe, apparence=apparence,
                          usages=usages,
                          motif_coupe=_motif(coupe),
                          motif_surface=_motif(surface))


def _motif(nom):
    """`Motif` d'un seul motif de premier plan, ou vide (nom « Aucun »)."""
    if not nom:
        return Motif()
    return Motif(premier=Couche(nom=nom))


def _indicateur(vm, libelle):
    for indic in vm.Indicateurs:
        if indic.Libelle == libelle:
            return indic
    raise AssertionError(u'indicateur « %s » absent' % libelle)


class TestCleNom(unittest.TestCase):

    def test_casse_accents_ponctuation_et_marqueur_de_copie(self):
        for nom in (u'Béton banché', u'beton_banche', u'BETON BANCHE',
                    u'Béton banché (1)', u'Béton banché - copie',
                    u'Béton banché copy'):
            self.assertEqual(_cle_nom(nom), u'betonbanche', nom)

    def test_deux_betons_differents_ne_se_confondent_pas(self):
        self.assertNotEqual(_cle_nom(u'Béton C25'), _cle_nom(u'Béton C30'))


class TestAuditPageVM(unittest.TestCase):

    def test_compte_utilises_et_non_utilises(self):
        vm = AuditPageVM([
            _carte(1, u'Utilisé', usages=FakeUsages(types=1, instances=3)),
            _carte(2, u'Jamais posé', usages=FakeUsages(types=2)),
            _carte(3, u'Orphelin', usages=FakeUsages()),
        ])
        self.assertEqual(_indicateur(vm, u'Matériaux').Valeur, u'3')
        self.assertEqual(_indicateur(vm, u'Utilisés').Valeur, u'2')
        self.assertEqual(_indicateur(vm, u'Non utilisés').Valeur, u'1')
        # « Sans instance » ne compte QUE les utilisés sans instance : un
        # matériau non utilisé n'a pas d'instance par définition, le compter
        # ferait un doublon du compteur précédent.
        self.assertEqual(_indicateur(vm, u'Sans instance').Valeur, u'1')
        self.assertTrue(_indicateur(vm, u'Non utilisés').Alerte)
        self.assertFalse(_indicateur(vm, u'Matériaux').Alerte)

    def test_apparences_partagees_regroupees(self):
        vm = AuditPageVM([
            _carte(1, u'Béton A', apparence=u'Concrete Cast'),
            _carte(2, u'Béton B', apparence=u'Concrete Cast'),
            _carte(3, u'Chêne', apparence=u'Oak'),
            _carte(4, u'Sans rendu', apparence=u''),
        ])
        self.assertEqual(len(vm.ApparencesPartagees), 1)
        groupe = vm.ApparencesPartagees[0]
        self.assertEqual(groupe.Titre, u'Concrete Cast')
        self.assertEqual(groupe.Nombre, 2)
        self.assertEqual(_indicateur(vm, u'Apparences dupliquées').Valeur, u'2')
        # « Aucune » n'est pas une apparence : ne doit pas faire un groupe.
        self.assertEqual(_indicateur(vm, u'Sans apparence').Valeur, u'1')

    def test_noms_proches_regroupes(self):
        vm = AuditPageVM([
            _carte(1, u'Béton banché'),
            _carte(2, u'beton_banche'),
            _carte(3, u'Chêne'),
        ])
        self.assertEqual(len(vm.NomsProches), 1)
        self.assertEqual(vm.NomsProches[0].Nombre, 2)
        self.assertFalse(vm.ARienASignaler)

    def test_modele_propre_na_rien_a_signaler(self):
        vm = AuditPageVM([
            _carte(1, u'Béton', apparence=u'Concrete',
                   usages=FakeUsages(types=1, instances=1)),
            _carte(2, u'Chêne', apparence=u'Oak',
                   usages=FakeUsages(types=1, instances=1)),
        ])
        self.assertTrue(vm.ARienASignaler)
        self.assertEqual(_indicateur(vm, u'Utilisés').Detail, u'100 %')

    def test_modele_vide_ne_leve_pas(self):
        vm = AuditPageVM([])
        self.assertEqual(_indicateur(vm, u'Matériaux').Valeur, u'0')
        self.assertEqual(_indicateur(vm, u'Utilisés').Detail, u'')
        self.assertTrue(vm.ARienASignaler)


class TestHachures(unittest.TestCase):

    def test_motifs_identiques_regroupes_par_face(self):
        vm = AuditPageVM([
            _carte(1, u'Béton A', coupe=u'Béton', surface=u'Uni'),
            _carte(2, u'Béton B', coupe=u'Béton', surface=u'Briques'),
            _carte(3, u'Enduit', coupe=u'Plâtre', surface=u'Uni'),
        ])
        self.assertEqual([(g.Titre, g.Nombre) for g in vm.MotifsCoupe],
                         [(u'Béton', 2)])
        self.assertEqual([(g.Titre, g.Nombre) for g in vm.MotifsSurface],
                         [(u'Uni', 2)])
        # 1, 2 (coupe) et 3 (surface) : trois matériaux indiscernables sur au
        # moins une face.
        self.assertEqual(_indicateur(vm, u'Motifs identiques').Valeur, u'3')

    def test_absence_de_motif_nest_pas_un_motif_partage(self):
        vm = AuditPageVM([_carte(1, u'Béton'), _carte(2, u'Chêne')])
        self.assertEqual(vm.MotifsCoupe, [])
        self.assertEqual(vm.MotifsSurface, [])
        self.assertEqual(_indicateur(vm, u'Sans motif de coupe').Valeur, u'2')
        self.assertEqual(_indicateur(vm, u'Sans motif de surface').Valeur, u'2')
        self.assertEqual(_indicateur(vm, u'Sans aucun motif').Valeur, u'2')

    def test_motif_partage_ne_compte_pas_comme_doublon_au_score(self):
        # Partager « Uni » est la norme, pas un défaut : les hachures restent
        # hors de la partition de l'anneau et hors du barème.
        vm = AuditPageVM([
            _carte(1, u'Béton', apparence=u'Concrete', coupe=u'Uni',
                   surface=u'Uni', usages=FakeUsages(types=1, instances=1)),
            _carte(2, u'Chêne', apparence=u'Oak', coupe=u'Uni',
                   surface=u'Uni', usages=FakeUsages(types=1, instances=1)),
        ])
        self.assertEqual(vm.Score, 100)
        self.assertEqual(dict((s.Libelle, s.Nombre) for s in vm.Segments)
                         [u'En doublon'], 0)


class TestSections(unittest.TestCase):

    def test_seules_les_sections_non_vides_existent(self):
        vm = AuditPageVM([
            _carte(1, u'Béton A', apparence=u'Concrete'),
            _carte(2, u'Béton B', apparence=u'Concrete'),
        ])
        self.assertEqual([s.Titre for s in vm.Sections],
                         [u'Apparences partagées'])
        self.assertFalse(vm.ARienASignaler)

    def test_la_premiere_section_est_deployee(self):
        vm = AuditPageVM([
            _carte(1, u'Béton A', apparence=u'Concrete', coupe=u'Béton'),
            _carte(2, u'Béton B', apparence=u'Concrete', coupe=u'Béton'),
        ])
        self.assertEqual([s.EstDeployee for s in vm.Sections], [True, False])
        self.assertEqual(vm.Sections[0].Compteur, u'1 groupe · 2 matériaux')

    def test_le_pliage_est_pilotable_depuis_lexpander(self):
        vm = AuditPageVM([
            _carte(1, u'Béton A', apparence=u'Concrete'),
            _carte(2, u'Béton B', apparence=u'Concrete'),
        ])
        section = vm.Sections[0]
        section.EstDeployee = False
        self.assertFalse(section.EstDeployee)

    def test_aucune_section_sur_un_modele_propre(self):
        vm = AuditPageVM([
            _carte(1, u'Béton', apparence=u'Concrete', coupe=u'Béton'),
            _carte(2, u'Chêne', apparence=u'Oak', coupe=u'Bois'),
        ])
        self.assertEqual(vm.Sections, [])
        self.assertTrue(vm.ARienASignaler)


class TestArcs(unittest.TestCase):
    """Géométrie de l'anneau : pure, testable hors Revit (les imports WPF de
    donut_image sont gardés)."""

    def test_partition_en_trois(self):
        self.assertEqual(donut_image.arcs([0.5, 0.25, 0.25]),
                         [(-90.0, 180.0), (90.0, 90.0), (180.0, 90.0)])

    def test_part_nulle_ne_produit_pas_darc(self):
        # Un balayage de 0° ne dessine rien mais laisserait une capsule de
        # plume visible sur l'anneau.
        self.assertEqual(donut_image.arcs([1.0, 0.0]), [(-90.0, 360.0)])

    def test_demarre_a_midi(self):
        self.assertEqual(donut_image.arcs([1.0])[0][0], -90.0)


class TestScoreEtAnneau(unittest.TestCase):

    def test_modele_propre_note_100(self):
        vm = AuditPageVM([
            _carte(1, u'Béton', apparence=u'Concrete',
                   usages=FakeUsages(types=1, instances=1)),
            _carte(2, u'Chêne', apparence=u'Oak',
                   usages=FakeUsages(types=1, instances=1)),
        ])
        self.assertEqual(vm.Score, 100)
        self.assertEqual(vm.ScoreMention, u'Bon état')
        self.assertEqual(vm.ScoreDetail, u'aucune pénalité')

    def test_moitie_non_utilisee_perd_la_moitie_du_poste(self):
        # Poste « non utilisés » : 50 points au maximum, donc −25 à moitié.
        vm = AuditPageVM([
            _carte(1, u'Béton', apparence=u'Concrete',
                   usages=FakeUsages(types=1, instances=1)),
            _carte(2, u'Chêne', apparence=u'Oak', usages=FakeUsages()),
        ])
        self.assertEqual(vm.Score, 75)
        self.assertEqual(vm.ScoreMention, u'À nettoyer')

    def test_les_parts_de_lanneau_font_une_partition(self):
        # Le matériau 3 est non utilisé ET en doublon d'apparence : il ne
        # compte QUE comme non utilisé, sinon l'anneau dépasse 100 %.
        vm = AuditPageVM([
            _carte(1, u'Béton A', apparence=u'Concrete',
                   usages=FakeUsages(types=1, instances=2)),
            _carte(2, u'Béton B', apparence=u'Concrete',
                   usages=FakeUsages(types=1, instances=2)),
            _carte(3, u'Béton C', apparence=u'Concrete', usages=FakeUsages()),
        ])
        parts = dict((s.Libelle, s.Nombre) for s in vm.Segments)
        self.assertEqual(parts, {u'Sains': 0, u'En doublon': 2,
                                 u'Non utilisés': 1})
        self.assertEqual(sum(parts.values()), len(vm.Cartes))
        self.assertAlmostEqual(sum(s.Portion for s in vm.Segments), 1.0)

    def test_legende_et_anneau_partagent_la_teinte(self):
        vm = AuditPageVM([_carte(1, u'Béton', apparence=u'Concrete',
                                 usages=FakeUsages(types=1, instances=1))])
        segment = vm.Segments[0]
        self.assertEqual(segment.Couleur, donut_image.hexa(segment.Rgb))
        self.assertEqual(segment.Rgb, donut_image.couleur('sains'))

    def test_modele_vide_note_zero_sans_lever(self):
        vm = AuditPageVM([])
        self.assertEqual(vm.Score, 0)
        self.assertEqual(vm.ScoreMention, u'—')
        self.assertEqual([s.Part for s in vm.Segments], [u'—', u'—', u'—'])


if __name__ == '__main__':
    unittest.main()
