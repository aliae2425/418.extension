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

from lib.services import presentation
from lib.services.ordres import Ordres


class FakeMateriau(object):
    def __init__(self, identifiant, nom, parametres=()):
        self.Id = identifiant          # un entier suffit : `ident` l'accepte
        self.Name = nom
        self.Parameters = list(parametres)


class FakeLigne(object):
    def __init__(self, categorie, types=0, instances=0):
        self.Categorie = categorie
        self.Types = types
        self.Instances = instances

    @property
    def Total(self):
        return self.Types + self.Instances

    @property
    def Detail(self):
        return u'%d type(s)' % self.Types


class FakeRapport(object):
    def __init__(self, lignes=(), peints=0):
        self.Lignes = list(lignes)
        self.Peints = peints

    @property
    def Total(self):
        return sum(ligne.Total for ligne in self.Lignes)

    @property
    def EstVide(self):
        return not self.Lignes


class FakeService(object):
    """Rejoue ce que fait `MaterialService` sans toucher à Revit."""

    def __init__(self, rapport=None):
        self.appels = []
        self._rapport = rapport or FakeRapport()

    def renommer(self, materiaux, regles):
        self.appels.append(('renommer', [m.Name for m in materiaux]))
        changes = 0
        for index, materiau in enumerate(materiaux, start=1):
            nouveau = regles.apply(materiau.Name, index=index)
            if nouveau != materiau.Name:
                materiau.Name = nouveau
                changes += 1
        return changes

    def enregistrer(self, materiau, valeurs, parametres=None):
        self.appels.append(('enregistrer', dict(valeurs or {}),
                            dict(parametres or {})))
        return []                      # rien de refusé

    def analyser(self, sources, categories=None):
        self.appels.append(('analyser', list(sources), categories))
        return self._rapport

    def remplacer(self, sources, cible, categories=None):
        self.appels.append(('remplacer', list(sources), cible, categories))
        return self._rapport


#: Un catalogue de motifs minimal : un « Aucun », un motif de dessin, un
#: motif de MODÈLE — c'est ce dernier qui fait toute la différence entre les
#: quatre emplacements.
MOTIFS = [
    {'id': -1, 'nom': u'Aucun', 'modele': False, 'type': u''},
    {'id': 1001, 'nom': u'Diagonale', 'modele': False, 'type': u'dessin'},
    {'id': 1002, 'nom': u'Briques', 'modele': True, 'type': u'modèle'},
]


class FakeCatalogue(object):
    """Ce que `Ordres` demande au catalogue : les catégories, les motifs, et
    la traduction entier -> identifiant Revit."""

    def __init__(self, categories=()):
        self.categories = [{'id': i, 'nom': nom}
                           for (i, nom) in categories]
        self.motifs = list(MOTIFS)
        self.apparences = [{'id': -1, 'nom': u'Aucune'}]

    def element_id(self, identifiant):
        return u'eid:%s' % identifiant

    def couche(self, identifiant, couleur_hex):
        return None                    # aucune hachure : la carte se rend quand même


class FakeDocument(object):
    def __init__(self, lecture_seule=False):
        self.IsReadOnly = lecture_seule


def _ordres(noms=(u'Béton coulé', u'Béton banché', u'BA13'),
            categories=((10, u'Murs'), (11, u'Sols')), rapport=None,
            doc=None):
    materiaux = dict((index + 1, FakeMateriau(index + 1, nom))
                     for index, nom in enumerate(noms))
    cartes = [{'id': identifiant, 'nom': materiau.Name,
               'usages': {'total': 0, 'instances': 0}}
              for identifiant, materiau in sorted(materiaux.items())]
    service = FakeService(rapport)
    return Ordres(doc=doc if doc is not None else FakeDocument(),
                  service=service, catalogue=FakeCatalogue(categories),
                  materiaux=materiaux, cartes=cartes), service


