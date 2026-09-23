# -*- coding: utf-8 -*-
"""Les outils que le modèle peut appeler sur la maquette. Lecture seule.

Le panneau tourne DANS Revit : les routes pyRevit lui suffisent, elles sont
déjà servies par pyRevit (cf. ``routes418``). Pas de client MCP ici —
le protocole MCP existe pour les clients qui sont dehors, et le traverser
depuis l'intérieur ajouterait un process Python à la place d'un GET local.

Catalogue écrit à la main contre les vraies signatures des gestionnaires de
``vendor/mcp-server-for-revit/revit_mcp/`` : les noms de paramètres ne se
devinent pas (``list_families`` filtre sur ``contains``, pas sur une
catégorie). Toute entrée ajoutée ici doit être relue là-bas.

Écriture : uniquement les routes qui posent une transaction nommée, donc
défaisables au ``Ctrl+Z`` — ``place_family``, ``color_splash``,
``clear_colors``. Restent dehors ``save_document``, ``sync_with_central``,
``open_document``, ``close_document`` (aucune transaction, rien à annuler, et
la synchro pousse sur le central) et ``execute_code`` (IronPython arbitraire,
que le modèle peut lui-même sortir de toute transaction).

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
    from core import routes418
except Exception:
    from lib.core.journal import journal
    from lib.core import routes418

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

    # --- écriture ---------------------------------------------------------
    # Uniquement les routes qui posent une transaction nommée : le garde-fou
    # est la pile d'annulation de Revit, Ctrl+Z les défait une par une. Restent
    # dehors, et doivent y rester sans décision explicite :
    #   save_document · sync_with_central · open_document · close_document
    #     — aucune transaction, donc rien à annuler ; sync pousse en plus sur
    #       le central, donc chez les autres.
    #   execute_code
    #     — IronPython arbitraire, et le modèle peut demander lui-même
    #       use_transaction=false. Ce n'est pas un outil, c'est une porte.
    ('revit_place_family', '/place_family/', 'POST',
     'Place une instance de famille. MODIFIE la maquette, dans une '
     'transaction annulable. Coordonnées en PIEDS (unités internes Revit).',
     {'type': 'object',
      'properties': {
          'family_name': {'type': 'string'},
          'type_name': {'type': 'string',
                        'description': 'type voulu ; le premier si omis'},
          'location': {'type': 'object',
                       'description': 'position en pieds',
                       'properties': {'x': {'type': 'number'},
                                      'y': {'type': 'number'},
                                      'z': {'type': 'number'}},
                       'required': ['x', 'y', 'z']},
          'rotation': {'type': 'number', 'description': 'radians, 0 par défaut'},
          'level_name': {'type': 'string'},
          'properties': {'type': 'object',
                         'description': 'paramètres à poser, p. ex. {"Mark": "A1"}'}},
      'required': ['family_name', 'location'],
      'additionalProperties': False}),
    ('revit_color_splash', '/color_splash/', 'POST',
     'Colore les éléments d\'une catégorie selon les valeurs d\'un paramètre. '
     'MODIFIE l\'affichage de la vue active, dans une transaction annulable.',
     {'type': 'object',
      'properties': {
          'category_name': {'type': 'string'},
          'parameter_name': {'type': 'string'},
          'use_gradient': {'type': 'boolean'},
          'custom_colors': {'type': 'array', 'items': {'type': 'string'},
                            'description': 'couleurs hexa, p. ex. ["#FF0000"]'}},
      'required': ['category_name', 'parameter_name'],
      'additionalProperties': False}),
    ('revit_clear_colors', '/clear_colors/', 'POST',
     'Retire les remplacements de couleur d\'une catégorie. MODIFIE '
     'l\'affichage de la vue active, dans une transaction annulable.',
     {'type': 'object',
      'properties': {'category_name': {'type': 'string'}},
      'required': ['category_name'],
      'additionalProperties': False}),
)

_PAR_NOM = dict((entree[0], entree) for entree in CATALOGUE)


def outils():
    """Le catalogue sous forme neutre : chaque client lui donne sa forme."""
    return [{'nom': nom, 'description': description, 'parametres': schema}
            for nom, _route, _methode, description, schema in CATALOGUE]


def disponible():
    """``(utilisable, raison)`` — la raison n'a de sens que si c'est faux."""
    if not routes418.base():
        return False, routes418.ABSENT
    try:
        brut = _appeler('/status/', 'GET', None, timeout=3)
    except Exception as e:
        _log.warning('maquette injoignable : %s', e)
        return False, ('Maquette injoignable : le serveur de routes pyRevit '
                       'ne répond pas. /journal pour le détail.')
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
    _nom, route, methode, _description, schema = entree
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
    return _tronquer(brut, bool(schema.get('properties')))


def _appeler(route, methode, corps, timeout=DELAI):
    # On ne démarre rien : le serveur est celui de pyRevit, ou il n'y en a pas.
    racine = routes418.base()
    if not racine:
        raise ValueError(routes418.ABSENT)
    url = racine + PREFIXE + route
    donnees = None
    if methode == 'POST':
        # ensure_ascii=False : sous IronPython, laisser json échapper les
        # accents lui-même lève. On encode explicitement derrière.
        donnees = json.dumps(corps or {}, ensure_ascii=False).encode('utf-8')
    requete = Request(url, data=donnees)
    if donnees is not None:
        requete.add_header('Content-Type', 'application/json; charset=utf-8')
    return urlopen(requete, timeout=timeout).read().decode('utf-8', 'replace')


def _tronquer(texte, filtrable=True):
    """Coupe, et dit au modèle quoi faire — ce qui dépend de l'outil.

    Conseiller « affine les filtres » à un outil qui n'en a aucun l'envoie
    rappeler le même outil pour le même résultat : c'est arrivé en vrai avec
    revit_list_views, deux fois d'affilée.
    """
    if len(texte) <= LIMITE_SORTIE:
        return texte
    conseil = ('restreindre les arguments de l\'outil pour en voir moins '
               'à la fois' if filtrable else
               'cet outil ne prend aucun filtre : la liste restera '
               'incomplète, inutile de le rappeler à l\'identique')
    return '{0}\n…tronqué à {1} caractères — {2}.'.format(
        texte[:LIMITE_SORTIE], LIMITE_SORTIE, conseil)


def _erreur(message):
    return json.dumps({'erreur': message}, ensure_ascii=False)
