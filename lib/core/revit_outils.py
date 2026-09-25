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

**Toutes** les routes du serveur sont ouvertes, sur décision explicite de
l'architecte. Trois familles, et la différence n'est pas cosmétique :

- lecture — ne touche à rien ;
- écriture en transaction (``place_family``, ``color_splash``,
  ``clear_colors``) — ``Ctrl+Z`` les défait une par une ;
- **irréversible** (``execute_code``, ``save_document``,
  ``sync_with_central``, ``open_document``, ``close_document``) — aucune
  transaction, donc aucun retour arrière. ``sync_with_central`` pousse en
  plus sur le central, donc chez toute l'équipe.

Les seuls garde-fous sur la troisième famille sont la description lue par le
modèle et la consigne système (``chat_syntaxe.OUTILLE``). Les affaiblir,
c'est retirer le dernier filet — chaque appel est en outre journalisé en
WARNING avec ses arguments, pour qu'on puisse savoir après coup ce qui s'est
passé.

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
    from core.chat_syntaxe import detail_http
    from core import routes418
except Exception:
    from lib.core.journal import journal
    from lib.core.chat_syntaxe import detail_http
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

# Le serveur de routes pyRevit partage UN handler de requête et UN
# ExternalEvent entre toutes ses requêtes (server.py:36-41, singletons de
# module réécrits à chaque appel). Deux requêtes simultanées se marchent
# dessus dans le contexte d'API Revit — au mieux la réponse part au mauvais
# appelant, au pire Revit tombe. On ne peut pas corriger amont, mais on peut
# garantir que 418 n'en émet jamais deux à la fois.
# ponytail: verrou global. Il ne protège que de NOUS — un client MCP externe
# ou rvt-mcp qui tape le même serveur en parallèle rouvre la course.
_VERROU = threading.Lock()

# Dernier verdict de `disponible()`, relu par le bandeau du panneau sans
# refaire d'appel : une requête de plus, c'était une occasion de collision.
_dernier = {'ok': True, 'raison': ''}

# Dernier outil qui a échoué. Le modèle reçoit l'erreur et en fait ce qu'il
# veut — parfois rien. L'architecte, lui, doit la voir : le panneau vient la
# chercher ici pour l'afficher en haut.
_echec = {'texte': ''}

_VIDE = {'type': 'object', 'properties': {}, 'additionalProperties': False}

