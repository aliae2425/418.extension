# -*- coding: utf-8 -*-
"""Client de chat passant par le CLI ``codex``, déjà connecté.

Aucune clé API : le CLI a été authentifié une fois dans le navigateur
(``codex login``) et l'usage passe sur l'abonnement ChatGPT. On ne lit ni ne
rejoue son jeton — on lui parle en sous-processus, il gère son OAuth.

Logique pure (aucun import Revit ni WPF) pour rester testable hors Revit.
"""
from __future__ import unicode_literals
import os
import subprocess
import tempfile
import time

try:
    from core.journal import journal, flux
    from core.chat_syntaxe import SYSTEME
except Exception:
    from lib.core.journal import journal, flux
    from lib.core.chat_syntaxe import SYSTEME

_log = journal('cli')

EXECUTABLE = 'codex'

# --ephemeral : aucune session laissée sur le disque.
# -s read-only : le modèle peut lire pour répondre, jamais écrire.
# --ignore-user-config : le chat n'hérite ni du config.toml ni des consignes
#   personnelles de l'utilisateur ; l'authentification, elle, reste lue.
ARGUMENTS = ['exec', '--skip-git-repo-check', '--ephemeral',
             '--ignore-user-config', '-s', 'read-only', '--color', 'never']

ABSENT = 'CLI codex introuvable — l\'installer (npm i -g @openai/codex)'
DECONNECTE = 'CLI codex non connecté — choisir de nouveau pour ouvrir le navigateur'

# CREATE_NO_WINDOW : sans lui, une console noire clignote par-dessus Revit
# à chaque message.
_SANS_FENETRE = 0x08000000

# Statut de connexion mis en cache : assez court pour qu'un « codex login »
# terminé dans le navigateur soit vu, assez long pour ne pas lancer un
# processus à chaque rafraîchissement du panneau.
DELAI_STATUT = 10.0
_statut = {}

# Le `codex login` en cours, pour savoir quand l'utilisateur a fini dans son
# navigateur — sans lui il faudrait relancer /connect à la main.
_login = []
DELAI_LOGIN = 300.0


class ErreurCLI(Exception):
    """Échec d'appel : CLI absent, non connecté, ou sortie illisible."""


class _JamaisLevee(Exception):
    """Repli de branche ``except`` sous Python 2, où rien ne la lève."""


_EXPIRATION = getattr(subprocess, 'TimeoutExpired', _JamaisLevee)


def chemin(nom=None):
    """Chemin complet de l'exécutable, ``None`` s'il est introuvable.

    Réimplémenté plutôt que ``shutil.which`` : celui-ci n'existe pas sous
    IronPython 2.7, qui est le moteur du panneau ancré. Et le nom nu ne suffit
    pas — ``CreateProcess`` ne résout pas PATHEXT, donc « codex » reste
    introuvable alors que « codex.CMD » est bien dans le PATH.
    """
    nom = nom or EXECUTABLE
    if os.path.dirname(nom):
        return nom if os.path.isfile(nom) else None
    extensions = ['']
    if os.name == 'nt':
        pathext = [e for e in os.environ.get('PATHEXT', '').split(os.pathsep)
                   if e]
        # npm pose DEUX fichiers côte à côte : « codex » (script shell, que
        # CreateProcess ne sait pas lancer — c'est le [Errno 2]) et
        # « codex.CMD ». Ne chercher que les extensions exécutables, sauf si
        # le nom en porte déjà une.
        if not any(nom.lower().endswith(e.lower()) for e in pathext):
            extensions = pathext
    for dossier in os.environ.get('PATH', '').split(os.pathsep):
        if not dossier:
            continue
        for extension in extensions:
            candidat = os.path.join(dossier, nom + extension)
            if os.path.isfile(candidat):
                return candidat
    return None


def oublier_statut():
    _statut.clear()


def connecte():
    """``codex login status`` : le CLI porte-t-il une session utilisable ?

    Mis en cache : ``pret()`` est lu par une propriété liée au XAML, donc
    plusieurs fois par interaction, et chaque lecture coûte un processus.
    """
    maintenant = time.time()
    if _statut and maintenant - _statut['quand'] < DELAI_STATUT:
        return _statut['valeur']
    valeur = _demander_statut()
    _statut['quand'] = maintenant
    _statut['valeur'] = valeur
    return valeur


