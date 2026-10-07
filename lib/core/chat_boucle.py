# -*- coding: utf-8 -*-
"""La boucle d'outils, commune aux clients qui en ont une.

Elle vivait dans ``chat_oauth``, donc un seul fournisseur voyait la maquette :
la connexion qui accepte les PDF était justement celle qui n'avait pas d'yeux,
et l'inverse. C'était une asymétrie d'implémentation, pas de protocole.

Ce qui est VRAIMENT commun tient en trois choses, et elles sont ici : le
catalogue, l'exécution d'un outil, et la règle du dernier tour. Le reste —
forme du corps, lecture des appels, rangement des résultats — appartient au
protocole de chacun et reste chez lui : ``/v1/chat/completions`` imbrique les
outils sous « function », le backend Responses les pose à plat, et aucune
abstraction ne rendra ces deux-là identiques sans mentir.

Logique pure (aucun import Revit ni WPF) pour rester testable hors Revit.
"""
from __future__ import unicode_literals
import json

try:
    from core.journal import journal
except Exception:
    from lib.core.journal import journal

try:
    from core import revit_outils
except Exception:
    try:
        from lib.core import revit_outils
    except Exception:
        revit_outils = None            # sans lui, le chat reste sans outils

_log = journal('boucle')

# Repli quand la maquette n'est pas joignable : ``revit_outils`` tient le
# plafond réel, c'est lui qui sait ce qu'un modèle qui boucle coûte.
TOURS = 5

REFUS = ('refusé par l\'architecte — ne pas réessayer sans une demande '
         'explicite de sa part')
SANS_INTERFACE = ('aucune interface pour demander l\'accord — outil '
                  'irréversible refusé')


def tours():
    return revit_outils.TOURS_MAX if revit_outils is not None else TOURS


def catalogue(outils=None):
    """Les outils à annoncer au modèle, ``[]`` si la maquette est muette.

    ``outils`` imposé court-circuite tout — c'est ce dont les tests se
    servent, n'ayant pas de Revit sous la main.

    Ne rien envoyer vaut mieux qu'annoncer des outils inexécutables : un
    modèle à qui l'on promet des yeux répond « je regarde » et ne regarde rien.
    """
    if outils is not None:
        return list(outils)
    if revit_outils is None:
        return []
    utilisable, _raison = revit_outils.disponible()
    return revit_outils.outils() if utilisable else []


def arguments(brut):
    """Arguments JSON d'un appel d'outil, ``{}`` s'ils sont illisibles.

    Un modèle qui bafouille son JSON ne doit pas faire échouer le tour : on
    appelle l'outil sans argument, il dira lui-même ce qui manque.
    """
    try:
        charge = json.loads(brut or '{}')
    except (ValueError, TypeError):
        return {}
    return charge if isinstance(charge, dict) else {}


def dire(avancement, texte):
    """Annonce une étape à l'interface. Ne lève jamais : ce n'est qu'affichage.

    Le rappel vient d'un fil de fond ; c'est à l'appelant de le marshaler.
    """
    if avancement is None:
        return
    try:
        avancement(texte)
    except Exception:
        _log.exception('rappel d\'avancement')


def executer(nom, donnees, avancement=None, confirmer=None):
    """Lance un outil sur la maquette et renvoie sa sortie, prête à repartir.

    Un outil IRRÉVERSIBLE (synchroniser, exporter, enregistrer, exécuter du
    code) passe d'abord par ``confirmer`` : aucun Ctrl+Z ne le défait, la
    synchronisation pousse sur le central donc chez toute l'équipe. Une
    consigne d'invite système ne vaut rien ici — c'est le modèle lui-même qui
    décide de la respecter, et c'est lui qu'on surveille.

    Pas de ``confirmer`` = pas d'interface pour demander = refus. Ouvrir en
    grand quand personne ne peut répondre serait exactement l'inverse de ce
    que ce garde-fou existe pour faire.
    """
    if revit_outils is None:
        return json.dumps({'erreur': 'outils indisponibles'},
                          ensure_ascii=False)
    if nom in revit_outils.irreversibles():
        refus = _accord(nom, donnees, avancement, confirmer)
        if refus:
            return refus
    dire(avancement, 'j\'appelle {0}…'.format(nom))
    sortie = revit_outils.executer(nom, donnees)
    _log.info('outil %s(%s) -> %s octets', nom, donnees, len(sortie))
    return sortie


def _accord(nom, donnees, avancement, confirmer):
    """``''`` si l'outil peut partir, sinon le refus à rendre au modèle."""
    if confirmer is None:
        _log.warning('IRRÉVERSIBLE %s sans interface de confirmation', nom)
        return json.dumps({'erreur': SANS_INTERFACE}, ensure_ascii=False)
    dire(avancement, 'j\'attends votre accord…')
    try:
        accorde = confirmer(nom, donnees)
    except Exception:
        # Une confirmation qui casse vaut un refus, jamais un laissez-passer.
        _log.exception('demande de confirmation')
        accorde = False
    if accorde:
        return ''
    _log.warning('IRRÉVERSIBLE %s refusé %s', nom, donnees)
    return json.dumps({'erreur': REFUS}, ensure_ascii=False)


def boucler(tour, avancement=None):
    """``tour(avec_outils)`` → ``(texte, nombre d'appels d'outils)``.

    Tant que le modèle demande des outils, on recommence. ``tour`` exécute les
    outils qu'il a lus et les range dans l'état de son protocole ; il ne rend
    un texte que le jour où il n'a plus rien à appeler.

    Au plafond, un dernier tour SANS outils plutôt qu'une erreur : le modèle a
    déjà tout lu, il lui reste à le dire — lever ici laisserait l'architecte
    avec une bulle vide après dix secondes d'attente.
    """
    plafond = tours()
    for _ in range(plafond):
        texte, appels = tour(True)
        if not appels:
            return texte
    _log.warning('plafond de %s tours d\'outils atteint', plafond)
    dire(avancement, 'je conclus…')
    texte, _appels = tour(False)
    return texte