# nom exposé au modèle · route · méthode · description · schéma des arguments
CATALOGUE = (
    ('revit_status', '/status/', 'GET',
     'État du lien avec Revit et titre du document ouvert.', _VIDE),
    ('revit_model_info', '/model_info/', 'GET',
     'Vue d\'ensemble de la maquette : niveaux, nombre de pièces, '
     'avertissements. Les altitudes y sont en PIEDS, comme partout dans '
     'Revit.', _VIDE),
    ('revit_current_view_info', '/current_view_info/', 'GET',
     'Vue active : nom, type, échelle, discipline.', _VIDE),
    ('revit_list_views', '/list_views/', 'GET',
     'Toutes les vues du projet, rangées par type. Les FEUILLES sont dans le '
     'seau « other », pas dans un seau à elles. Sortie volumineuse et sans '
     'aucun filtre : sur un gros projet elle arrive tronquée, dis-le plutôt '
     'que de la présenter comme complète.', _VIDE),
    ('revit_list_levels', '/list_levels/', 'GET',
     'Niveaux du projet. Les altitudes sont en PIEDS : convertis-les en '
     'mètres (×0,3048) avant de les annoncer.', _VIDE),
    ('revit_list_family_categories', '/list_family_categories/', 'GET',
     'Catégories de familles chargées et leur nombre de types. À appeler '
     'AVANT de chercher une famille par son nom : il donne les noms de '
     'catégories réellement présents dans ce projet, en français.', _VIDE),
    ('revit_list_families', '/list_families/', 'POST',
     'Familles et types chargés. ATTENTION : « contains » filtre sur le nom '
     'de la famille ou du type, JAMAIS sur la catégorie — chercher « porte » '
     'ne rend pas les éléments de la catégorie « Portes » si les familles '
     'portent un autre nom. Ne rien trouver ne prouve rien : vérifie avec '
     'revit_list_family_categories avant de conclure à une absence.',
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

    # --- écriture, dans une transaction nommée ----------------------------
    # Ctrl+Z les défait une par une : le garde-fou est la pile d'annulation
    # de Revit.
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

    # --- IRRÉVERSIBLE -----------------------------------------------------
    # Aucune de ces routes ne pose de transaction : Ctrl+Z n'y peut RIEN.
    # Ouvertes sur décision explicite de l'architecte, contre l'avis donné.
    # Le seul garde-fou qui reste est la description lue par le modèle, et
    # la consigne système (chat_syntaxe.OUTILLE) : les deux doivent rester
    # aussi explicites qu'elles le sont ici.
    ('revit_execute_code', '/execute_code/', 'POST',
     'DANGER — exécute du code IronPython dans Revit. Irréversible si '
     'use_transaction vaut false. Dernier recours, quand aucun autre outil '
     'ne fait l\'affaire, et jamais sans l\'accord explicite de '
     'l\'architecte dans le message précédent.',
     {'type': 'object',
      'properties': {
          'code': {'type': 'string',
                   'description': 'IronPython 2.7 ; doc et uidoc disponibles'},
          'description': {'type': 'string',
                          'description': 'ce que fait le code, en français'},
          'use_transaction': {
              'type': 'boolean',
              'description': 'true (défaut) = annulable. Ne passer false '
                             'que pour une opération d\'interface pure.'}},
      'required': ['code'],
      'additionalProperties': False}),
    ('revit_save_document', '/save_document/', 'POST',
     'DANGER — enregistre le projet. IRRÉVERSIBLE : écrase la version sur '
     'disque, Ctrl+Z ne la ramène pas. Jamais sans demande explicite.',
     {'type': 'object',
      'properties': {
          'file_path': {'type': 'string',
                        'description': 'chemin pour un « enregistrer sous » ; '
                                       'omis = enregistre sur place'}},
      'additionalProperties': False}),
    ('revit_sync_with_central', '/sync_with_central/', 'POST',
     'DANGER — synchronise avec le fichier central. IRRÉVERSIBLE, et visible '
     'par toute l\'équipe. Jamais sans demande explicite.',
     {'type': 'object',
      'properties': {
          'comment': {'type': 'string', 'description': 'commentaire de synchro'},
          'compact': {'type': 'boolean'},
          'relinquish_all': {'type': 'boolean',
                             'description': 'libérer tous les emprunts (défaut true)'}},
      'additionalProperties': False}),
    ('revit_open_document', '/open_document/', 'POST',
     'DANGER — ouvre un autre projet dans Revit. Change le document courant, '
     'donc la cible de TOUS les autres outils. Jamais sans demande explicite.',
     {'type': 'object',
      'properties': {
          'file_path': {'type': 'string', 'description': 'chemin du .rvt'},
          'detach': {'type': 'boolean', 'description': 'détacher du central'},
          'audit': {'type': 'boolean'}},
      'required': ['file_path'],
      'additionalProperties': False}),
    ('revit_close_document', '/close_document/', 'POST',
     'DANGER — ferme le projet courant. IRRÉVERSIBLE, et les modifications '
     'non enregistrées sont perdues si save vaut false. Jamais sans demande '
     'explicite.',
     {'type': 'object',
      'properties': {
          'save': {'type': 'boolean',
                   'description': 'enregistrer avant de fermer (défaut false)'}},
      'additionalProperties': False}),
)

# Ce que le modèle ne peut pas défaire. Sert à la consigne système et au
# journal : un appel de cette liste mérite une ligne qu'on retrouve après coup.
IRREVERSIBLES = ('revit_execute_code', 'revit_save_document',
                 'revit_sync_with_central', 'revit_open_document',
                 'revit_close_document')

_PAR_NOM = dict((entree[0], entree) for entree in CATALOGUE)


def outils():
    """Le catalogue sous forme neutre : chaque client lui donne sa forme."""
    return [{'nom': nom, 'description': description, 'parametres': schema}
            for nom, _route, _methode, description, schema in CATALOGUE]


def derniere_raison():
    """Ce qu'a conclu le dernier ``disponible()``. Aucun appel réseau.

    Le panneau s'en sert pour son bandeau : refaire une requête juste pour
    l'afficher, c'était une occasion de collision de plus sur le serveur.
    """
    return _dernier['raison']


def disponible():
    """``(utilisable, raison)`` — la raison n'a de sens que si c'est faux."""
    ok, raison = _verdict()
    _dernier['ok'], _dernier['raison'] = ok, raison
    return ok, raison


def _verdict():
    if not routes418.base():
        return False, routes418.ABSENT
    try:
        brut = _appeler('/status/', 'GET', None, timeout=5)
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
    if nom in IRREVERSIBLES:
        # En WARNING et avec les arguments : c'est la seule trace qui restera
        # pour comprendre ce que le modèle a fait, une fois que c'est fait.
        _log.warning('IRRÉVERSIBLE %s %s', nom, corps)
    try:
        brut = _appeler(route, methode, corps)
    except HTTPError as e:
        # detail_http lit le CORPS de la réponse : sans lui on ne garderait
        # que « HTTP 500 » et le vrai message — « AttributeError: Name » —
        # mourrait dans le journal de Revit.
        return _echoue(nom, detail_http(e))
    except URLError as e:
        return _echoue(nom, 'maquette injoignable — {0}'.format(
            getattr(e, 'reason', e)))
    except Exception as e:
        _log.exception('%s a échoué', nom)
        return _echoue(nom, '{0}'.format(e))
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
    # Une seule requête 418 en vol à la fois : le serveur de routes n'en
    # supporte pas deux (cf. _VERROU).
    with _VERROU:
        return urlopen(requete,
                       timeout=timeout).read().decode('utf-8', 'replace')


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
