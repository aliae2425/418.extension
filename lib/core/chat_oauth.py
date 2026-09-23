# -*- coding: utf-8 -*-
"""Client de chat OpenAI par abonnement ChatGPT, sans aucun CLI à installer.

418 déroule lui-même le flux OAuth PKCE d'OpenAI — navigateur, boucle locale
sur le port 1455, échange du code — puis appelle le backend Responses de
ChatGPT. C'est ce que fait ``chat_cli`` en déléguant à ``codex`` ; ici il n'y a
rien à installer, mais **418 garde le jeton**, contrairement à ``chat_cli``.

Zone grise assumée : on emprunte le ``client_id`` public du CLI Codex et un
``originator`` whitelisté côté serveur. OpenAI peut fermer ça sans préavis —
le repli est immédiat, ``chat_cli`` et ``chat_openai`` restent branchés.

Logique pure (aucun import Revit ni WPF) pour rester testable hors Revit.
"""
from __future__ import unicode_literals
import base64
import hashlib
import io
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
    from core.chat_syntaxe import SYSTEME, OUTILLE, detail_http
except Exception:
    from lib.core.journal import journal
    from lib.core.chat_syntaxe import SYSTEME, OUTILLE, detail_http

try:
    from core import revit_outils
except Exception:
    try:
        from lib.core import revit_outils
    except Exception:
        revit_outils = None            # sans lui, le chat reste sans outils

_log = journal('oauth')

CLIENT = 'app_EMoamEEZ73f0CkXaXp7hrann'
URL_AUTORISATION = 'https://auth.openai.com/oauth/authorize'
URL_JETONS = 'https://auth.openai.com/oauth/token'
URL_REPONSES = 'https://chatgpt.com/backend-api/codex/responses'

# Port imposé : il est enregistré tel quel dans la redirection du client OAuth,
# on ne peut pas en prendre un autre.
PORT = 1455
CHEMIN_RAPPEL = '/auth/callback'
REDIRECTION = 'http://localhost:{0}{1}'.format(PORT, CHEMIN_RAPPEL)
PORTEE = 'openid profile email offline_access'

# Le backend ne sert que des « originators » de première partie ; une valeur
# inconnue se prend un 403, ou un catalogue de modèles amputé.
ORIGINATEUR = 'codex_cli_rs'

# Un seul nom, pas une liste (cf. CLAUDE.md) : « /model <nom> » le remplace.
# Le backend n'accepte qu'une poignée de noms pour un compte ChatGPT — les
# suffixes « -codex » et « -pro » se prennent un 400. S'il vieillit, INDICE
# ci-dessous transforme l'échec en mode d'emploi plutôt qu'en énigme.
MODELE_DEFAUT = 'gpt-5.6-terra'

# Cités seulement quand le modèle courant vient d'être refusé : cette liste ne
# peut pas rotter en silence, elle ne s'affiche que là où ça a déjà cassé.
# ponytail: noms de modèles en dur. Les retirer le jour où le backend expose
# un catalogue listable — modeles() les servirait alors à /model.
INDICE = ('\n→ /model <nom> pour en choisir un autre — p. ex. gpt-5.6-terra '
          '(équilibré), gpt-5.6-luna (rapide), gpt-5.6-sol (le plus fort).')

# Marge avant expiration : rafraîchir pile à l'échéance, c'est se prendre le
# 401 pendant que la requête voyage.
MARGE = 60.0
DELAI_LOGIN = 300.0

ABSENT = 'aucune session — /connect pour se connecter dans le navigateur'

# La page vit dans GUI/resources/oauth.html, éditable sans toucher au Python.
# Pas sous vendor/ : c'est le subtree du serveur MCP, qu'on n'édite jamais.
GABARIT = 'oauth.html'

# Repli minimal, uniquement si le fichier manque. Le flux OAuth a réussi à ce
# stade : le navigateur doit le dire, même sans mise en forme. Laisser
# l'ouverture du fichier lever ferait échouer une connexion pourtant valide.
_SECOURS = ('<!doctype html><meta charset="utf-8"><title>418 — __TITRE__</title>'
            '<body style="font:16px sans-serif;padding:3em;text-align:center">'
            '<h1>__TITRE__</h1><p>__SOUS__</p>')


