# -*- coding: utf-8 -*-
"""Abonnement ChatGPT : la danse OAuth, et le tuyau que CORS nous impose.

Deux choses que JS ne peut pas faire, et rien d'autre :

1. **écouter une socket** — le navigateur revient sur ``localhost:1455``,
   et une page n'ouvre pas de port ;
2. **joindre le backend ChatGPT** — mesuré : ``chatgpt.com/backend-api`` ne
   renvoie aucun ``Access-Control-Allow-Origin``, et ``allow-credentials``
   interdit le ``*``. Une page ne peut pas lire la réponse.

**Le protocole, lui, reste en JS.** Ce module ne sait pas ce qu'est un item
Responses, un appel d'outil ou une instruction système : il reçoit un corps
déjà formé, le poste signé, et renvoie les lignes du flux une à une. C'est
``fournisseurs/chatgpt.js`` qui connaît le protocole — un fournisseur, un
module, comme pour OpenAI par clé.

Zone grise assumée, et elle n'a pas changé : on emprunte le ``client_id``
public du CLI Codex et un drapeau de flux Codex. opencode fait exactement
pareil. La seule chose qu'on ne fait pas, c'est se faire passer pour lui —
``originator`` dit ``418``, là où l'ancien code disait ``codex_cli_rs``.
OpenAI peut fermer ça sans préavis ; le repli est ``/connect <clé>``.

Logique pure (aucun import Revit ni WPF) pour rester testable hors Revit.
"""
from __future__ import unicode_literals
import base64
import hashlib
import json
import os
import time

try:                                   # CPython 3
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
    from urllib.parse import urlencode, urlparse, parse_qs
    from http.server import BaseHTTPRequestHandler, HTTPServer
except ImportError:                    # IronPython 2.7
    from urllib2 import Request, urlopen, HTTPError, URLError
    from urllib import urlencode
    from urlparse import urlparse, parse_qs
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

try:
    from core.journal import journal
    from harnais import secrets
except Exception:
    from lib.core.journal import journal
    from lib.harnais import secrets

_log = journal('oauth')

# Le client public du CLI Codex. Emprunté, comme chez opencode.
CLIENT = 'app_EMoamEEZ73f0CkXaXp7hrann'
URL_AUTORISATION = 'https://auth.openai.com/oauth/authorize'
URL_JETONS = 'https://auth.openai.com/oauth/token'
URL_REPONSES = 'https://chatgpt.com/backend-api/codex/responses'

PORT = 1455
CHEMIN_RAPPEL = '/auth/callback'
REDIRECTION = 'http://localhost:{0}{1}'.format(PORT, CHEMIN_RAPPEL)
PORTEE = 'openid profile email offline_access'

# On se nomme. L'ancien code envoyait `codex_cli_rs` — il prétendait ÊTRE
# Codex. opencode envoie `opencode` ; on envoie `418`.
ORIGINATEUR = '418'

# Rafraîchir un peu avant l'échéance : un jeton qui expire pendant l'appel
# rend un 401 au milieu d'un flux, là où une marge coûte une requête.
MARGE = 60.0
DELAI_LOGIN = 300.0

ABSENT = 'aucune session — /connect pour se connecter dans le navigateur'

# L'état du flux en cours. Un dictionnaire de module : le rappel du navigateur
# arrive sur un autre fil que celui qui a ouvert la session.
_flux = {}


class ErreurOAuth(Exception):
    """Échec attendu, à dire en clair plutôt qu'en trace."""


# --- état ------------------------------------------------------------------

def pret():
    """Une session utilisable ici et maintenant ?"""
    jetons = secrets.jetons()
    if not jetons.get('access_token'):
        return False
    # Expiré mais rafraîchissable : utilisable quand même. Dire non ici
    # renverrait l'architecte au navigateur pour rien.
    return not _doit_rafraichir(jetons) or bool(jetons.get('refresh_token'))


def deconnecter():
    _fermer_serveur()
    return secrets.oublier_jetons()


# --- la danse --------------------------------------------------------------

