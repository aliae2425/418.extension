# -*- coding: utf-8 -*-
"""Où vivent les secrets : hors du dépôt, toujours.

``data/`` finit poussé — c'est arrivé, et une clé dans un dépôt ne se
rattrape pas par un commit de suppression. Les secrets vont donc dans
``%LOCALAPPDATA%\\418.extension\\``, qui n'est ni versionné ni synchronisé,
et qu'une copie de l'extension n'emporte pas.

Deux sources pour une clé, et l'ordre compte :

1. ce que l'architecte a posé par ``/connect`` ;
2. la variable d'environnement, pour les postes réglés par l'IT.

Le fichier gagne : taper ``/connect`` et ne rien voir changer parce qu'une
variable traîne serait incompréhensible. ``/logout`` efface le fichier et
retombe sur la variable, en le disant.

Logique pure (aucun import Revit ni WPF) pour rester testable hors Revit.
"""
from __future__ import unicode_literals
import io
import json
import os

try:
    from core.journal import journal
except Exception:
    from lib.core.journal import journal

_log = journal('secrets')

FICHIER = 'auth.json'


def dossier():
    """``%LOCALAPPDATA%\\418.extension``, créé si absent.

    ponytail: pas d'ACL posée. `%LOCALAPPDATA%` est déjà par utilisateur, et
    `os.chmod` ne gouverne sous Windows que le bit lecture seule — il
    donnerait l'illusion d'une protection sans en poser une. Le jour où ça
    compte, c'est `icacls` qu'il faut, pas `chmod`.
    """
    racine = (os.environ.get('LOCALAPPDATA')
              or os.path.expanduser('~'))
    chemin = os.path.join(racine, '418.extension')
    try:
        if not os.path.isdir(chemin):
            os.makedirs(chemin)
    except Exception:
        _log.exception('dossier des secrets injoignable')
    return chemin


def _chemin():
    return os.path.join(dossier(), FICHIER)


def _lire():
    try:
        with io.open(_chemin(), encoding='utf-8') as ouvert:
            charge = json.loads(ouvert.read() or '{}')
    except Exception:
        return {}
    return charge if isinstance(charge, dict) else {}


def _ecrire(charge):
    try:
        # ensure_ascii=False : sous IronPython 2.7, laisser json échapper les
        # accents lui-même lève. On écrit en UTF-8 explicitement.
        brut = json.dumps(charge, ensure_ascii=False, indent=2)
        with io.open(_chemin(), 'w', encoding='utf-8') as ouvert:
            ouvert.write(brut if isinstance(brut, type('')) else brut.decode('utf-8'))
        return True
    except Exception:
        _log.exception('écriture des secrets impossible')
        return False


# Une clé par fournisseur : ils n'ont ni le même format, ni la même
# facturation, et en poser une ne doit pas effacer l'autre. La variable
# d'environnement de repli diffère aussi.
FOURNISSEURS = {
    'openai': {'champ': 'cle', 'variable': 'OPENAI_API_KEY'},
    'anthropic': {'champ': 'cle_anthropic', 'variable': 'ANTHROPIC_API_KEY'},
}


def _fiche(fournisseur):
    return FOURNISSEURS.get(fournisseur or 'openai') or FOURNISSEURS['openai']


def cle(fournisseur='openai'):
    """La clé à employer, ``''`` s'il n'y en a aucune. Le fichier d'abord."""
    fiche = _fiche(fournisseur)
    posee = (_lire().get(fiche['champ']) or '').strip()
    if posee:
        return posee
    return (os.environ.get(fiche['variable']) or '').strip()


def poser_cle(valeur, fournisseur='openai'):
    """Range la clé. ``True`` si c'est écrit.

    Aucune validation de forme : les préfixes changent au gré des
    fournisseurs, et refuser une clé valide parce qu'elle ne commence pas par
    ``sk-`` serait pire que de laisser l'API répondre 401.
    """
    valeur = (valeur or '').strip()
    if not valeur:
        return False
    charge = _lire()
    charge[_fiche(fournisseur)['champ']] = valeur
    pose = _ecrire(charge)
    # Jamais la valeur au journal, même tronquée.
    _log.info('clé %s posée : %s', fournisseur, 'oui' if pose else 'échec')
    return pose


def oublier_cle(fournisseur=None):
    """Efface la ou les clés rangées. Ne touche PAS aux variables d'environnement.

    Sans argument, efface TOUT : c'est ce que `/logout` veut dire, et laisser
    une clé derrière ferait croire à une déconnexion qui n'en est pas une.

    Un fournisseur inconnu n'efface RIEN. `_fiche()` retombe sur OpenAI, ce qui
    est sans danger pour une lecture et désastreux ici : `/logout anthropc`
    effacerait la clé OpenAI sans rien dire.
    """
    if fournisseur and fournisseur not in FOURNISSEURS:
        _log.warning('fournisseur inconnu, rien effacé : %s', fournisseur)
        return False
    charge = _lire()
    champs = ([FOURNISSEURS[fournisseur]['champ']] if fournisseur
              else [f['champ'] for f in FOURNISSEURS.values()])
    efface = False
    for champ in champs:
        if champ in charge:
            del charge[champ]
            efface = True
    if efface:
        _ecrire(charge)
        _log.info('clé(s) effacée(s) : %s', ', '.join(champs))
    return efface


# --- jetons OAuth ---------------------------------------------------------

def jetons():
    """Les jetons de session, ``{}`` s'il n'y en a pas."""
    lus = _lire().get('jetons')
    return lus if isinstance(lus, dict) else {}


def poser_jetons(valeurs):
    charge = _lire()
    charge['jetons'] = valeurs or {}
    pose = _ecrire(charge)
    # Jamais la valeur au journal, même tronquée.
    _log.info('jetons posés : %s', 'oui' if pose else 'échec')
    return pose


def oublier_jetons():
    charge = _lire()
    if 'jetons' not in charge:
        return False
    del charge['jetons']
    _ecrire(charge)
    _log.info('jetons effacés')
    return True