def _ressource(nom):
    """Chemin d'une ressource du socle. Jamais de chemin en dur (CLAUDE.md)."""
    try:
        from core.AppPaths import AppPaths
    except Exception:
        from lib.core.AppPaths import AppPaths
    return AppPaths().resource_path(nom)


def gabarit():
    """Le gabarit HTML, relu à chaque rendu.

    Pas de cache : c'est ce qui rend la page modifiable à chaud — éditer le
    fichier puis rafraîchir l'onglet suffit, sans Reload pyRevit. Deux kilos
    lus une fois par connexion, ça ne se mesure pas.
    """
    try:
        with io.open(_ressource(GABARIT), encoding='utf-8') as f:
            return f.read()
    except Exception:
        _log.warning('%s illisible — page de secours servie', GABARIT)
        return _SECOURS


def logo():
    """Le logo en ``url(data:…)``, '' s'il est illisible.

    Embarqué plutôt que servi : la boucle locale ferme sa socket dès le code
    reçu, donc un ``<img src="/logo.png">`` partirait dans le vide — la page
    s'affiche après que le serveur a rendu la main.
    """
    try:
        with open(_ressource('logo.png'), 'rb') as f:
            brut = base64.b64encode(f.read()).decode('ascii')
        return 'url("data:image/png;base64,{0}")'.format(brut)
    except Exception:
        _log.warning('logo illisible — page servie sans théière')
        return ''


def page(reussi=True):
    """Page rendue au navigateur. Elle dit la vérité : un refus n'affiche pas
    « réussi » pendant que le panneau, lui, annonce l'échec."""
    titre = 'Connexion réussie' if reussi else 'Connexion interrompue'
    sous = ('Vous pouvez refermer cet onglet et retourner dans Revit.'
            if reussi else
            'Rien n\'a été enregistré. Relancez /connect dans Revit.')
    return (gabarit().replace('__LOGO__', logo())
                     .replace('__TITRE__', titre)
                     .replace('__SOUS__', sous)
                     .replace('__ETAT__', '' if reussi else 'rate'))


class ErreurOAuth(Exception):
    """Échec : pas de session, flux interrompu, ou backend en erreur."""


# Jetons en mémoire, image du fichier. `pret()` est lu par une propriété liée
# au XAML, donc plusieurs fois par interaction : jamais de disque après le
# premier chargement.
_jetons = {}
_charge = []

# Flux de connexion en cours : verifier PKCE, state, et la socket déjà liée.
_flux = {}


# --- stockage ------------------------------------------------------------

def dossier():
    """Hors du dépôt : un dossier d'extension se zippe et se partage.

    ``data/`` est gitignoré, mais CLAUDE.md interdit d'y poser un secret et il
    a raison — le jeton suivrait la moindre copie de l'extension.
    """
    base = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
    return os.path.join(base, '418.extension')


def fichier():
    return os.path.join(dossier(), 'auth.json')


def _lire():
    if _charge:
        return _jetons
    _charge.append(True)
    try:
        with open(fichier(), 'rb') as f:
            _jetons.update(json.loads(f.read().decode('utf-8')))
    except Exception:
        pass                           # pas encore connecté : cas normal
    return _jetons


def _ecrire(jetons):
    _jetons.clear()
    _jetons.update(jetons)
    del _charge[:]
    _charge.append(True)
    chemin = fichier()
    try:
        if not os.path.isdir(dossier()):
            os.makedirs(dossier())
        # ensure_ascii=False : sous IronPython, laisser json échapper lui-même
        # les accents lève. On encode explicitement derrière.
        brut = json.dumps(jetons, ensure_ascii=False).encode('utf-8')
        with open(chemin, 'wb') as f:
            f.write(brut)
        # ponytail: jeton en clair. DPAPI (CryptProtectData) si le chiffrement
        # au repos devient une exigence — le fichier est déjà isolé du dépôt.
        try:
            os.chmod(chemin, 0o600)
        except Exception:
            pass                       # NTFS n'en fait rien, ce n'est pas grave
    except Exception as e:
        _log.exception('écriture du jeton impossible')
        raise ErreurOAuth('impossible d\'enregistrer la session — {0}'.format(e))