def connecter():
    """Ouvre le navigateur. **Ne bloque pas.**

    La socket est liée ICI, pas dans ``attendre()`` : entre les deux appels le
    navigateur peut déjà frapper le rappel, et on perdrait le code.
    """
    _fermer_serveur()
    verifier = _b64(os.urandom(64))
    etat = _b64(os.urandom(24))
    try:
        serveur = HTTPServer(('127.0.0.1', PORT), _Rappel)
    except Exception as e:
        _log.exception('port %s indisponible', PORT)
        raise ErreurOAuth(
            'port {0} occupé — une connexion « codex login » ou opencode est '
            'peut-être en cours. Fermez-la, puis réessayez ({1}).'.format(PORT, e))
    serveur.timeout = 1.0
    _Rappel.recu = None
    _flux.update({'verifier': verifier, 'etat': etat, 'serveur': serveur})
    url = url_autorisation(verifier, etat)
    _ouvrir(url)
    _log.info('flux OAuth ouvert sur le port %s', PORT)
    return url


def attendre(timeout=None):
    """Bloque jusqu'au retour du navigateur. ``True`` si la session est ouverte.

    À appeler HORS du fil d'interface.
    """
    timeout = DELAI_LOGIN if timeout is None else timeout
    serveur = _flux.get('serveur')
    if serveur is None:
        return False
    limite = time.time() + timeout
    try:
        # Une boucle plutôt qu'un seul `handle_request()` : le navigateur
        # demande aussi /favicon.ico, qui consommerait la seule requête servie.
        while _Rappel.recu is None and time.time() < limite:
            serveur.handle_request()
    finally:
        _fermer_serveur()
    recu = _Rappel.recu
    _Rappel.recu = None
    if not recu:
        _log.warning('aucun retour du navigateur après %s s', timeout)
        return False
    try:
        _echanger(recu)
    except ErreurOAuth as e:
        _log.error('échange du code refusé : %s', e)
        return False
    _log.info('session ouverte')
    return True


def url_autorisation(verifier, etat):
    parametres = [
        ('response_type', 'code'),
        ('client_id', CLIENT),
        ('redirect_uri', REDIRECTION),
        ('scope', PORTEE),
        ('code_challenge', defi(verifier)),
        ('code_challenge_method', 'S256'),
        ('id_token_add_organizations', 'true'),
        ('codex_cli_simplified_flow', 'true'),
        ('originator', ORIGINATEUR),
        ('state', etat),
    ]
    return '{0}?{1}'.format(URL_AUTORISATION, urlencode(parametres))


def defi(verifier):
    """Défi PKCE S256 : SHA-256 du verifier, base64url, sans remplissage."""
    return _b64(hashlib.sha256(verifier.encode('ascii')).digest())


def _echanger(recu):
    """Valide le retour du navigateur et échange le code contre des jetons."""
    erreur = _premier(recu, 'error')
    if erreur:
        raise ErreurOAuth('refusé par OpenAI — {0}'.format(erreur))
    code = _premier(recu, 'code')
    if not code:
        raise ErreurOAuth('retour du navigateur sans code')
    # Sans cette comparaison, n'importe quelle page ouverte pendant le flux
    # pourrait pousser son propre code sur notre boucle locale.
    if _premier(recu, 'state') != _flux.get('etat'):
        raise ErreurOAuth('état ne correspondant pas — connexion abandonnée')
    secrets.poser_jetons(_conserver(_demander_jetons({
        'grant_type': 'authorization_code',
        'client_id': CLIENT,
        'code': code,
        'redirect_uri': REDIRECTION,
        'code_verifier': _flux.get('verifier'),
    })))


