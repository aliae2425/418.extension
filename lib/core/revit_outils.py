# -*- coding: utf-8 -*-
"""Les outils que le modèle peut appeler sur la maquette. Lecture seule.

Le panneau tourne DANS Revit : les routes pyRevit lui suffisent, elles sont
déjà servies par notre instance (cf. ``routes418``). Pas de client MCP ici —
le protocole MCP existe pour les clients qui sont dehors, et le traverser
depuis l'intérieur ajouterait un process Python à la place d'un GET local.

Catalogue écrit à la main contre les vraies signatures des gestionnaires de
``vendor/mcp-server-for-revit/revit_mcp/`` : les noms de paramètres ne se
devinent pas (``list_families`` filtre sur ``contains``, pas sur une
catégorie). Toute entrée ajoutée ici doit être relue là-bas.

Aucune route d'écriture : ni ``execute_code``, ni ``place_family``, ni
``color_splash``, ni ``open/close/save_document``, ni ``sync_with_central``.
Le modèle regarde la maquette, il n'y touche pas.

Logique pure (aucun import Revit ni WPF) pour rester testable hors Revit.
"""
from __future__ import unicode_literals
import json

try:                                   # CPython 3
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
except ImportError:                    # IronPython 2.7
    from urllib2 import Request, urlopen, HTTPError, URLError

try:
    from core.journal import journal
    from core.routes418 import base, assurer
except Exception:
    from lib.core.journal import journal
    from lib.core.routes418 import base, assurer

_log = journal('outils')

PREFIXE = '/revit_mcp'

# Un modèle qui boucle brûle l'abonnement en silence : le plafond n'est pas
# une précaution, c'est le garde-fou.
TOURS_MAX = 5

# Une vue chargée ou un catalogue de familles dépasse largement ce que la
# requête suivante peut porter. On tronque avant de renvoyer, jamais après.
LIMITE_SORTIE = 6000

DELAI = 30

_VIDE = {'type': 'object', 'properties': {}, 'additionalProperties': False}

# nom exposé au modèle · route · méthode · description · schéma des arguments
CATALOGUE = (
    ('revit_status', '/status/', 'GET',
     'État du lien avec Revit et titre du document ouvert.', _VIDE),
    ('revit_model_info', '/model_info/', 'GET',
     'Vue d\'ensemble de la maquette : niveaux, nombre de pièces, '
     'avertissements.', _VIDE),
    ('revit_current_view_info', '/current_view_info/', 'GET',
     'Vue active : nom, type, échelle, discipline.', _VIDE),
    ('revit_list_views', '/list_views/', 'GET',
     'Toutes les vues exportables du projet, par type.', _VIDE),
    ('revit_list_levels', '/list_levels/', 'GET',
     'Niveaux du projet avec leur altitude.', _VIDE),
    ('revit_list_family_categories', '/list_family_categories/', 'GET',
     'Catégories de familles chargées et leur nombre de types.', _VIDE),
    ('revit_list_families', '/list_families/', 'POST',
     'Familles et types chargés, filtrables par fragment de nom.',
     {'type': 'object',
      'properties': {
          'contains': {'type': 'string',
                       'description': 'fragment de nom, insensible à la casse'},
          'limit': {'type': 'integer',
                    'description': 'nombre maximum de résultats (défaut 50)'}},
      'additionalProperties': False}),
    ('revit_list_category_parameters', '/list_category_parameters/', 'POST',
     'Paramètres disponibles sur les éléments d\'une catégorie.',
     {'type': 'object',
      'properties': {
          'category_name': {'type': 'string',
                            'description': 'nom de catégorie, p. ex. « Portes »'}},
      'required': ['category_name'],
      'additionalProperties': False}),
    ('revit_current_view_elements', '/current_view_elements/', 'POST',
     'Éléments visibles dans la vue active.',
     {'type': 'object',
      'properties': {
          'limit': {'type': 'integer',
                    'description': 'nombre maximum d\'éléments (défaut 5000)'},
          'include_levels': {'type': 'boolean'},
          'include_location': {'type': 'boolean'}},
      'additionalProperties': False}),
)

_PAR_NOM = dict((entree[0], entree) for entree in CATALOGUE)


def outils():
    """Le catalogue sous forme neutre : chaque client lui donne sa forme."""
    return [{'nom': nom, 'description': description, 'parametres': schema}
            for nom, _route, _methode, description, schema in CATALOGUE]


def disponible():
    """``(utilisable, raison)`` — la raison n'a de sens que si c'est faux."""
    try:
        brut = _appeler('/status/', 'GET', None, timeout=3)
    except Exception as e:
        _log.warning('maquette injoignable : %s', e)
        return False, ('Maquette injoignable : le serveur de routes 418 n\'a '
                       'pas démarré. Rechargez pyRevit, puis /journal.')
    try:
        etat = json.loads(brut)
    except ValueError:
        return False, 'Maquette injoignable : réponse illisible de Revit.'
    if not etat.get('revit_available'):
        return False, 'Aucun document Revit ouvert : les outils resteront muets.'
    return True, ''


def executer(nom, arguments=None):
    """Lance un outil et renvoie sa sortie en texte, prête à être renvoyée.

    Ne lève jamais : un échec part au modèle sous forme de JSON ``{"erreur":…}``
    pour qu'il puisse le dire ou tenter autre chose, plutôt que de faire
    échouer tout le tour.
    """
    entree = _PAR_NOM.get(nom)
    if entree is None:
        return _erreur('outil inconnu : {0}'.format(nom))
    _nom, route, methode, _description, _schema = entree
    corps = arguments if isinstance(arguments, dict) else None
    try:
        brut = _appeler(route, methode, corps)
    except HTTPError as e:
        _log.error('%s -> HTTP %s', nom, getattr(e, 'code', '?'))
        return _erreur('Revit a refusé l\'appel (HTTP {0})'.format(
            getattr(e, 'code', '?')))
    except URLError as e:
        _log.error('%s -> injoignable : %s', nom, getattr(e, 'reason', e))
        return _erreur('maquette injoignable — {0}'.format(
            getattr(e, 'reason', e)))
    except Exception as e:
        _log.exception('%s a échoué', nom)
        return _erreur('{0}'.format(e))
    _log.debug('%s -> %s octets', nom, len(brut))
    return _tronquer(brut)


def _appeler(route, methode, corps, timeout=DELAI):
    # Démarrage paresseux : on est ici sur un fil de fond du chat, Revit est
    # bâti et au repos. C'est le seul moment sûr pour ouvrir la socket.
    assurer()
    url = base() + PREFIXE + route
    donnees = None
    if methode == 'POST':
        # ensure_ascii=False : sous IronPython, laisser json échapper les
        # accents lui-même lève. On encode explicitement derrière.
        donnees = json.dumps(corps or {}, ensure_ascii=False).encode('utf-8')
    requete = Request(url, data=donnees)
    if donnees is not None:
        requete.add_header('Content-Type', 'application/json; charset=utf-8')
    return urlopen(requete, timeout=timeout).read().decode('utf-8', 'replace')


def _tronquer(texte):
    if len(texte) <= LIMITE_SORTIE:
        return texte
    return (texte[:LIMITE_SORTIE] +
            '\n…tronqué à {0} caractères — affiner les filtres de l\'outil '
            '(contains, limit) pour en voir moins à la fois.'.format(
                LIMITE_SORTIE))


def _erreur(message):
    return json.dumps({'erreur': message}, ensure_ascii=False)