def oublier():
    _jetons.clear()
    del _charge[:]
    try:
        os.remove(fichier())
    except OSError:
        pass


# --- contrat -------------------------------------------------------------

def pret():
    jetons = _lire()
    if not jetons.get('access_token'):
        return False
    # Expiré mais rafraîchissable : toujours utilisable, `repondre()` s'en
    # charge. Dire non ici renverrait l'utilisateur au navigateur pour rien.
    return not _doit_rafraichir(jetons) or bool(jetons.get('refresh_token'))


def raison():
    return ABSENT


def modeles():
    """Non listable : le backend Codex n'expose aucun catalogue. ``/model`` sert."""
    return ()


def connecter():
    """Ouvre le navigateur. **Ne bloque pas** — on est sur le fil d'interface.

    La socket est liée ici, pas dans ``attendre_connexion()`` : entre les deux
    appels le navigateur peut déjà frapper le rappel, et on perdrait le code.
    """
    _fermer_serveur()
    verifier = _b64(os.urandom(64))
    etat = _b64(os.urandom(24))
    try:
        serveur = HTTPServer(('127.0.0.1', PORT), _Rappel)
    except Exception as e:
        _log.exception('port %s indisponible', PORT)
        raise ErreurOAuth(
            'port {0} occupé — fermer un « codex login » en cours, puis '
            'réessayer ({1})'.format(PORT, e))
    serveur.timeout = 1.0
    _Rappel.recu = None
    _flux.update({'verifier': verifier, 'etat': etat, 'serveur': serveur})
    url = url_autorisation(verifier, etat)
    _ouvrir(url)
    _log.info('flux OAuth ouvert sur le port %s', PORT)
    return 'Connexion ouverte dans le navigateur…'


def attendre_connexion(timeout=None, **_kwargs):
    """Bloque jusqu'au retour du navigateur, puis dit si la session est ouverte.

    À appeler hors du fil d'interface : c'est le VM qui s'en charge.
    """
    timeout = DELAI_LOGIN if timeout is None else timeout
    serveur = _flux.get('serveur')
    if serveur is None:
        return False
    limite = time.time() + timeout
    try:
        # Boucle plutôt qu'un seul handle_request() : le navigateur demande
        # aussi /favicon.ico, qui consommerait la seule requête servie.
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


def deconnecter():
    _fermer_serveur()
    oublier()
    _log.info('session effacée')
    return 'Session fermée. /connect pour rouvrir le navigateur.'


def repondre(messages, modele=None, timeout=180, outils=None, **_kwargs):
    """Renvoie le texte de la réponse, ou lève ``ErreurOAuth``.

    Boucle d'outils : tant que le modèle demande un outil, on l'exécute sur la
    maquette et on lui rend la main. ``outils`` à ``None`` laisse le catalogue
    se décider seul ; une liste vide désactive les outils (ce que font les
    tests, qui n'ont pas de Revit sous la main).
    """
    if not _lire().get('access_token'):
        raise ErreurOAuth(ABSENT)
    catalogue = _catalogue() if outils is None else list(outils)
    entree = items(messages)

    tours = revit_outils.TOURS_MAX if revit_outils is not None else 5
    for _tour in range(tours):
        brut = _echange(corps(entree, modele, catalogue), timeout)
        demandes = appels(brut)
        if not demandes:
            return _texte_final(brut)
        for appel in demandes:
            # L'item d'origine PUIS son résultat : le backend ne garde rien
            # d'un appel à l'autre (store=false), il faut lui rendre les deux.
            entree.append(appel)
            entree.append(_resultat(appel))

    # Plafond atteint : on redemande sans outils plutôt que de lever. Le
    # modèle a déjà tout lu, il lui reste à le dire — une erreur ici laisserait
    # l'architecte avec une bulle vide après dix secondes d'attente.
    _log.warning('plafond de %s tours d\'outils atteint', tours)
    return _texte_final(_echange(corps(entree, modele, None), timeout))