def _rafraichir():
    jetons = secrets.jetons()
    refresh = jetons.get('refresh_token')
    if not refresh:
        raise ErreurOAuth(ABSENT)
    try:
        neufs = _demander_jetons({
            'grant_type': 'refresh_token',
            'client_id': CLIENT,
            'refresh_token': refresh,
            'scope': PORTEE,
        })
    except ErreurOAuth:
        # Un refresh refusé ne se répare pas tout seul : on efface, et on le
        # dit. opencode laisse le disque périmé et l'utilisateur deviner.
        secrets.oublier_jetons()
        raise ErreurOAuth('session expirée — /connect pour rouvrir le navigateur')
    # Le backend ne renvoie pas toujours un refresh_token neuf : garder
    # l'ancien, sinon la session meurt au rafraîchissement suivant.
    garde = _conserver(neufs)
    if not garde['refresh_token']:
        garde['refresh_token'] = refresh
    if not garde['id_token']:
        garde['id_token'] = jetons.get('id_token', '')
        garde['compte'] = jetons.get('compte', '')
    secrets.poser_jetons(garde)
    return garde


def _demander_jetons(corps):
    requete = Request(URL_JETONS,
                      data=urlencode(corps).encode('utf-8'))
    requete.add_header('Content-Type', 'application/x-www-form-urlencoded')
    try:
        brut = urlopen(requete, timeout=30).read().decode('utf-8')
    except HTTPError as e:
        raise ErreurOAuth(_detail(e))
    except URLError as e:
        raise ErreurOAuth('auth.openai.com injoignable — {0}'.format(
            getattr(e, 'reason', e)))
    try:
        return json.loads(brut)
    except ValueError:
        raise ErreurOAuth('réponse de jetons illisible')


def _conserver(reponse):
    """Ne garde que ce qui sert, et fige l'échéance en horloge absolue."""
    duree = reponse.get('expires_in') or 0
    return {
        'access_token': reponse.get('access_token', ''),
        'refresh_token': reponse.get('refresh_token', ''),
        'id_token': reponse.get('id_token', ''),
        'compte': compte(reponse.get('id_token', '')),
        'expire': time.time() + float(duree) if duree else 0.0,
    }


def _doit_rafraichir(jetons):
    expire = jetons.get('expire') or 0
    return bool(expire) and time.time() >= expire - MARGE


def compte(id_token):
    """``chatgpt_account_id`` porté par le ``id_token``, '' s'il n'y est pas.

    Aucune vérification de signature : le jeton sort d'un TLS vers l'émetteur,
    et on ne s'en sert que pour remplir un en-tête.
    """
    try:
        charge_utile = id_token.split('.')[1]
        # base64url sans remplissage : le rajouter, sinon b64decode lève.
        charge_utile += '=' * (-len(charge_utile) % 4)
        brut = base64.urlsafe_b64decode(charge_utile.encode('ascii'))
        claims = json.loads(brut.decode('utf-8'))
        return claims['https://api.openai.com/auth']['chatgpt_account_id']
    except Exception:
        return ''


# --- le tuyau --------------------------------------------------------------

def diffuser(corps, sur_ligne, timeout=180):
    """Poste un corps déjà formé et rend les lignes du flux UNE A UNE.

    C'est tout ce que ce module sait du modèle : il ne lit pas ce qu'il
    transporte. ``sur_ligne(texte)`` reçoit chaque ligne ``data:`` brute, au
    fil de l'eau — pas d'un bloc à la fin, sinon l'architecte attend soixante
    secondes devant une bulle vide.
    """
    jetons = secrets.jetons()
    if not jetons.get('access_token'):
        raise ErreurOAuth(ABSENT)
    if _doit_rafraichir(jetons):
        jetons = _rafraichir()
    try:
        return _lire_flux(corps, jetons, sur_ligne, timeout)
    except HTTPError as e:
        if e.code != 401 or not jetons.get('refresh_token'):
            raise ErreurOAuth(_detail(e))
        # Un 401 malgré la marge : l'horloge a dérivé, ou le jeton a été
        # révoqué ailleurs. Un seul réessai, jamais deux.
        _log.info('401 — rafraîchissement puis réessai')
        return _lire_flux(corps, _rafraichir(), sur_ligne, timeout)


