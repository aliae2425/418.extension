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

from lib.services import hatch
from lib.viewmodels import EditeurVM as module
from lib.viewmodels.EditeurVM import (EditeurVM, EmplacementVM, rgb_de_hex,
                                      hex_de_rgb)
from lib.viewmodels.MaterialCardVM import Couche
from lib.viewmodels.lecture_materiau import ApparenceRef, MotifRef


class _FauxHatchImage(object):
    """Note ce que l'aperçu demande, sans toucher à WPF."""

    def __init__(self):
        self.appels = []

    def vignette(self, couches, largeur=None, hauteur=None, echelle_vue=None):
        self.appels.append((list(couches), largeur, hauteur, echelle_vue))
        return 'image-1-%s' % echelle_vue


class _FauxMateriau(object):
    def __init__(self, nom=u'Béton'):
        self.Name = nom


class _FausseCarte(object):
    def __init__(self, nom=u'Béton'):
        self.Nom = nom
        self.rafraichie = False

    def rafraichir(self, nom, classe, apparence, couleur, coupe, surface):
        self.Nom = nom
        self.rafraichie = True


class _FauxService(object):
    """Accepte tout, sauf les attributs listés dans `refuse`."""

    def __init__(self, refuse=()):
        self.refuse = set(refuse)
        self.recu = None

    def enregistrer(self, materiau, valeurs):
        self.recu = dict(valeurs)
        if 'Name' in valeurs and 'Name' not in self.refuse:
            materiau.Name = valeurs['Name']
        return [cle for cle in valeurs if cle in self.refuse]


def _motif(nom, est_modele=False, identifiant=None):
    return MotifRef(identifiant or nom,
                    Couche(nom=nom, grilles=[hatch.Grille(offset=1.0)],
                           est_modele=est_modele))


def _vm(service=None, materiau=None, carte=None):
    """Un éditeur chargé sur un matériau simple : brique en coupe, rien en
    surface."""
    brique = _motif(u'Brique')
    beton = _motif(u'Béton', est_modele=True)
    aucun = MotifRef(u'aucun')
    motifs = [aucun, brique, beton]
    choisis = {
        (u'Cut', u'Background'): (aucun, (255, 255, 255)),
        (u'Cut', u'Foreground'): (brique, (0, 0, 0)),
        (u'Surface', u'Background'): (aucun, (255, 255, 255)),
        (u'Surface', u'Foreground'): (aucun, (0, 0, 0)),
    }
    return EditeurVM(
        nom=u'Béton', classe=u'Béton', couleur=(176, 65, 62),
        transparence=0, brillance=64, lissage=50,
        apparence=ApparenceRef(u'asset-1', u'Béton coulé'),
        choisis=choisis, motifs=motifs,
        apparences=[ApparenceRef(u'aucune', u'Aucune'),
                    ApparenceRef(u'asset-1', u'Béton coulé')],
        service=service, materiau=materiau, carte=carte), motifs


class _Base(unittest.TestCase):
    def setUp(self):
        self.faux = _FauxHatchImage()
        self._vrai = module.hatch_image
        module.hatch_image = self.faux

    def tearDown(self):
        module.hatch_image = self._vrai


class TestCouleurHex(unittest.TestCase):
    def test_aller_retour(self):
        self.assertEqual(rgb_de_hex(hex_de_rgb((176, 65, 62))), (176, 65, 62))

    def test_saisie_incomplete_garde_le_defaut(self):
        # Le TextBox est lié en PropertyChanged : « #B04 » existe le temps
        # d'une frappe et ne doit ni lever ni noircir l'aperçu.
        self.assertEqual(rgb_de_hex(u'#B04', defaut=(1, 2, 3)), (1, 2, 3))
        self.assertEqual(rgb_de_hex(u'#ZZZZZZ', defaut=(1, 2, 3)), (1, 2, 3))

    def test_le_diese_est_facultatif(self):
        self.assertEqual(rgb_de_hex(u'FFFFFF'), (255, 255, 255))


