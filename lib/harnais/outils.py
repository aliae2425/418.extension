# -*- coding: utf-8 -*-
"""Le pont entre le chat et les outils Revit de ``lib/rvt``.

Le panneau tourne DANS Revit : les routes pyRevit lui suffisent. Pas de
client MCP ici — le protocole existe pour les clients qui sont *dehors*, et
le traverser depuis l'intérieur ajouterait un process entre nous et un GET
local.

**Le catalogue n'est plus écrit ici.** Il est servi par ``/418/outils/``,
dérivé du registre qui déclare chaque outil une seule fois. Les deux listes
qu'on tenait en parallèle ont divergé deux fois : une route renommée sans le
catalogue (le chat a perdu TOUS ses outils sur un 404 lu comme « maquette
injoignable »), un paramètre deviné de travers. Ça ne peut plus arriver.

Logique pure (aucun import Revit ni WPF) pour rester testable hors Revit.
"""
from __future__ import unicode_literals
import json
import threading

try:                                   # CPython 3
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
except ImportError:                    # IronPython 2.7
    from urllib2 import Request, urlopen, HTTPError, URLError

try:
    from core.journal import journal
    from core import routes418
except Exception:
    from lib.core.journal import journal
    from lib.core import routes418

_log = journal('outils')

# Un modèle qui boucle brûle l'abonnement en silence : le plafond n'est pas
# une précaution, c'est le garde-fou.
TOURS_MAX = 5

# Une vue chargée ou un catalogue de familles dépasse largement ce que la
# requête suivante peut porter. On tronque avant de renvoyer, jamais après.
LIMITE_SORTIE = 6000

DELAI = 30

# Le serveur de routes pyRevit partage UN handler de requête et UN
# ExternalEvent entre toutes ses requêtes (server.py:36-41, singletons de
# module réécrits à chaque appel). Deux requêtes simultanées se marchent
# dessus dans le contexte d'API Revit — au mieux la réponse part au mauvais
# appelant, au pire Revit tombe.
# ponytail: verrou global. Il ne protège que de NOUS — un client externe qui
# tape le même serveur en parallèle rouvre la course.
_VERROU = threading.Lock()

# Catalogue servi par /418/outils/, lu une fois par session : il ne change
# pas sans un Reload pyRevit, qui rejoue le processus de toute façon.
_catalogue = []


def outils():
    """Le catalogue, tel que le serveur le déclare. ``[]`` s'il est muet."""
    if _catalogue:
        return list(_catalogue)
    try:
        charge = json.loads(_appeler('/418/outils/', 'GET', None, timeout=8))
    except Exception as e:
        _log.warning('catalogue indisponible : %s', e)
        return []
    _catalogue.extend(charge.get('outils') or [])
    _log.info('catalogue : %d outils', len(_catalogue))
    return list(_catalogue)


def oublier_catalogue():
    """Pour les tests seulement : un cache de module se garde d'un test à l'autre."""
    del _catalogue[:]


def executer(nom, arguments=None):
    """Lance un outil et renvoie sa sortie en texte, prête à être renvoyée.

    Ne lève jamais : un échec part au modèle sous forme de JSON
    ``{"erreur":…}`` pour qu'il puisse le dire ou tenter autre chose, plutôt
    que de faire échouer tout le tour.
    """
    fiche = _par_nom().get(nom)
    if fiche is None:
        return _echoue(nom, 'outil inconnu')
    corps = arguments if isinstance(arguments, dict) else {}
    if fiche.get('irreversible'):
        _log.warning('IRRÉVERSIBLE %s %s', nom, corps)
    try:
        brut = _appeler('/418/outil/{0}'.format(nom), 'POST', corps)
    except HTTPError as e:
        # detail_http lit le CORPS : sans lui on ne garderait que « HTTP 500 »
        # et le vrai message mourrait dans le journal de Revit.
        return _echoue(nom, detail_http(e))
    except URLError as e:
        return _echoue(nom, 'maquette injoignable — {0}'.format(
            getattr(e, 'reason', e)))
    except Exception as e:
        _log.exception('%s a échoué', nom)
        return _echoue(nom, '{0}'.format(e))
    souci = _erreur_dans_le_corps(brut)
    if souci:
        _log.error('%s : %s', nom, souci)
    _log.debug('%s -> %s octets', nom, len(brut))
    return _tronquer(brut, bool(fiche['parametres'].get('properties')))


