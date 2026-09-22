# -*- coding: utf-8 -*-
"""Client de chat OpenAI, sans dépendance.

``urllib`` seul : ni ``requests`` ni le SDK ``openai`` ne sont disponibles
dans le CPython embarqué de pyRevit, encore moins sous IronPython.

Logique pure (aucun import Revit ni WPF) pour rester testable hors Revit.
"""
from __future__ import unicode_literals
import json
import os

try:                                   # CPython 3
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
except ImportError:                    # IronPython 2.7
    from urllib2 import Request, urlopen, HTTPError, URLError

try:
    from core.journal import journal
except Exception:
    from lib.core.journal import journal

_log = journal('openai')

URL = 'https://api.openai.com/v1/chat/completions'
URL_MODELES = 'https://api.openai.com/v1/models'
CLE_ENV = 'OPENAI_API_KEY'
MODELE_ENV = 'OPENAI_MODEL'
MODELE_DEFAUT = 'gpt-4o-mini'

SYSTEME = ("Tu assistes un architecte dans Autodesk Revit. Réponds en "
           "français, brièvement. Les #références citent des éléments de la "
           "maquette ; tu n'y as pas encore accès, demande-les si besoin.")


_MODELES = []                          # cache mémoire de /v1/models


class ErreurOpenAI(Exception):
    """Échec d'appel : clé absente, réseau, ou réponse illisible."""


def pret():
    return bool(os.environ.get(CLE_ENV))


def raison():
    return 'clé absente — définir la variable d\'environnement ' + CLE_ENV


def connecter():
    """Pas de connexion par navigateur ici : la clé se pose à la main."""
    return None


def modeles():
    """Modèles de conversation du compte, ``()`` si on ne peut pas demander."""
    if _MODELES:
        return tuple(_MODELES)
    cle = os.environ.get(CLE_ENV)
    if not cle:
        return ()
    requete = Request(URL_MODELES)
    requete.add_header('Authorization', 'Bearer ' + cle)
    try:
        brut = urlopen(requete, timeout=15).read().decode('utf-8')
        catalogue = json.loads(brut)['data']
    except Exception:
        return ()
    # Le compte expose aussi les modèles d'image, d'audio et d'embedding :
    # seuls les modèles de conversation ont leur place dans /model.
    noms = sorted(set(
        entree['id'] for entree in catalogue
        if entree.get('id', '').startswith(('gpt-', 'o1', 'o3', 'o4'))
        and not any(exclu in entree['id']
                    for exclu in ('audio', 'image', 'realtime', 'tts',
                                  'transcribe', 'embedding'))))
    _MODELES.extend(noms)
    return tuple(noms)


def charge(messages, modele=None):
    """Corps de la requête. ``messages`` : liste de couples (role, texte)."""
    return {
        'model': modele or os.environ.get(MODELE_ENV) or MODELE_DEFAUT,
        'messages': ([{'role': 'system', 'content': SYSTEME}] +
                     [{'role': role, 'content': texte}
                      for role, texte in messages]),
    }


def repondre(messages, cle=None, modele=None, timeout=60):
    """Renvoie le texte de la réponse, ou lève ``ErreurOpenAI``."""
    cle = cle or os.environ.get(CLE_ENV)
    if not cle:
        raise ErreurOpenAI(raison())

    # ensure_ascii=False : sous IronPython, laisser json échapper lui-même
    # les accents lève. On encode explicitement derrière.
    corps = json.dumps(charge(messages, modele), ensure_ascii=False)
    requete = Request(URL, data=corps.encode('utf-8'))
    requete.add_header('Content-Type', 'application/json; charset=utf-8')
    requete.add_header('Authorization', 'Bearer ' + cle)

    try:
        brut = urlopen(requete, timeout=timeout).read().decode('utf-8')
    except HTTPError as e:
        detail = _detail(e)
        _log.error('HTTP %s — %s', e.code, detail)
        raise ErreurOpenAI('HTTP {0} — {1}'.format(e.code, detail))
    except URLError as e:
        _log.error('réseau injoignable — %s', getattr(e, 'reason', e))
        raise ErreurOpenAI('réseau injoignable — {0}'.format(
            getattr(e, 'reason', e)))
    return extraire(brut)


def extraire(brut):
    """Texte du premier choix d'une réponse de l'API."""
    try:
        return json.loads(brut)['choices'][0]['message']['content'].strip()
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        raise ErreurOpenAI('réponse illisible — {0}'.format(brut[:200]))


def _detail(erreur):
    """Message d'erreur de l'API plutôt que le corps brut, s'il s'y trouve."""
    try:
        return json.loads(erreur.read().decode('utf-8'))['error']['message']
    except Exception:
        return getattr(erreur, 'reason', '') or ''