def _lire_flux(corps, jetons, sur_ligne, timeout):
    requete = Request(URL_REPONSES, data=corps.encode('utf-8'))
    requete.add_header('Content-Type', 'application/json; charset=utf-8')
    requete.add_header('Authorization', 'Bearer ' + jetons['access_token'])
    requete.add_header('Accept', 'text/event-stream')
    requete.add_header('originator', ORIGINATEUR)
    if jetons.get('compte'):
        requete.add_header('ChatGPT-Account-Id', jetons['compte'])

    reponse = urlopen(requete, timeout=timeout)
    lignes = 0
    try:
        # Itérer sur la réponse plutôt que `.read()` : c'est toute la
        # différence entre un flux et un bloc. L'ancien code faisait `.read()`
        # et jetait le streaming que le serveur envoyait déjà.
        for brute in reponse:
            ligne = brute.decode('utf-8', 'replace').strip()
            if not ligne.startswith('data:'):
                continue
            utile = ligne[5:].strip()
            if not utile or utile == '[DONE]':
                continue
            lignes += 1
            sur_ligne(utile)
    finally:
        try:
            reponse.close()
        except Exception:
            pass
    _log.debug('flux terminé, %d évènements', lignes)
    return lignes


def _detail(erreur):
    """``HTTPError`` → « HTTP 400 — <message de l'API> »."""
    code = getattr(erreur, 'code', '?')
    try:
        corps = json.loads(erreur.read().decode('utf-8'))
    except Exception:
        return 'HTTP {0} — {1}'.format(code, getattr(erreur, 'reason', '') or '')
    if not isinstance(corps, dict):
        corps = {}
    contenu = corps.get('error')
    texte = lambda v: isinstance(v, type(''))        # noqa: E731
    message = (corps.get('error_description')
               or (contenu if texte(contenu) else (contenu or {}).get('message'))
               or (corps.get('detail') if texte(corps.get('detail')) else ''))
    return 'HTTP {0} — {1}'.format(code, message or 'sans détail')


# --- la boucle locale ------------------------------------------------------

class _Rappel(BaseHTTPRequestHandler):
    """Sert la page de retour et retient ce que le navigateur a rapporté."""

    recu = None

    def do_GET(self):                                        # noqa: N802
        morceaux = urlparse(self.path)
        if morceaux.path != CHEMIN_RAPPEL:
            self.send_response(404)
            self.end_headers()
            return
        _Rappel.recu = parse_qs(morceaux.query)
        reussi = 'code' in _Rappel.recu and 'error' not in _Rappel.recu
        corps = _page(reussi).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def log_message(self, *_args):
        pass                                 # le journal de 418 suffit


def _page(reussi=True):
    titre = 'Connexion réussie' if reussi else 'Connexion refusée'
    detail = ('Vous pouvez fermer cet onglet et revenir dans Revit.' if reussi
              else 'Rien n\'a été enregistré. Réessayez depuis le volet.')
    return ('<!doctype html><meta charset="utf-8">'
            '<title>418 — {0}</title>'
            '<style>body{{font:15px/1.6 "Segoe UI",system-ui,sans-serif;'
            'display:grid;place-items:center;height:100vh;margin:0;'
            'background:#f3f3f3;color:#1a1a1a}}'
            '@media(prefers-color-scheme:dark){{body{{background:#23272f;'
            'color:#f3f3f3}}}}div{{text-align:center}}'
            'h1{{font-size:18px;margin:0 0 8px}}p{{color:#6b6b6b;margin:0}}'
            '</style><div><h1>{0}</h1><p>{1}</p></div>').format(titre, detail)


def _fermer_serveur():
    serveur = _flux.pop('serveur', None)
    if serveur is None:
        return
    try:
        serveur.server_close()
    except Exception:
        _log.exception('fermeture du serveur de rappel')


def _ouvrir(url):
    """Ouvre le navigateur par défaut. Ne lève jamais."""
    try:
        import webbrowser
        webbrowser.open(url)
    except Exception:
        _log.exception('ouverture du navigateur')


def _b64(octets):
    """base64url sans remplissage, comme l'exige PKCE."""
    return base64.urlsafe_b64encode(octets).decode('ascii').rstrip('=')


def _premier(recu, cle):
    valeurs = (recu or {}).get(cle) or []
    return valeurs[0] if valeurs else ''
