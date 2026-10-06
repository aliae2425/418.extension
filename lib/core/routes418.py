# -*- coding: utf-8 -*-
"""Où joindre la maquette : le serveur de routes de pyRevit, port découvert.

418 n'instancie plus son propre ``RoutesServer``. L'essai a coûté deux
plantages de Revit, et la raison est structurelle, pas une maladresse à
corriger : le module ``pyrevit.routes.server.server`` crée un
``UI.ExternalEvent`` au chargement, et Revit n'accepte ça que sur le fil
principal, hors OnStartup. Notre serveur n'aurait besoin d'exister qu'au
premier appel du chat — donc sur un fil de fond, donc trop tard. Les deux
contraintes ne se recouvrent nulle part.

S'y ajoutait un défaut qu'on ne pouvait pas corriger sans éditer amont :
``REQUEST_HNDLR`` et ``EVENT_HNDLR`` sont des singletons de module,
réécrits à chaque requête. Deux serveurs = deux requêtes concurrentes qui se
marchent dessus dans le contexte d'API Revit.

On se branche donc sur le serveur que pyRevit tient déjà, en lui demandant son
port au lieu de le supposer — 48884 monte d'un cran par Revit supplémentaire,
le coder en dur serait un bug en attente. On ne crée rien, on ne démarre rien,
on ne touche à aucun de ses réglages.

Contrepartie assumée : si la case « Routes » des réglages pyRevit n'est pas
cochée, aucun serveur ne tourne et les outils sont muets. Le bandeau du chat
le dit, plutôt que de faire tomber Revit pour l'éviter.
"""
from __future__ import unicode_literals

try:
    from core.journal import journal
except Exception:
    from lib.core.journal import journal

try:
    # Lecture d'un dictionnaire posé sur l'AppDomain : aucun objet Revit créé,
    # rien qui exige le fil principal. C'est tout ce qu'on s'autorise ici.
    from pyrevit.coreutils import envvars
except Exception:                      # hors Revit : module importable quand même
    envvars = None

_log = journal('routes')

ABSENT = ('Serveur de routes pyRevit éteint : cocher « Routes » dans les '
          'réglages pyRevit, puis redémarrer Revit.')


def serveur():
    """L'instance que pyRevit fait tourner, ``None`` s'il n'y en a pas."""
    if envvars is None:
        return None
    try:
        return envvars.get_pyrevit_env_var(envvars.ROUTES_SERVER)
    except Exception:
        _log.exception('lecture de ROUTES_SERVER')
        return None


def base():
    """Racine des appels HTTP vers la maquette, ``''`` si rien ne tourne."""
    actif = serveur()
    if actif is None:
        return ''
    # `host` vaut '' quand pyRevit écoute sur toutes les interfaces : on
    # s'adresse à la boucle locale dans tous les cas, on est dans le process.
    return 'http://127.0.0.1:{0}'.format(actif.port)