def _catalogue():
    """Les outils disponibles, ou rien si la maquette n'est pas joignable.

    Ne rien envoyer vaut mieux qu'annoncer des outils inexécutables : un
    modèle à qui l'on promet des yeux répond « je regarde » et ne regarde rien.
    """
    if revit_outils is None:
        return []
    utilisable, _raison = revit_outils.disponible()
    return revit_outils.outils() if utilisable else []


def _resultat(appel):
    """Item de retour d'un appel d'outil, prêt à repartir dans ``input``."""
    nom = appel.get('name') or ''
    try:
        arguments = json.loads(appel.get('arguments') or '{}')
    except ValueError:
        arguments = {}
    if revit_outils is None:
        sortie = json.dumps({'erreur': 'outils indisponibles'},
                            ensure_ascii=False)
    else:
        sortie = revit_outils.executer(nom, arguments)
    _log.info('outil %s(%s) -> %s octets', nom, arguments, len(sortie))
    return {'type': 'function_call_output',
            'call_id': appel.get('call_id'),
            'output': sortie}


def _echange(charge_utile, timeout):
    """Un aller-retour avec le backend, jeton rafraîchi et réessayé si besoin."""
    jetons = _lire()
    if _doit_rafraichir(jetons):
        jetons = _rafraichir()
    brut_corps = json.dumps(charge_utile, ensure_ascii=False)
    try:
        return _poster(brut_corps, jetons, timeout)
    except HTTPError as e:
        if e.code != 401 or not jetons.get('refresh_token'):
            raise ErreurOAuth(indice(detail_http(e)))
        # Jeton refusé alors qu'on le croyait valide : un seul réessai.
        _log.info('401 — rafraîchissement puis réessai')
        try:
            return _poster(brut_corps, _rafraichir(), timeout)
        except HTTPError as e2:
            raise ErreurOAuth(indice(detail_http(e2)))
        except URLError as e2:
            raise ErreurOAuth('réseau injoignable — {0}'.format(
                getattr(e2, 'reason', e2)))
    except URLError as e:
        _log.error('réseau injoignable — %s', getattr(e, 'reason', e))
        raise ErreurOAuth('réseau injoignable — {0}'.format(
            getattr(e, 'reason', e)))


def _texte_final(brut):
    reponse = extraire(brut)
    if reponse:
        return reponse
    # Un 200 sans texte, c'est soit un refus glissé dans le flux, soit une
    # forme d'évènement qu'on ne sait pas lire : les deux se disent, et ne se
    # disent pas pareil. Accuser le modèle à l'aveugle envoie sur une fausse
    # piste — c'est exactement ce qui vient de se passer.
    souci = erreur_du_flux(brut)
    if souci:
        raise ErreurOAuth(indice(souci))
    raise ErreurOAuth('réponse illisible — /journal donne les évènements reçus')


# --- flux OAuth ----------------------------------------------------------

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
    _ecrire(_conserver(_demander_jetons({
        'grant_type': 'authorization_code',
        'client_id': CLIENT,
        'code': code,
        'redirect_uri': REDIRECTION,
        'code_verifier': _flux.get('verifier'),
    })))


def _rafraichir():
    jetons = _lire()
    refresh = jetons.get('refresh_token')
    if not refresh:
        raise ErreurOAuth(ABSENT)
    try:
        neufs = _demander_jetons({
            'grant_type': 'refresh_token',
            'client_id': CLIENT,
            'refresh_token': refresh,
        })
    except ErreurOAuth:
        # Un refresh révoqué ne repassera jamais : effacer, sinon `pret()`
        # reste vrai et chaque message rejoue le même échec.
        oublier()
        raise ErreurOAuth('session expirée — /connect pour vous reconnecter')
    # OpenAI ne renvoie pas toujours un nouveau refresh_token ni un id_token :
    # garder les anciens plutôt que de les perdre.
    garde = _conserver(neufs)
    for cle in ('refresh_token', 'id_token', 'compte'):
        if not garde.get(cle) and jetons.get(cle):
            garde[cle] = jetons[cle]
    _ecrire(garde)
    return garde