def _demander_statut():
    executable = chemin()
    if not executable:
        _log.warning('%s introuvable dans le PATH', EXECUTABLE)
        return False
    try:
        processus = subprocess.Popen(
            [executable, 'login', 'status'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, **_options())
        sortie, erreur = processus.communicate()
    except Exception as e:
        _log.warning('login status a échoué : %s', e)
        return False
    # codex écrit ce statut sur stderr, pas sur stdout : lire les deux.
    dit = (_texte(sortie) + _texte(erreur)).lower()
    _log.debug('login status rc=%s | %s', processus.returncode,
               dit.strip()[:200])
    return processus.returncode == 0 and 'logged in' in dit


def pret():
    return connecte()


def raison():
    return ABSENT if not chemin() else DECONNECTE


def connecter():
    """Lance ``codex login`` : c'est LE flux navigateur, tenu par le CLI.

    On ne l'attend pas — l'utilisateur va s'authentifier dans son navigateur
    pendant que Revit reste rendu à la main.
    """
    executable = chemin()
    if not executable:
        _log.warning('connecter() : %s introuvable', EXECUTABLE)
        return None
    # La session va changer : le statut en cache n'a plus rien à dire.
    oublier_statut()
    # `codex login` écrit son URL et sa progression, puis attend le retour du
    # navigateur : on ne l'attend pas (Revit resterait figé), mais on branche
    # ses deux flux sur le journal — sinon un échec est totalement muet.
    sortie = flux()
    try:
        processus = subprocess.Popen(
            [executable, 'login'],
            stdout=sortie or subprocess.PIPE,
            stderr=subprocess.STDOUT if sortie else subprocess.PIPE,
            **_options())
        del _login[:]
        _login.append(processus)
    except Exception as e:
        _log.exception('codex login n\'a pas démarré')
        raise ErreurCLI('ouverture impossible — {0}'.format(e))
    finally:
        # Le processus fils garde son propre descripteur : refermer le nôtre.
        if sortie is not None:
            try:
                sortie.close()
            except Exception:
                pass
    _log.info('codex login lancé (%s)', executable)
    return 'Connexion ouverte dans le navigateur…'


def attendre_connexion(timeout=None, pas=0.5):
    """Bloque jusqu'à la fin de ``codex login``, puis dit si c'est bon.

    À appeler hors du fil d'interface. On surveille le processus plutôt que
    d'interroger le statut en boucle : `codex login` se termine de lui-même
    quand le navigateur a rendu la main, ou quand l'utilisateur abandonne.
    """
    timeout = DELAI_LOGIN if timeout is None else timeout
    processus = _login[0] if _login else None
    limite = time.time() + timeout
    while processus is not None and processus.poll() is None:
        if time.time() >= limite:
            _log.warning('codex login toujours en cours après %s s', timeout)
            break
        time.sleep(pas)
    oublier_statut()
    ouverte = connecte()
    _log.info('fin de codex login | connecte=%s', ouverte)
    return ouverte


def deconnecter():
    """``codex logout`` : efface les identifiants gardés par le CLI.

    Contrairement à la connexion, c'est immédiat et sans navigateur : on
    l'attend.
    """
    executable = chemin()
    if not executable:
        return None
    try:
        processus = subprocess.Popen(
            [executable, 'logout'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, **_options())
        sortie, erreur = processus.communicate()
    except Exception as e:
        _log.exception('codex logout a échoué')
        raise ErreurCLI('déconnexion impossible — {0}'.format(e))
    finally:
        oublier_statut()
    dit = _fin(erreur) or _fin(sortie)
    _log.info('codex logout rc=%s | %s', processus.returncode, dit)
    if processus.returncode != 0:
        raise ErreurCLI(dit or 'codex logout a échoué (code {0})'.format(
            processus.returncode))
    return 'Session codex fermée. /connect pour rouvrir le navigateur.'


def modeles():
    """Non listable : le harnais choisit son modèle, et n'expose pas de liste."""
    return ()


def invite(messages):
    """Aplatit l'échange : ``codex exec`` ne garde rien d'un appel à l'autre."""
    lignes = [SYSTEME, '']
    for role, texte in messages:
        lignes.append('{0} : {1}'.format(
            'Utilisateur' if role == 'user' else 'Toi', texte))
    return '\n'.join(lignes)


def repondre(messages, modele=None, timeout=180, **_kwargs):
    """Renvoie le texte de la réponse, ou lève ``ErreurCLI``."""
    executable = chemin()
    if not executable:
        raise ErreurCLI(ABSENT)
    arguments = list(ARGUMENTS) + (['-m', modele] if modele else [])

    # -o : le CLI écrit la réponse finale seule, ce qui évite d'avoir à
    # démêler sa trace de progression sur stdout.
    descripteur, sortie = tempfile.mkstemp(prefix='openarchi_', suffix='.txt')
    os.close(descripteur)
    try:
        processus = subprocess.Popen(
            [executable] + arguments + ['-o', sortie, '-'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, **_options())
        entree = invite(messages).encode('utf-8')
        try:
            _, erreur = processus.communicate(entree, timeout=timeout)
        except TypeError:              # Python 2 : communicate() sans timeout
            _, erreur = processus.communicate(entree)
        except _EXPIRATION:
            processus.kill()
            raise ErreurCLI('pas de réponse après {0} s'.format(timeout))

        _log.debug('exec rc=%s modele=%s', processus.returncode, modele)
        if processus.returncode != 0:
            _log.error('exec a échoué : %s', _texte(erreur)[-600:])
            raise ErreurCLI(_fin(erreur) or
                            'codex a échoué (code {0})'.format(
                                processus.returncode))
        with open(sortie, 'rb') as fichier:
            reponse = fichier.read().decode('utf-8').strip()
    finally:
        try:
            os.remove(sortie)
        except OSError:
            pass

    if not reponse:
        raise ErreurCLI('réponse vide — vérifier « codex login »')
    return reponse


def _options():
    return {'creationflags': _SANS_FENETRE} if os.name == 'nt' else {}


def _texte(brut):
    if not brut:
        return ''
    if isinstance(brut, type('')):
        return brut
    return brut.decode('utf-8', 'replace')


def _fin(erreur):
    """Dernière ligne utile de stderr : le reste n'est que de la bannière."""
    lignes = [ligne.strip() for ligne in _texte(erreur).splitlines()
              if ligne.strip()]
    return lignes[-1] if lignes else ''