def detail_http(erreur):
    """``HTTPError`` → « HTTP 400 — <message de l'API> ».

    Les fournisseurs logent leur message à trois endroits différents selon
    l'endpoint (``error.message``, ``error_description``, ``detail``) ; sans
    ce tri, l'appelant reçoit le corps JSON brut ou juste un code nu.

    Vivait dans ``chat_syntaxe``, supprimé avec le reste du harnais WPF. Posé
    ici, chez son seul consommateur, plutôt que gardé dans un module à part.
    """
    code = getattr(erreur, 'code', '?')
    try:
        corps = json.loads(erreur.read().decode('utf-8'))
    except Exception:
        return 'HTTP {0} — {1}'.format(code, getattr(erreur, 'reason', '') or '')
    if not isinstance(corps, dict):
        corps = {}
    contenu = corps.get('error')
    texte = lambda v: isinstance(v, type(''))       # noqa: E731
    message = (corps.get('error_description') or
               (contenu if texte(contenu) else (contenu or {}).get('message')) or
               (corps.get('detail') if texte(corps.get('detail')) else ''))
    return 'HTTP {0} — {1}'.format(code, message or 'sans détail')


def _par_nom():
    return dict((o['nom'], o) for o in outils())


def _appeler(route, methode, corps, timeout=DELAI):
    racine = routes418.base()
    if not racine:
        raise ValueError(routes418.ABSENT)
    donnees = None
    if methode == 'POST':
        # ensure_ascii=False : sous IronPython, laisser json échapper les
        # accents lui-même lève. On encode explicitement derrière.
        donnees = json.dumps(corps or {}, ensure_ascii=False).encode('utf-8')
    requete = Request(racine + route, data=donnees)
    if donnees is not None:
        requete.add_header('Content-Type', 'application/json; charset=utf-8')
    # Le laissez-passer des outils irréversibles. On tourne DANS le process
    # Revit, donc on peut le lire ; une page web extérieure ne le peut pas.
    # Hors Revit (tests), `jeton()` est introuvable et l'en-tête n'est pas
    # posé — ce qui est le bon comportement, pas un repli.
    try:
        from rvt import jeton
    except Exception:
        try:
            from lib.rvt import jeton
        except Exception:
            jeton = None
    if jeton is not None:
        requete.add_header('X-418-Jeton', jeton())
    # Une seule requête 418 en vol à la fois (cf. _VERROU).
    with _VERROU:
        return urlopen(requete,
                       timeout=timeout).read().decode('utf-8', 'replace')


def _erreur_dans_le_corps(brut):
    """Message d'échec caché dans une réponse HTTP 200. '' s'il n'y en a pas."""
    try:
        charge = json.loads(brut)
    except ValueError:
        return ''
    if not isinstance(charge, dict):
        return ''
    if charge.get('status') == 'error' or charge.get('success') is False \
            or charge.get('erreur') or charge.get('error'):
        return '{0}'.format(charge.get('erreur') or charge.get('error') or
                            charge.get('message') or 'échec sans message')
    return ''


def _tronquer(texte, filtrable=True):
    """Coupe, et dit au modèle quoi faire — ce qui dépend de l'outil."""
    if len(texte) <= LIMITE_SORTIE:
        return texte
    conseil = ('restreindre les arguments de l\'outil pour en voir moins '
               'à la fois' if filtrable else
               'cet outil ne prend aucun filtre : la liste restera '
               'incomplète, inutile de le rappeler à l\'identique')
    return '{0}\n…tronqué à {1} caractères — {2}.'.format(
        texte[:LIMITE_SORTIE], LIMITE_SORTIE, conseil)


def _echoue(nom, message):
    """Journalise, et rend l'erreur au modèle.

    Elle lui revient en JSON plutôt qu'en exception : il peut la dire ou
    corriger sa demande, là qu'une exception ferait échouer le tour entier.
    L'interface, elle, la lit dans la part `outil` passée en échec.
    """
    _log.error('%s : %s', nom, message)
    return json.dumps({'erreur': message}, ensure_ascii=False)
