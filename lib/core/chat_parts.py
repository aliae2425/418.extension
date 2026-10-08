# -*- coding: utf-8 -*-
"""Le protocole entre le moteur et l'interface : des *parts* et des évènements.

C'est la leçon d'opencode qu'on retient, et la seule qui coûte peu :
**un message n'est pas une chaîne**. Il est une suite de parts typées, et un
évènement porte une part, pas un message. Sans ça, pas de rendu incrémental :
on ne peut pas peindre au fil de l'eau ce qu'on ne reçoit qu'entier — c'est
exactement ce qui fait attendre 60 s devant une bulle vide aujourd'hui.

opencode en déclare neuf (`text, tool, reasoning, step-start, step-finish,
patch, file, compaction, agent`). On en prend cinq, parce qu'on n'a pas de
fichiers à montrer ni de compactage à tracer :

| genre | ce qu'il porte |
|---|---|
| `texte` | ce que le modèle dit, poussé delta par delta |
| `raisonnement` | ce qu'il se dit à lui-même, repliable |
| `outil` | un appel : son nom, ses arguments, son état, sa sortie |
| `etape` | une frontière de tour — ce qui comble l'attente |
| `erreur` | ce qui a cassé, dit à l'architecte et pas seulement au modèle |

Et trois évènements, qui suffisent :

| évènement | quand |
|---|---|
| `part.neuve` | une part apparaît |
| `part.delta` | du texte s'ajoute à une part existante |
| `part.maj` | l'état d'une part change (un outil finit, échoue) |

L'accord sur un outil irréversible n'est pas un évènement de plus : c'est une
part `outil` dont l'état passe à `attente_accord`, et l'interface répond. Le
garde-fou reste côté moteur — une interface qui ne répondrait pas laisse
l'outil refusé, jamais ouvert.

Logique pure : aucun import Revit, WPF ni réseau. Testable hors Revit.
"""
from __future__ import unicode_literals
import json

# --- genres de parts -------------------------------------------------------

TEXTE = 'texte'
RAISONNEMENT = 'raisonnement'
OUTIL = 'outil'
ETAPE = 'etape'
ERREUR = 'erreur'

GENRES = (TEXTE, RAISONNEMENT, OUTIL, ETAPE, ERREUR)

# --- états d'une part `outil` ---------------------------------------------

EN_COURS = 'en_cours'
ATTENTE_ACCORD = 'attente_accord'
FAIT = 'fait'
REFUSE = 'refuse'
ECHEC = 'echec'

# --- évènements ------------------------------------------------------------

NEUVE = 'part.neuve'
DELTA = 'part.delta'
MAJ = 'part.maj'
FINI = 'tour.fini'


class Part(object):
    """Un morceau de réponse. Son `id` est ce qui rend les deltas possibles."""

    def __init__(self, identifiant, genre, texte='', nom='', arguments=None,
                 etat='', sortie=''):
        if genre not in GENRES:
            raise ValueError('genre inconnu : {0}'.format(genre))
        self.id = identifiant
        self.genre = genre
        self.texte = texte
        self.nom = nom                     # parts `outil` seulement
        self.arguments = arguments or {}
        self.etat = etat
        self.sortie = sortie

    def json(self):
        """La forme qui part à l'interface. Pas de clé vide : ça se lit mal."""
        charge = {'id': self.id, 'genre': self.genre}
        for cle, valeur in (('texte', self.texte), ('nom', self.nom),
                            ('etat', self.etat), ('sortie', self.sortie)):
            if valeur:
                charge[cle] = valeur
        if self.arguments:
            charge['arguments'] = self.arguments
        return charge


class Flux(object):
    """Émet des évènements vers l'interface, en numérotant les parts.

    ``sortie(evenement, charge)`` est le seul point de contact : le panneau y
    branche un ``PostWebMessageAsJson``, un test y branche une liste. Le
    moteur, lui, ne sait pas qu'une interface existe.
    """

    def __init__(self, sortie):
        self._sortie = sortie
        self._rang = 0
        self._parts = {}

    # --- création ---------------------------------------------------------

    def ouvrir(self, genre, **champs):
        """Déclare une part neuve et la renvoie. L'interface la dessine vide."""
        self._rang += 1
        part = Part('p{0}'.format(self._rang), genre, **champs)
        self._parts[part.id] = part
        self._dire(NEUVE, part.json())
        return part

    # --- alimentation -----------------------------------------------------

    def ajouter(self, part, morceau):
        """Du texte de plus. On n'envoie QUE le morceau, pas le cumul.

        Renvoyer la part entière à chaque jeton ferait repeindre toute la
        bulle à chaque fois : c'est la différence entre un flux et un
        diaporama.
        """
        if not morceau:
            return part
        part.texte += morceau
        self._dire(DELTA, {'id': part.id, 'morceau': morceau})
        return part

    def changer(self, part, **champs):
        """Change l'état d'une part — un outil qui finit, échoue, attend."""
        for cle, valeur in champs.items():
            if not hasattr(part, cle):
                raise ValueError('champ inconnu : {0}'.format(cle))
            setattr(part, cle, valeur)
        self._dire(MAJ, part.json())
        return part

    # --- fin de tour ------------------------------------------------------

    def fini(self, raison=''):
        """Le pendant de `session.idle` : l'interface rend la main à la saisie."""
        self._dire(FINI, {'raison': raison} if raison else {})

    # --- sortie -----------------------------------------------------------

    def _dire(self, evenement, charge):
        self._sortie(evenement, charge)

    def parts(self):
        """Les parts émises, dans l'ordre. Pour les tests et la relecture."""
        return [self._parts['p{0}'.format(n)]
                for n in range(1, self._rang + 1)]

    def dernier_id(self):
        """L'id de la dernière part ouverte, ``''`` s'il n'y en a aucune.

        L'interface a besoin de savoir à QUELLE part répondre quand elle
        accorde un outil. Le demander au flux évite de le deviner depuis un
        compteur tenu ailleurs — et ça se teste.
        """
        return 'p{0}'.format(self._rang) if self._rang else ''


def encoder(evenement, charge):
    """Un évènement prêt pour ``PostWebMessageAsJson``.

    ``ensure_ascii=False`` puis encodage explicite : sous IronPython 2.7,
    laisser json échapper les accents lui-même lève — et ça reste invisible
    en test CPython.
    """
    return json.dumps({'evenement': evenement, 'charge': charge},
                      ensure_ascii=False)