class TestValeursModifiees(_Base):
    def test_rien_ne_bouge_au_chargement(self):
        vm, _ = _vm()
        self.assertEqual(vm.valeurs_modifiees(), {})

    def test_seul_le_champ_touche_ressort(self):
        vm, _ = _vm()
        vm.Nom = u'Béton banché'
        self.assertEqual(vm.valeurs_modifiees(), {'Name': u'Béton banché'})

    def test_un_motif_ressort_sous_son_nom_dattribut_revit(self):
        vm, motifs = _vm()
        vm.Faces[0].Premier.Motif = motifs[2]          # coupe, premier plan
        self.assertEqual(vm.valeurs_modifiees(),
                         {'CutForegroundPatternId': motifs[2].Id})

    def test_une_couleur_demplacement_ressort_en_triplet(self):
        vm, _ = _vm()
        vm.Faces[1].Fond.Couleur = u'#102030'          # surface, arrière-plan
        self.assertEqual(vm.valeurs_modifiees(),
                         {'SurfaceBackgroundPatternColor': (16, 32, 48)})

    def test_le_slider_envoie_un_double_le_vm_garde_un_entier(self):
        vm, _ = _vm()
        vm.Transparence = 42.0
        self.assertEqual(vm.valeurs_modifiees(), {'Transparency': 42})


class TestEnregistrer(_Base):
    def test_succes_reancre_letat(self):
        service = _FauxService()
        materiau, carte = _FauxMateriau(), _FausseCarte()
        vm, _ = _vm(service, materiau, carte)
        vm.Classe = u'Maçonnerie'

        self.assertTrue(vm.enregistrer())
        self.assertEqual(service.recu, {'MaterialClass': u'Maçonnerie'})
        self.assertTrue(carte.rafraichie)
        # Un second clic n'a plus rien à écrire.
        self.assertEqual(vm.valeurs_modifiees(), {})

    def test_un_refus_reste_en_attente_et_ne_bloque_pas_le_reste(self):
        service = _FauxService(refuse=['CutForegroundPatternId'])
        vm, motifs = _vm(service, _FauxMateriau(), _FausseCarte())
        vm.Classe = u'Maçonnerie'
        vm.Faces[0].Premier.Motif = motifs[2]

        self.assertFalse(vm.enregistrer())
        self.assertIn(u'CutForegroundPatternId', vm.Statut)
        # La classe est passée, le motif reste à réessayer.
        self.assertEqual(vm.valeurs_modifiees(),
                         {'CutForegroundPatternId': motifs[2].Id})

    def test_le_nom_accepte_par_revit_revient_dans_le_champ(self):
        # Revit suffixe « * » sur collision : l'éditeur doit afficher ce qui
        # a été retenu, pas ce qui a été demandé.
        service = _FauxService()
        carte = _FausseCarte()
        vm, _ = _vm(service, _FauxMateriau(), carte)
        vm.Nom = u'Béton'
        carte.rafraichir = lambda *a: setattr(carte, 'Nom', u'Béton*')
        vm.Classe = u'X'
        vm.enregistrer()
        self.assertEqual(vm.Nom, u'Béton*')