def _demander_jetons(corps):
    donnees = json.dumps(corps, ensure_ascii=False).encode('utf-8')
    requete = Request(URL_JETONS, data=donnees)
    requete.add_header('Content-Type', 'application/json')
    try:
        brut = urlopen(requete, timeout=30).read().decode('utf-8')
    except HTTPError as e:
        raise ErreurOAuth(detail_http(e))
    except URLError as e:
        raise ErreurOAuth('réseau injoignable — {0}'.format(
            getattr(e, 'reason', e)))
    try:
        return json.loads(brut)
    except ValueError:
        raise ErreurOAuth('réponse d\'authentification illisible')


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


# --- appel au modèle -----------------------------------------------------

def items(messages):
    """Couples (role, texte) → items d'entrée du backend."""
    # L'assistant parle en `output_text`, l'utilisateur en `input_text` :
    # inverser les deux fait répondre un 400 au corps entier.
    return [{'role': role,
             'content': [{'type': ('output_text' if role == 'assistant'
                                   else 'input_text'),
                          'text': texte}]}
            for role, texte in messages]


def charge(messages, modele=None, outils=None):
    """Corps Responses. ``messages`` : liste de couples (role, texte)."""
    return corps(items(messages), modele, outils)


def corps(entree, modele=None, outils=None):
    """Corps Responses à partir d'items déjà construits (boucle d'outils)."""
    charge_utile = {
        'model': modele or MODELE_DEFAUT,
        'instructions': SYSTEME,
        'input': entree,
        # store=false est exigé par le backend, ce n'est pas une préférence.
        'store': False,
        'stream': True,
    }
    if outils:
        charge_utile['instructions'] = SYSTEME + OUTILLE
        # Forme à plat, vérifiée contre le backend : pas de niveau
        # « function » intermédiaire, contrairement à /v1/chat/completions.
        charge_utile['tools'] = [
            {'type': 'function', 'name': outil['nom'],
             'description': outil['description'], 'strict': False,
             'parameters': outil['parametres']}
            for outil in outils]
        charge_utile['tool_choice'] = 'auto'
    return charge_utile


def appels(brut):
    """Items ``function_call`` terminés du flux, dans l'ordre.

    Même prudence que ``extraire`` : l'instantané final porte les mêmes items
    que les évènements un à un, on ne lit le second que si le premier n'a rien
    donné — les cumuler exécuterait chaque outil deux fois.
    """
    un_a_un, final = [], []
    for evenement in evenements(brut):
        type_ = evenement.get('type') or ''
        if type_ == 'response.output_item.done':
            item = evenement.get('item') or {}
            if item.get('type') == 'function_call':
                un_a_un.append(item)
        elif type_ in ('response.completed', 'response.done'):
            sortie = (evenement.get('response') or {}).get('output') or []
            final = [item for item in sortie
                     if item.get('type') == 'function_call']
    return un_a_un or final


def _poster(corps, jetons, timeout):
    requete = Request(URL_REPONSES, data=corps.encode('utf-8'))
    requete.add_header('Content-Type', 'application/json; charset=utf-8')
    requete.add_header('Authorization', 'Bearer ' + jetons['access_token'])
    requete.add_header('Accept', 'text/event-stream')
    requete.add_header('originator', ORIGINATEUR)
    if jetons.get('compte'):
        requete.add_header('ChatGPT-Account-Id', jetons['compte'])
    brut = urlopen(requete, timeout=timeout).read().decode('utf-8')
    _log.debug('réponse reçue (%s octets)', len(brut))
    return brut


def evenements(brut):
    """Évènements JSON d'un flux SSE, dans l'ordre. Ignore ce qui n'en est pas."""
    lus = []
    for ligne in brut.splitlines():
        if not ligne.startswith('data:'):
            continue
        utile = ligne[5:].strip()
        if not utile or utile == '[DONE]':
            continue
        try:
            lus.append(json.loads(utile))
        except ValueError:
            continue
    return lus


def _texte_item(item):
    """Texte d'un item de sortie. Les items ``reasoning`` n'en portent pas."""
    return ''.join(bloc.get('text') or ''
                   for bloc in (item.get('content') or [])
                   if bloc.get('type') in ('output_text', 'text'))


