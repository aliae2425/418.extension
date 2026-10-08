# -*- coding: utf-8 -*-
"""Un agent FICTIF, qui n'appelle aucun modèle et ne touche pas la maquette.

Il n'existe que pour éprouver le chemin complet — moteur Python → parts →
`postMessage` → interface web — avec de vraies formes et de vrais délais,
sans dépendre d'un abonnement, d'un réseau ni d'un document ouvert.

Ce qu'il met à l'épreuve, et qui est tout l'enjeu du prototype :

- le **streaming** mot à mot (`part.delta`), et non une bulle qui tombe d'un bloc ;
- le **raisonnement** affiché à part, repliable ;
- les **appels d'outils** avec leurs états — `en_cours`, puis `fait` ou `echec` ;
- l'**accord sur un irréversible**, demandé dans le fil et non dans une modale ;
- l'**interruption** en cours de route ;
- les **étapes**, qui comblent l'attente en disant ce qui se passe.

Les noms d'outils sont ceux de `lib/rvt` — `revit_etat`, `revit_vues`,
`revit_synchroniser` — pour que les formes rendues soient celles qu'on aura
vraiment à rendre, pas des inventions qui mentiraient sur la suite.

Logique pure : aucun import Revit, WPF ni réseau. Testable hors Revit.
"""
from __future__ import unicode_literals
import time

try:
    from core import chat_parts as cp
except Exception:
    from lib.core import chat_parts as cp

# Un mot toutes les 25 ms : assez lent pour qu'on VOIE le flux, assez rapide
# pour ne pas rendre l'essai pénible. Le vrai modèle est plus irrégulier.
CADENCE = 0.025

# Ce que le faux outil met à « travailler ». Les vrais appels de lib/rvt
# tiennent entre 30 ms et quelques secondes.
TRAVAIL = 0.6


class Interrompu(Exception):
    """L'architecte a coupé en cours de route. Ce n'est pas une erreur."""