class TestApercuRenommage(unittest.TestCase):
    def test_seules_les_cartes_cochees_sortent(self):
        ordres, _ = _ordres()
        sortie = ordres.traiter({'ordre': 'apercu_renommage', 'ids': [1, 3],
                                 'prefixe': u'A_'})
        self.assertEqual(sorted(sortie['noms']), [u'1', u'3'])
        self.assertEqual(sortie['noms'][u'1'], u'A_Béton coulé')

    def test_le_jeton_n_ne_numerote_que_les_cochees(self):
        # {n} compte dans l'ordre de la LISTE, pas dans celui des ids reçus :
        # c'est l'ordre qui part ensuite au service, les deux doivent
        # coïncider.
        ordres, _ = _ordres()
        sortie = ordres.traiter({'ordre': 'apercu_renommage', 'ids': [3, 2],
                                 'suffixe': u'-{n}'})
        self.assertEqual(sortie['noms'][u'2'], u'Béton banché-1')
        self.assertEqual(sortie['noms'][u'3'], u'BA13-2')

    def test_une_regex_invalide_se_dit_sans_lever(self):
        ordres, _ = _ordres()
        sortie = ordres.traiter({'ordre': 'apercu_renommage', 'ids': [1],
                                 'rechercher': u'(('})
        self.assertTrue(sortie['erreur'])
        self.assertEqual(sortie['noms'][u'1'], u'Béton coulé')

    def test_le_champ_rechercher_est_une_regex(self):
        ordres, _ = _ordres()
        sortie = ordres.traiter({'ordre': 'apercu_renommage', 'ids': [3],
                                 'rechercher': u'\\d+', 'remplacer': u'X'})
        self.assertEqual(sortie['noms'][u'3'], u'BAX')


class TestRenommage(unittest.TestCase):
    def test_les_materiaux_partent_dans_l_ordre_de_la_liste(self):
        ordres, service = _ordres()
        ordres.traiter({'ordre': 'renommer', 'ids': [3, 1],
                        'suffixe': u'-{n}'})
        self.assertEqual(service.appels[0],
                         ('renommer', [u'Béton coulé', u'BA13']))

    def test_les_noms_rendus_sont_ceux_de_la_maquette(self):
        ordres, _ = _ordres()
        sortie = ordres.traiter({'ordre': 'renommer', 'ids': [1],
                                 'prefixe': u'A_'})
        self.assertEqual(sortie['changes'], 1)
        self.assertEqual(sortie['noms'][u'1'], u'A_Béton coulé')
        # La carte suit : un second aperçu doit partir du nouveau nom.
        suite = ordres.traiter({'ordre': 'apercu_renommage', 'ids': [1],
                                'prefixe': u'A_'})
        self.assertEqual(suite['noms'][u'1'], u'A_A_Béton coulé')

    def test_sans_coche_rien_ne_part_au_service(self):
        ordres, service = _ordres()
        self.assertEqual(ordres.traiter({'ordre': 'renommer', 'ids': []}),
                         {'changes': 0, 'noms': {}})
        self.assertEqual(service.appels, [])


class TestPortee(unittest.TestCase):
    def test_toutes_les_categories_cochees_valent_tout_le_modele(self):
        # None n'est pas « les mêmes catégories sans filtre » : sans filtre,
        # le balayage voit aussi ce qui n'a pas de catégorie de modèle. C'est
        # ce qu'on veut quand l'utilisateur n'a rien restreint.
        ordres, service = _ordres()
        ordres.traiter({'ordre': 'analyser', 'sources': [1],
                        'categories': [10, 11]})
        self.assertIsNone(service.appels[0][2])

    def test_une_portee_partielle_part_en_identifiants_revit(self):
        ordres, service = _ordres()
        ordres.traiter({'ordre': 'analyser', 'sources': [1],
                        'categories': [11]})
        self.assertEqual(service.appels[0][2], [u'eid:11'])