def extraire(brut):
    """Texte final d'un flux SSE, quelle que soit la forme qu'il prend.

    Trois sources possibles selon le modèle et la version du backend, par
    ordre de fiabilité décroissante — jamais cumulées, elles portent le même
    texte et le concaténer le doublerait :

    1. l'instantané final (``response.completed``) ;
    2. les items terminés un à un (``response.output_item.done``) ;
    3. à défaut, les ``delta`` recollés.

    Ne se fier qu'à (1) laissait la bulle vide sur les modèles qui ne
    l'émettent pas — c'est ce qui est arrivé en vrai avec gpt-5.6.

    ponytail: trois branches parce qu'on ignore encore laquelle le backend
    emprunte. Le « types=[…] » écrit plus bas le dira ; garder alors la seule
    observée et supprimer les deux autres.
    """
    final, items, deltas, types = '', [], [], []
    for evenement in evenements(brut):
        type_ = evenement.get('type') or ''
        types.append(type_)
        if type_ in ('response.completed', 'response.done'):
            reponse = evenement.get('response') or {}
            # Certains backends posent directement le texte agrégé ici.
            final = (reponse.get('output_text') or
                     ''.join(_texte_item(item)
                             for item in (reponse.get('output') or [])))
        elif type_ == 'response.output_item.done':
            items.append(_texte_item(evenement.get('item') or {}))
        elif type_.endswith('.delta') and 'output_text' in type_:
            deltas.append(evenement.get('delta') or '')

    texte = (final or ''.join(items) or ''.join(deltas)).strip()
    if not texte:
        # Sans ça, un flux d'une forme inconnue ne laisse aucune trace de ce
        # qu'il contenait : impossible à corriger sans redemander à l'user.
        _log.warning('aucun texte extrait | types=%s', sorted(set(types)))
    return texte


def erreur_du_flux(brut):
    """Message d'un refus arrivé en 200, à l'intérieur du flux. '' sinon."""
    for evenement in evenements(brut):
        if (evenement.get('type') or '') not in ('error', 'response.failed'):
            continue
        souci = (evenement.get('error') or
                 (evenement.get('response') or {}).get('error') or
                 evenement)
        if isinstance(souci, dict):
            souci = (souci.get('message') or souci.get('reason') or
                     json.dumps(souci, ensure_ascii=False)[:200])
        return '{0}'.format(souci)
    return ''


# --- plomberie -----------------------------------------------------------

class _Rappel(BaseHTTPRequestHandler):
    """Boucle locale d'un seul usage : elle recueille le code, rien d'autre."""

    recu = None

    def do_GET(self):
        demande = urlparse(self.path)
        if demande.path != CHEMIN_RAPPEL:
            self.send_response(404)
            self.end_headers()
            return
        recu = parse_qs(demande.query)
        _Rappel.recu = recu
        # Dire « réussi » sur un refus d'OpenAI laisserait l'architecte avec
        # deux écrans qui se contredisent — le navigateur et le panneau.
        corps = page(bool(recu.get('code')) and not recu.get('error')
                     ).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def log_message(self, *_args):
        pass                           # sinon stderr, que personne ne lit ici


def _fermer_serveur():
    serveur = _flux.pop('serveur', None)
    if serveur is not None:
        try:
            serveur.server_close()
        except Exception:
            pass


def _ouvrir(url):
    try:
        import webbrowser
        if webbrowser.open(url):
            return
    except Exception:
        pass
    # webbrowser est capricieux sous IronPython : passer par le shell Windows.
    try:
        os.startfile(url)              # pylint: disable=no-member
    except Exception as e:
        _log.exception('navigateur impossible à ouvrir')
        raise ErreurOAuth('navigateur impossible à ouvrir — {0}'.format(e))


def _b64(octets):
    return base64.urlsafe_b64encode(octets).decode('ascii').rstrip('=')


def indice(message):
    """Ajoute le mode d'emploi quand c'est le modèle que le backend refuse.

    « The 'X' model is not supported… » tout seul laisse l'architecte sans
    porte de sortie : il ne peut pas deviner qu'une commande existe.
    """
    if 'not supported' in message or 'model' in message.lower():
        return message + INDICE
    return message


def _premier(recu, cle):
    valeurs = recu.get(cle) or ['']
    return valeurs[0]