class ProtoAgent(object):
    """Rejoue un scénario selon ce qu'on lui dit, sans jamais rien deviner.

    ``accord(nom, arguments)`` doit rendre un booléen et a le droit de
    BLOQUER : on tourne sur un fil de fond. ``coupe()`` dit si l'architecte a
    demandé l'arrêt ; il est consulté entre chaque morceau, jamais pendant.
    """

    def __init__(self, flux, accord=None, coupe=None, dormir=None):
        self._flux = flux
        self._accord = accord
        self._coupe = coupe or (lambda: False)
        # Injecté pour que les tests ne dorment pas : une suite qui attend
        # trois secondes par scénario ne se lance plus.
        self._dormir = dormir if dormir is not None else time.sleep

    # --- aiguillage -------------------------------------------------------

    def repondre(self, question):
        """Joue le scénario que la question appelle. Ne lève jamais."""
        try:
            self._jouer(question or '')
        except Interrompu:
            self._flux.ouvrir(cp.ETAPE, texte='interrompu')
            self._flux.fini('interrompu')
        except Exception as e:                 # un prototype ne doit pas mourir
            self._flux.ouvrir(cp.ERREUR, texte='{0}'.format(e))
            self._flux.fini('erreur')
        else:
            self._flux.fini()

    def _jouer(self, question):
        basse = question.lower()
        if 'synchronis' in basse:
            return self._scenario_irreversible()
        if 'erreur' in basse or 'casse' in basse:
            return self._scenario_echec()
        if 'vue' in basse or 'feuille' in basse:
            return self._scenario_outils()
        return self._scenario_simple(question)

    # --- scénarios --------------------------------------------------------

    def _scenario_simple(self, question):
        """Le cas nominal : on réfléchit, on répond. Aucun outil."""
        self._penser('La demande ne porte sur aucun élément du modèle. '
                     'Je réponds de mémoire, sans ouvrir le document.')
        self._dire(
            'Je suis un agent **fictif** : aucun modèle ne me répond et je ne '
            'touche pas à la maquette. Je sers à éprouver le chemin complet — '
            'moteur Python, parts typées, postMessage, interface web.\n\n'
            'Essayez « liste mes vues » pour voir des appels d\'outils, '
            '« synchronise le projet » pour l\'accord sur un irréversible, '
            'ou « fais une erreur ».\n\n'
            'Votre question était : « {0} »'.format(question.strip()))

    def _scenario_outils(self):
        """Deux lectures enchaînées, puis une réponse qui s'appuie dessus."""
        self._penser('Il me faut l\'état du document avant de lister quoi que '
                     'ce soit — inutile d\'interroger un projet fermé.')
        self._outil('revit_etat', {},
                    '{"document": "MAISON-PDA.rvt", "revit_disponible": true}')
        self._etape('document ouvert, je peux lire')
        self._outil('revit_vues', {'type': 'FloorPlan', 'limite': 50},
                    '{"vues": 47, "exportables": 31}')
        self._dire(
            'Le projet **MAISON-PDA.rvt** contient **47 vues en plan**, dont '
            '31 exportables.\n\n'
            '| type | nombre |\n|---|---|\n| plans | 47 |\n'
            '| exportables | 31 |\n\n'
            'Les 16 restantes n\'ont pas de cartouche associé.')

    def _scenario_echec(self):
        """Un outil qui tombe. L'architecte doit le voir, pas seulement le modèle."""
        self._penser('J\'essaie la lecture directe.')
        part = self._flux.ouvrir(cp.OUTIL, nom='revit_nomenclatures',
                                 arguments={'nom': 'Surfaces'},
                                 etat=cp.EN_COURS)
        self._attendre(TRAVAIL)
        self._flux.changer(part, etat=cp.ECHEC,
                           sortie='nomenclature introuvable : « Surfaces »')
        self._dire('La nomenclature « Surfaces » n\'existe pas dans ce projet. '
                   'Voulez-vous que je liste celles qui existent ?')

    def _scenario_irreversible(self):
        """Le garde-fou 418, celui qu'aucune consigne système ne remplace.

        Un outil irréversible passe par l'accord de l'architecte. Pas de
        réponse = refus ; pas d'interface pour demander = refus aussi. Ouvrir
        en grand quand personne ne peut répondre serait l'inverse exact de ce
        que ce verrou existe pour faire.
        """
        self._penser('La synchronisation pousse sur le central : elle est '
                     'visible par toute l\'équipe et aucun Ctrl+Z ne la défait. '
                     'Je demande l\'accord avant.')
        arguments = {'commentaire': 'mise à jour des niveaux',
                     'liberer_tout': True}
        part = self._flux.ouvrir(cp.OUTIL, nom='revit_synchroniser',
                                 arguments=arguments, etat=cp.ATTENTE_ACCORD)
        accorde = False
        if self._accord is not None:
            accorde = bool(self._accord('revit_synchroniser', arguments))
        if not accorde:
            self._flux.changer(part, etat=cp.REFUSE,
                               sortie='refusé par l\'architecte')
            return self._dire('Entendu, je ne synchronise pas. '
                              'Rien n\'a été poussé sur le central.')
        self._flux.changer(part, etat=cp.EN_COURS, sortie='')
        self._attendre(TRAVAIL)
        self._flux.changer(part, etat=cp.FAIT,
                           sortie='{"synchronise": true, "emprunts": 0}')
        self._dire('Projet synchronisé. Les emprunts ont été libérés.')

    # --- briques ----------------------------------------------------------

    def _penser(self, texte):
        self._ecrire(self._flux.ouvrir(cp.RAISONNEMENT), texte)

    def _dire(self, texte):
        self._ecrire(self._flux.ouvrir(cp.TEXTE), texte)

    def _etape(self, texte):
        self._flux.ouvrir(cp.ETAPE, texte=texte)

    def _outil(self, nom, arguments, sortie):
        part = self._flux.ouvrir(cp.OUTIL, nom=nom, arguments=arguments,
                                 etat=cp.EN_COURS)
        self._attendre(TRAVAIL)
        self._flux.changer(part, etat=cp.FAIT, sortie=sortie)
        return part

    def _ecrire(self, part, texte):
        """Pousse le texte mot à mot. C'est ÇA qu'on vient éprouver.

        On recolle l'espace au mot suivant plutôt que de l'émettre seul : un
        delta vide est ignoré par `ajouter`, et on perdrait les espaces.
        """
        premier = True
        for mot in texte.split(' '):
            self._verifier()
            self._flux.ajouter(part, mot if premier else ' ' + mot)
            premier = False
            self._attendre(CADENCE)

    def _attendre(self, secondes):
        self._verifier()
        self._dormir(secondes)
        self._verifier()

    def _verifier(self):
        if self._coupe():
            raise Interrompu()