class TestRemplacement(unittest.TestCase):
    def test_le_rapport_part_en_json(self):
        rapport = FakeRapport([FakeLigne(u'Murs', types=2)], peints=3)
        ordres, _ = _ordres(rapport=rapport)
        sortie = ordres.traiter({'ordre': 'analyser', 'sources': [1],
                                 'categories': [10, 11]})
        self.assertEqual(sortie['lignes'],
                         [{'categorie': u'Murs', 'detail': u'2 type(s)',
                           'total': 2}])
        self.assertEqual(sortie['peints'], 3)
        self.assertFalse(sortie['applique'])

    def test_sans_cible_rien_n_est_remplace(self):
        ordres, service = _ordres()
        sortie = ordres.traiter({'ordre': 'remplacer', 'sources': [1],
                                 'cible': None, 'categories': [10, 11]})
        self.assertTrue(sortie['vide'])
        self.assertEqual(service.appels, [])

    def test_un_remplacement_applique_se_signale(self):
        rapport = FakeRapport([FakeLigne(u'Sols', instances=4)])
        ordres, _ = _ordres(rapport=rapport)
        sortie = ordres.traiter({'ordre': 'remplacer', 'sources': [1],
                                 'cible': 2, 'categories': [10, 11]})
        self.assertTrue(sortie['applique'])
        self.assertIn(u'4', sortie['etat'])

    def test_une_source_inconnue_ne_part_pas(self):
        ordres, service = _ordres()
        ordres.traiter({'ordre': 'analyser', 'sources': [1, 999],
                        'categories': [10, 11]})
        self.assertEqual(service.appels[0][1], [1])


class TestSelecteurDeMotif(unittest.TestCase):
    """La règle des motifs offerts vit ici, pas dans la page : c'est elle qui
    évite un « refusé par Revit » que plus rien n'explique à l'écriture."""

    def _motifs(self, face, couche, courant=-1):
        ordres, _ = _ordres()
        return ordres.traiter({'ordre': 'selecteur', 'face': face,
                               'couche': couche, 'motif': courant})

    def test_le_premier_plan_de_surface_accepte_tout(self):
        sortie = self._motifs(u'Surface', u'Foreground')
        self.assertEqual([m['id'] for m in sortie['motifs']], [-1, 1001, 1002])
        self.assertEqual(sortie['contrainte'], u'')

    def test_les_trois_autres_emplacements_excluent_le_modele(self):
        for face, couche in ((u'Cut', u'Foreground'), (u'Cut', u'Background'),
                             (u'Surface', u'Background')):
            sortie = self._motifs(face, couche)
            self.assertEqual([m['id'] for m in sortie['motifs']], [-1, 1001],
                             u'%s.%s' % (face, couche))
            self.assertTrue(sortie['contrainte'])

    def test_un_motif_interdit_deja_en_place_reste_propose(self):
        # Matériau hérité d'un vieux gabarit ou d'un fichier lié : sans ça la
        # fenêtre s'ouvre sur du vide et le premier changement de couleur
        # effacerait le motif sans le dire.
        sortie = self._motifs(u'Cut', u'Foreground', courant=1002)
        self.assertEqual([m['id'] for m in sortie['motifs']],
                         [1002, -1, 1001])
        self.assertEqual(sortie['courant'], 1002)

    def test_le_titre_situe_l_emplacement(self):
        self.assertEqual(self._motifs(u'Cut', u'Foreground')['titre'],
                         u'Coupe · premier plan')


#: Faux `StorageType` : seul `String` nous intéresse, c'est lui qui décide
#: qu'un paramètre est modifiable dans la page.
class FakeStockage(object):
    String = 'String'
    Double = 'Double'


class FakeDefinition(object):
    def __init__(self, identifiant, nom):
        self.Id = identifiant
        self.Name = nom


class FakeParametre(object):
    def __init__(self, identifiant, nom, valeur, texte=True, fige=False):
        self.Definition = FakeDefinition(identifiant, nom)
        self.StorageType = FakeStockage.String if texte else FakeStockage.Double
        self.IsReadOnly = fige
        self.valeur = valeur

    def AsString(self):
        return self.valeur

    def AsValueString(self):
        return self.valeur


