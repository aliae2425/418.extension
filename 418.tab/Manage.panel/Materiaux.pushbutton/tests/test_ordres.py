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

from lib.services.ordres import Ordres


class FakeMateriau(object):
    def __init__(self, identifiant, nom):
        self.Id = identifiant          # un entier suffit : `ident` l'accepte
        self.Name = nom


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

    def analyser(self, sources, categories=None):
        self.appels.append(('analyser', list(sources), categories))
        return self._rapport

    def remplacer(self, sources, cible, categories=None):
        self.appels.append(('remplacer', list(sources), cible, categories))
        return self._rapport


class FakeCatalogue(object):
    """Les deux seules choses que `Ordres` demande au catalogue : la liste
    des catégories, et la traduction entier -> identifiant Revit."""

    def __init__(self, categories=()):
        self.categories = [{'id': i, 'nom': nom}
                           for (i, nom) in categories]
        self.motifs = []
        self.apparences = []

    def element_id(self, identifiant):
        return u'eid:%s' % identifiant


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
