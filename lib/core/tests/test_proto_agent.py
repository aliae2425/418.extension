# -*- coding: utf-8 -*-
"""Le protocole de parts et l'agent fictif, éprouvés hors Revit.

Ce qui compte ici n'est pas le scénario — il est faux par construction — mais
les invariants que l'interface tiendra pour acquis : des deltas qui portent le
morceau et pas le cumul, un `tour.fini` qui arrive toujours, et un irréversible
qui ne part JAMAIS sans accord.
"""
from __future__ import unicode_literals
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from core import chat_parts as cp                              # noqa: E402
from core.proto_agent import ProtoAgent, Interrompu            # noqa: E402


def _flux():
    """Un flux qui range ses évènements au lieu de les poster."""
    recus = []
    return cp.Flux(lambda e, c: recus.append((e, c))), recus


def _agent(accord=None, coupe=None):
    flux, recus = _flux()
    # `dormir` neutralisé : une suite qui attend trois secondes par scénario
    # ne se lance plus, donc personne ne la lance.
    return ProtoAgent(flux, accord=accord, coupe=coupe,
                      dormir=lambda _s: None), recus


def _texte(recus):
    """Le texte reconstitué depuis les deltas, comme le fait l'interface."""
    morceaux = []
    for evenement, charge in recus:
        if evenement == cp.DELTA:
            morceaux.append(charge['morceau'])
    return ''.join(morceaux)


def _parts(recus, genre):
    return [c for e, c in recus if e == cp.NEUVE and c['genre'] == genre]


class TestPart(unittest.TestCase):

    def test_genre_inconnu_refuse(self):
        self.assertRaises(ValueError, cp.Part, 'p1', 'chanson')

    def test_json_omet_les_champs_vides(self):
        # Une part pleine de clés vides se lit mal côté interface, et chaque
        # clé inutile repart à chaque évènement.
        charge = cp.Part('p1', cp.TEXTE, texte='bonjour').json()
        self.assertEqual({'id': 'p1', 'genre': 'texte', 'texte': 'bonjour'},
                         charge)

    def test_json_garde_les_arguments_doutil(self):
        charge = cp.Part('p1', cp.OUTIL, nom='revit_etat',
                         arguments={'limite': 5}, etat=cp.EN_COURS).json()
        self.assertEqual('revit_etat', charge['nom'])
        self.assertEqual({'limite': 5}, charge['arguments'])


class TestFlux(unittest.TestCase):

    def test_les_identifiants_se_suivent(self):
        flux, recus = _flux()
        flux.ouvrir(cp.TEXTE)
        flux.ouvrir(cp.ETAPE, texte='hop')
        self.assertEqual(['p1', 'p2'], [c['id'] for e, c in recus
                                        if e == cp.NEUVE])

    def test_le_delta_porte_le_morceau_pas_le_cumul(self):
        # L'invariant qui sépare un flux d'un diaporama : renvoyer la part
        # entière à chaque jeton ferait repeindre toute la bulle.
        flux, recus = _flux()
        part = flux.ouvrir(cp.TEXTE)
        flux.ajouter(part, 'bon')
        flux.ajouter(part, 'jour')
        deltas = [c['morceau'] for e, c in recus if e == cp.DELTA]
        self.assertEqual(['bon', 'jour'], deltas)
        self.assertEqual('bonjour', part.texte)

    def test_un_delta_vide_ne_part_pas(self):
        flux, recus = _flux()
        flux.ajouter(flux.ouvrir(cp.TEXTE), '')
        self.assertEqual([], [c for e, c in recus if e == cp.DELTA])

    def test_changer_un_champ_inconnu_refuse(self):
        # Sans ça, une faute de frappe poserait un attribut neuf en silence
        # et l'interface ne verrait jamais le changement attendu.
        flux, _recus = _flux()
        part = flux.ouvrir(cp.OUTIL, nom='revit_etat')
        self.assertRaises(ValueError, flux.changer, part, etta=cp.FAIT)

    def test_dernier_id_suit_la_derniere_part(self):
        # C'est par lui que le volet sait à QUELLE part répondre quand
        # l'architecte accorde un outil.
        flux, _recus = _flux()
        self.assertEqual('', flux.dernier_id())
        flux.ouvrir(cp.TEXTE)
        self.assertEqual('p1', flux.dernier_id())
        flux.ouvrir(cp.OUTIL, nom='revit_synchroniser')
        self.assertEqual('p2', flux.dernier_id())

    def test_encoder_nechappe_pas_les_accents(self):
        # ensure_ascii=False : laisser json échapper les accents lève sous
        # IronPython 2.7, et ça reste invisible ici. Le test fige la forme.
        brut = cp.encoder(cp.NEUVE, {'texte': 'élévation'})
        self.assertIn('élévation', brut)
        self.assertEqual('élévation', json.loads(brut)['charge']['texte'])