class TestApercu(_Base):
    def test_une_tuile_par_echelle(self):
        vm, _ = _vm()
        libelles = [t.Libelle for t in vm.Faces[0].Apercu]
        self.assertEqual(libelles,
                         [u'1:%d' % e for e in hatch.ECHELLES_APERCU])

    def test_seule_lechelle_varie_dune_tuile_a_lautre(self):
        vm, _ = _vm()
        derniers = self.faux.appels[-len(hatch.ECHELLES_APERCU):]
        self.assertEqual([a[3] for a in derniers], list(hatch.ECHELLES_APERCU))
        self.assertEqual(len(set(a[1] for a in derniers)), 1)   # même largeur
        self.assertEqual(len(set(a[2] for a in derniers)), 1)   # même hauteur

    def test_changer_un_motif_reconstruit_laperçu_de_sa_face_seule(self):
        vm, motifs = _vm()
        self.faux.appels = []
        vm.Faces[0].Premier.Motif = motifs[2]
        self.assertEqual(len(self.faux.appels), len(hatch.ECHELLES_APERCU))

    def test_laperçu_empile_le_fond_puis_le_premier_plan(self):
        vm, _ = _vm()
        couches = self.faux.appels[0][0]
        self.assertEqual([c.nom if c else None for c in couches],
                         [None, u'Brique'])


class TestMotifRef(unittest.TestCase):
    """Ce sur quoi le menu déroulant s'appuie pour afficher chaque motif."""

    def test_le_type_distingue_modele_et_dessin(self):
        self.assertEqual(_motif(u'Brique').Type, u'dessin')
        self.assertEqual(_motif(u'Béton', est_modele=True).Type, u'modèle')

    def test_aucun_na_pas_de_type(self):
        self.assertEqual(MotifRef(u'aucun').Type, u'')

    def test_aucun_ne_donne_aucune_couche_a_dessiner(self):
        self.assertIsNone(MotifRef(u'aucun').pour((0, 0, 0)))


class TestArrierePlan(_Base):
    """Revit n'accepte un motif de MODÈLE qu'en premier plan."""

    def test_larriere_plan_nofffre_pas_les_motifs_de_modele(self):
        vm, motifs = _vm()
        offerts = vm.Faces[0].Fond.Motifs
        self.assertIn(motifs[1], offerts)          # Brique, dessin
        self.assertNotIn(motifs[2], offerts)       # Béton, modèle

    def test_le_premier_plan_offre_tout(self):
        vm, motifs = _vm()
        self.assertEqual(vm.Faces[0].Premier.Motifs, motifs)

    def test_un_modele_deja_en_place_reste_offert(self):
        # Matériau hérité d'un vieux gabarit : le retirer du menu ferait
        # disparaître le motif au premier changement de couleur.
        modele = _motif(u'Béton', est_modele=True)
        offerts = EmplacementVM._proposables(
            u'Background', [MotifRef(u'aucun'), modele], modele)
        self.assertIn(modele, offerts)


class TestEchelleModele(unittest.TestCase):
    """Le cœur de l'aperçu multi-échelle : un motif de MODÈLE se densifie
    quand la vue s'éloigne, un motif de DESSIN reste en taille papier."""

    def test_un_motif_modele_se_densifie_quand_lechelle_seloigne(self):
        grille = hatch.Grille(offset=1.0)          # un pied entre deux droites
        proche = hatch.par_grille([grille], 150, 96, hatch.echelle_modele(20))
        loin = hatch.par_grille([grille], 150, 96, hatch.echelle_modele(200))
        self.assertGreater(len(loin[0][0]), len(proche[0][0]))

    def test_un_motif_de_dessin_ignore_lechelle_de_vue(self):
        # `ECHELLE_DESSIN` est une constante, pas une fonction de l'échelle :
        # c'est ce qui fait sortir les quatre tuiles identiques, et c'est le
        # comportement de Revit.
        grille = hatch.Grille(offset=0.02)
        a = hatch.par_grille([grille], 150, 96, hatch.ECHELLE_DESSIN)
        b = hatch.par_grille([grille], 150, 96, hatch.ECHELLE_DESSIN)
        self.assertEqual(len(a[0][0]), len(b[0][0]))

    def test_lechelle_par_defaut_reste_celle_de_la_vignette_de_card(self):
        self.assertEqual(hatch.echelle_modele(),
                         hatch.ECHELLE_DESSIN / hatch.ECHELLE_VUE)


if __name__ == '__main__':
    unittest.main()