class TestIdentite(unittest.TestCase):
    """L'onglet Identité lit la liste de Revit, pas une énumération écrite à
    la main : on simule donc `Material.GetIdentityParameterIds`."""

    def setUp(self):
        # `Material` et `StorageType` sont None hors Revit : on les pose le
        # temps du test, et on les remet après.
        self._anciens = (presentation.Material, presentation.StorageType)
        self.addCleanup(self._rendre)
        presentation.StorageType = FakeStockage

        class FakeMaterialStatique(object):
            @staticmethod
            def GetIdentityParameterIds():
                return [-11, -12, -13]      # l'ordre de Revit, pas l'alphabet

        presentation.Material = FakeMaterialStatique

    def _rendre(self):
        presentation.Material, presentation.StorageType = self._anciens

    def _materiau(self):
        return FakeMateriau(1, u'Béton', parametres=[
            FakeParametre(-99, u'Paramètre hors identité', u'x'),
            FakeParametre(-12, u'Fabricant', u'Lafarge'),
            FakeParametre(-11, u'Description', u'Béton banché'),
            FakeParametre(-13, u'Coût', u'12,50 €', texte=False),
        ])

    def test_seuls_les_parametres_declares_par_revit_sortent(self):
        noms = [p['nom'] for p in presentation.identite(self._materiau())]
        self.assertEqual(noms, [u'Description', u'Fabricant', u'Coût'])

    def test_l_ordre_est_celui_de_revit(self):
        # Ni l'ordre des paramètres du matériau, ni l'alphabet : celui de
        # l'onglet Identité, pour que la page ressemble à ce que Revit montre.
        sortie = presentation.identite(self._materiau())
        self.assertEqual([p['id'] for p in sortie], [-11, -12, -13])

    def test_seul_le_texte_est_annonce_modifiable(self):
        # Un coût porte une devise : le poser dans un champ texte ferait
        # écrire un nombre dans la monnaie du voisin.
        par_nom = dict((p['nom'], p) for p in
                       presentation.identite(self._materiau()))
        self.assertTrue(par_nom[u'Fabricant']['modifiable'])
        self.assertFalse(par_nom[u'Coût']['modifiable'])

    def test_un_parametre_fige_n_est_pas_modifiable(self):
        materiau = FakeMateriau(1, u'Béton', parametres=[
            FakeParametre(-11, u'Description', u'lu', fige=True)])
        self.assertFalse(presentation.identite(materiau)[0]['modifiable'])

    def test_seul_ce_qui_a_bouge_part_en_ecriture(self):
        materiau = self._materiau()
        changes = presentation.identite_modifiee(
            {u'-11': u'Béton banché',        # inchangé
             u'-12': u'Vicat',               # changé
             u'-13': u'0 €',                 # non modifiable
             u'-99': u'pirate'},             # hors identité
            materiau)
        self.assertEqual(changes, {-12: u'Vicat'})

    def test_les_parametres_partent_au_service_avec_les_attributs(self):
        materiau = self._materiau()
        ordres, service = _ordres()
        ordres._materiaux[1] = materiau
        ordres.traiter({'ordre': 'enregistrer', 'id': 1,
                        'valeurs': {'MaterialClass': u'Béton'},
                        'identite': {u'-12': u'Vicat'}})
        appel = [a for a in service.appels if a[0] == 'enregistrer'][0]
        self.assertEqual(appel[1], {'MaterialClass': u'Béton'})
        self.assertEqual(appel[2], {-12: u'Vicat'})

    def test_sans_rien_de_change_le_service_n_est_pas_appele(self):
        materiau = self._materiau()
        ordres, service = _ordres()
        ordres._materiaux[1] = materiau
        sortie = ordres.traiter({'ordre': 'enregistrer', 'id': 1,
                                 'valeurs': {}, 'identite': {}})
        self.assertTrue(sortie['ok'])
        self.assertEqual([a for a in service.appels if a[0] == 'enregistrer'],
                         [])


class TestEtat(unittest.TestCase):
    def test_une_maquette_en_lecture_seule_se_dit_avant_le_premier_clic(self):
        ordres, _ = _ordres(doc=FakeDocument(lecture_seule=True))
        self.assertFalse(ordres.traiter({'ordre': 'pret'})['modifiable'])

    def test_l_etat_porte_les_cartes_et_les_categories(self):
        ordres, _ = _ordres()
        etat = ordres.traiter({'ordre': 'pret'})
        self.assertEqual(len(etat['cartes']), 3)
        self.assertEqual([c['nom'] for c in etat['categories']],
                         [u'Murs', u'Sols'])

    def test_un_ordre_inconnu_leve(self):
        # L'hôte transforme l'exception en réponse d'erreur : la page ne
        # reste jamais pendue sur une promesse sans réponse.
        ordres, _ = _ordres()
        self.assertRaises(ValueError, ordres.traiter, {'ordre': 'danser'})


if __name__ == '__main__':
    unittest.main()