class TestScenarios(unittest.TestCase):

    def test_le_tour_finit_toujours(self):
        # Sans `tour.fini`, l'interface resterait bloquée sur « réfléchit… ».
        for question in ('bonjour', 'liste mes vues', 'fais une erreur',
                         'synchronise le projet'):
            agent, recus = _agent(accord=lambda n, a: False)
            agent.repondre(question)
            self.assertEqual(1, len([e for e, _c in recus if e == cp.FINI]),
                             'pas exactement un tour.fini pour ' + question)

    def test_le_scenario_simple_repond_sans_outil(self):
        agent, recus = _agent()
        agent.repondre('bonjour')
        self.assertEqual([], _parts(recus, cp.OUTIL))
        self.assertIn('fictif', _texte(recus))

    def test_le_scenario_outils_enchaine_deux_lectures(self):
        agent, recus = _agent()
        agent.repondre('liste mes vues')
        noms = [c['nom'] for c in _parts(recus, cp.OUTIL)]
        self.assertEqual(['revit_etat', 'revit_vues'], noms)

    def test_un_outil_qui_echoue_le_dit(self):
        agent, recus = _agent()
        agent.repondre('fais une erreur')
        etats = [c['etat'] for e, c in recus
                 if e == cp.MAJ and c['genre'] == cp.OUTIL]
        self.assertEqual([cp.ECHEC], etats)


class TestAccordIrreversible(unittest.TestCase):
    """Le garde-fou. Une consigne système ne vaut rien ici : c'est le modèle
    lui-même qui déciderait de la respecter, et c'est lui qu'on surveille."""

    def test_sans_accord_loutil_est_refuse(self):
        agent, recus = _agent(accord=lambda nom, args: False)
        agent.repondre('synchronise le projet')
        etats = [c['etat'] for e, c in recus
                 if e == cp.MAJ and c['nom'] == 'revit_synchroniser']
        self.assertEqual([cp.REFUSE], etats)
        self.assertNotIn(cp.FAIT, etats)

    def test_sans_interface_pour_demander_cest_un_refus(self):
        # Pas de rappel d'accord = personne pour répondre. Ouvrir en grand
        # serait l'inverse exact de ce que ce verrou existe pour faire.
        agent, recus = _agent(accord=None)
        agent.repondre('synchronise le projet')
        etats = [c['etat'] for e, c in recus
                 if e == cp.MAJ and c['nom'] == 'revit_synchroniser']
        self.assertEqual([cp.REFUSE], etats)

    def test_avec_accord_loutil_part(self):
        agent, recus = _agent(accord=lambda nom, args: True)
        agent.repondre('synchronise le projet')
        etats = [c['etat'] for e, c in recus
                 if e == cp.MAJ and c['nom'] == 'revit_synchroniser']
        self.assertEqual([cp.EN_COURS, cp.FAIT], etats)

    def test_laccord_recoit_le_nom_et_les_arguments(self):
        # L'architecte doit voir CE qu'il autorise, pas seulement qu'on lui
        # demande quelque chose.
        vus = []

        def accord(nom, arguments):
            vus.append((nom, arguments))
            return False

        agent, _recus = _agent(accord=accord)
        agent.repondre('synchronise le projet')
        self.assertEqual(1, len(vus))
        nom, arguments = vus[0]
        self.assertEqual('revit_synchroniser', nom)
        self.assertTrue(arguments.get('liberer_tout'))

    def test_la_part_attend_laccord_avant_de_partir(self):
        # L'état `attente_accord` est ce qui fait apparaître les boutons dans
        # le fil : sans lui, l'interface n'a rien à dessiner.
        agent, recus = _agent(accord=lambda n, a: True)
        agent.repondre('synchronise le projet')
        neuves = _parts(recus, cp.OUTIL)
        self.assertEqual(cp.ATTENTE_ACCORD, neuves[0]['etat'])


class TestInterruption(unittest.TestCase):

    def test_couper_arrete_le_tour(self):
        agent, recus = _agent(coupe=lambda: True)
        agent.repondre('liste mes vues')
        self.assertEqual([('raison', 'interrompu')],
                         [(k, v) for e, c in recus if e == cp.FINI
                          for k, v in c.items()])

    def test_couper_nemet_pas_derreur(self):
        # Une interruption demandée n'est pas une panne : l'afficher en rouge
        # ferait croire à un échec.
        agent, recus = _agent(coupe=lambda: True)
        agent.repondre('liste mes vues')
        self.assertEqual([], _parts(recus, cp.ERREUR))

    def test_une_panne_du_scenario_devient_une_part_erreur(self):
        agent, recus = _agent()

        def _casse():
            raise ValueError('boum')

        agent._penser = _casse
        agent.repondre('bonjour')
        self.assertEqual(1, len(_parts(recus, cp.ERREUR)))
        self.assertEqual(1, len([e for e, _c in recus if e == cp.FINI]))


if __name__ == '__main__':
    unittest.main()
