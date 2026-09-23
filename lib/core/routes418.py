# -*- coding: utf-8 -*-
"""Serveur de routes propre à 418 : notre instance, notre port, en local.

pyRevit n'expose qu'UN serveur de routes par process — ``routes.API(nom)`` ne
donne qu'un préfixe d'URL, jamais un port — et il ne démarre que si la case
« Routes » est cochée dans les réglages (``loader/sessionmgr.py`` :
``if user_config.routes_server``). Un outil tout-en-un ne peut pas dépendre
d'une case à cocher : on instancie donc notre propre ``RoutesServer``, sur un
port fixe, lié à la boucle locale.

Ce qu'on ne touche PAS, volontairement : ``user_config`` (réglage global de
pyRevit, pas le nôtre), ``serverinfo.register()`` (sa comptabilité de ports)
et ``envvars.ROUTES_SERVER`` (l'emplacement de SON serveur). Le serveur de
pyRevit reste ce qu'il est, allumé ou éteint, sur 48884.

Le routeur de pyRevit est global : notre instance sert donc la même table de
routes, ``/revit_mcp/...`` compris. On ne peut pas l'en empêcher sans éditer
amont, et ça ne coûte rien puisqu'on n'écoute que sur la boucle locale.

Hors Revit (tests), le module reste importable et ``demarrer()`` renvoie
``None`` sans lever.
"""
from __future__ import unicode_literals

try:
    from core.journal import journal
except Exception:
    from lib.core.journal import journal

try:
    from pyrevit.coreutils import envvars
except Exception:                      # hors Revit : import silencieux
    envvars = None

_log = journal('routes')


def _classe_serveur():
    """``RoutesServer``, importé au dernier moment. ``None`` hors Revit.

    Surtout PAS au chargement du module : importer
    ``pyrevit.routes.server.server`` exécute son ``UI.ExternalEvent.Create()``
    de niveau module. Or ce module est atteint par la chaîne
    ``startup.py → OpenArchiPanel → OpenArchiChatVM → chat_oauth →
    revit_outils → routes418``, donc pendant OnStartup — et créer un
    ExternalEvent à ce moment-là fait tomber Revit au lancement.
    """
    try:
        from pyrevit.routes.server.server import RoutesServer
        return RoutesServer
    except Exception:
        _log.exception('RoutesServer indisponible')
        return None

# Fixe, et à nous. Hors des plages exclues par Windows (50000-50059,
# 55000-55001) et loin de celle de pyRevit, qui part de 48884 et monte d'un
# cran par Revit supplémentaire — ce qui rend 48884 impossible à coder en dur.
PORT = 41800

# Jamais '' : c'est le défaut de ``routes_host`` chez pyRevit, et '' veut dire
# 0.0.0.0, donc tout le réseau local. Nos routes ne sortent pas de la machine.
HOTE = '127.0.0.1'

# Rangé dans l'AppDomain, pas dans un global de module : un « Reload » pyRevit
# rejoue les scripts dans un moteur neuf — les globals disparaissent, le
# socket non.
CLE = 'PYREVIT_418_ROUTESSERVER'


def base():
    """Racine des appels HTTP vers la maquette."""
    return 'http://{0}:{1}'.format(HOTE, PORT)


def assurer():
    """Le serveur, démarré si besoin. C'est la porte d'entrée normale.

    Jamais appelé depuis ``startup.py`` : lier une socket et lancer un fil de
    service pendant OnStartup fait tomber Revit au lancement. pyRevit ne
    démarre le sien qu'à la toute fin de sa session, pour la même raison.
    Ici on va plus loin — rien ne démarre tant que le chat n'a rien demandé.
    """
    if envvars is None:
        return None
    existant = envvars.get_pyrevit_env_var(CLE)
    if existant is not None:
        return existant
    return demarrer()


def demarrer():
    """(Re)démarre notre serveur. Renvoie l'instance, ``None`` hors Revit."""
    classe = _classe_serveur()
    if classe is None or envvars is None:
        return None
    # Obligatoire, et pas par politesse : ``ThreadedHttpServer`` pose
    # ``allow_reuse_address = True``, et sous Windows SO_REUSEADDR laisse un
    # SECOND socket se lier à un port déjà écouté, sans la moindre erreur.
    # Sans cet arrêt, chaque Reload empile une instance de plus sur le port et
    # les requêtes partent au hasard de l'une ou de l'autre.
    arreter()
    serveur = classe(host=HOTE, port=PORT)         # démarre son fil tout seul
    envvars.set_pyrevit_env_var(CLE, serveur)
    _log.info('serveur 418 à l\'écoute sur %s', base())
    return serveur


def arreter():
    """Arrête l'instance laissée par le chargement précédent, s'il y en a une."""
    if envvars is None:
        return
    ancien = envvars.get_pyrevit_env_var(CLE)
    if ancien is None:
        return
    try:
        ancien.stop()
        _log.debug('serveur 418 précédent arrêté')
    except Exception:
        _log.exception('arrêt du serveur 418 précédent')
    finally:
        envvars.set_pyrevit_env_var(CLE, None)
