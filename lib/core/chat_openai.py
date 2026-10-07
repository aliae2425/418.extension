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
    from core.chat_syntaxe import detail_http
    from core.prompt import systeme
    from core import chat_boucle
except Exception:
    from lib.core.journal import journal
    from lib.core.chat_syntaxe import detail_http
    from lib.core.prompt import systeme
    from lib.core import chat_boucle

_log = journal('openai')

URL = 'https://api.openai.com/v1/chat/completions'
URL_MODELES = 'https://api.openai.com/v1/models'
CLE_ENV = 'OPENAI_API_KEY'
MODELE_DEFAUT = 'gpt-4o-mini'


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


def deconnecter():
    """Rien à fermer : la clé vit dans l'environnement, pas dans une session.

    On vide tout de même le cache des modèles, qui appartient à la clé.
    """
    del _MODELES[:]
    return ('Rien à fermer : la clé vit dans {0}. Retirer la variable pour '
            'vous déconnecter.'.format(CLE_ENV))


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


def charge(messages, modele=None, pieces=None, outils=None):
    """Corps de la requête. ``messages`` : liste de couples (role, texte).

    ``pieces`` : fichiers à joindre, ``{'nom':…, 'media':…, 'b64':…}``. Ils
    partent sur le DERNIER message utilisateur — c'est la question en cours,
    et c'est le seul endroit où l'API accepte un contenu mixte sans que le
    reste de l'historique bascule en blocs.
    """
    tours = [{'role': role, 'content': texte} for role, texte in messages]
    if pieces:
        _joindre(tours, pieces)
    return corps(tours, modele, outils)


def corps(tours, modele=None, outils=None):
    """Corps de la requête à partir de tours déjà bâtis (boucle d'outils)."""
    charge_utile = {
        'model': modele or MODELE_DEFAUT,
        # Ne promettre des yeux que s'il y en a : sans outils, le modèle
        # répondrait « je regarde » sans rien voir.
        'messages': ([{'role': 'system', 'content': systeme(bool(outils))}] +
                     tours),
    }
    if outils:
        # Forme imbriquée sous « function », contrairement au backend
        # Responses de chat_oauth qui les pose à plat. Les deux API ne se
        # ressemblent qu'en surface.
        charge_utile['tools'] = [
            {'type': 'function',
             'function': {'name': outil['nom'],
                          'description': outil['description'],
                          'parameters': outil['parametres']}}
            for outil in outils]
        charge_utile['tool_choice'] = 'auto'
    return charge_utile


def _joindre(tours, pieces):
    """Bascule le dernier tour utilisateur en blocs et y pose les fichiers."""
    for tour in reversed(tours):
        if tour['role'] != 'user':
            continue
        tour['content'] = ([{'type': 'text', 'text': tour['content']}] +
                           [_piece(piece) for piece in pieces])
        return


def _piece(piece):
    """Un fichier en bloc de contenu. Une image n'a pas la même forme.

    ``image_url`` accepte un ``data:`` aussi bien qu'une URL — c'est la seule
    façon de montrer un plan qui n'est publié nulle part.
    """
    donnees = 'data:{0};base64,{1}'.format(piece['media'], piece['b64'])
    if (piece.get('media') or '').startswith('image/'):
        return {'type': 'image_url', 'image_url': {'url': donnees}}
    return {'type': 'file',
            'file': {'filename': piece['nom'], 'file_data': donnees}}


def repondre(messages, cle=None, modele=None, timeout=180, pieces=None,
             outils=None, avancement=None, confirmer=None, **_kwargs):
    """Renvoie le texte de la réponse, ou lève ``ErreurOpenAI``.

    Même boucle d'outils que ``chat_oauth`` — c'est tout l'intérêt de l'avoir
    sortie dans ``chat_boucle`` : cette connexion-ci est la seule à porter des
    PDF et des images, il aurait été absurde qu'elle soit aussi la seule
    aveugle à la maquette.
    """
    cle = cle or os.environ.get(CLE_ENV)
    if not cle:
        raise ErreurOpenAI(raison())
    catalogue = chat_boucle.catalogue(outils)
    tours = [{'role': role, 'content': texte} for role, texte in messages]
    if pieces:
        _joindre(tours, pieces)

    def tour(avec_outils):
        message = _message(_poster(
            corps(tours, modele, catalogue if avec_outils else None),
            cle, timeout))
        demandes = message.get('tool_calls') or []
        if not demandes:
            return _texte(message), 0
        # L'appel du modèle PUIS ses résultats : l'API est sans mémoire, elle
        # a besoin de relire son propre appel pour comprendre les retours.
        tours.append(message)
        for appel in demandes:
            tours.append(_retour(appel, avancement, confirmer))
        return None, len(demandes)

    return chat_boucle.boucler(tour, avancement)


def _retour(appel, avancement=None, confirmer=None):
    """Résultat d'un appel d'outil, au format que l'API attend en retour."""
    fonction = appel.get('function') or {}
    sortie = chat_boucle.executer(fonction.get('name') or '',
                                  chat_boucle.arguments(
                                      fonction.get('arguments')),
                                  avancement, confirmer)
    return {'role': 'tool', 'tool_call_id': appel.get('id'),
            'content': sortie}


def _poster(charge_utile, cle, timeout):
    """Un aller-retour, réponse déjà décodée."""
    # ensure_ascii=False : sous IronPython, laisser json échapper lui-même
    # les accents lève. On encode explicitement derrière.
    brut = json.dumps(charge_utile, ensure_ascii=False)
    requete = Request(URL, data=brut.encode('utf-8'))
    requete.add_header('Content-Type', 'application/json; charset=utf-8')
    requete.add_header('Authorization', 'Bearer ' + cle)
    try:
        return urlopen(requete, timeout=timeout).read().decode('utf-8')
    except HTTPError as e:
        message = detail_http(e)
        _log.error('%s', message)
        raise ErreurOpenAI(message)
    except URLError as e:
        _log.error('réseau injoignable — %s', getattr(e, 'reason', e))
        raise ErreurOpenAI('réseau injoignable — {0}'.format(
            getattr(e, 'reason', e)))


def _message(brut):
    """Message du premier choix d'une réponse de l'API."""
    try:
        message = json.loads(brut)['choices'][0]['message']
    except (ValueError, KeyError, IndexError, TypeError):
        raise ErreurOpenAI('réponse illisible — {0}'.format(brut[:200]))
    return message if isinstance(message, dict) else {}


def _texte(message):
    texte = message.get('content')
    if not texte:
        raise ErreurOpenAI('réponse sans texte — /journal pour le détail')
    return texte.strip()


def extraire(brut):
    """Texte du premier choix d'une réponse de l'API."""
    return _texte(_message(brut))
