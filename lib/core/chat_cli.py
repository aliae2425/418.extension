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

try:
    from shutil import which
except ImportError:                    # Python 2 / IronPython
    which = None

EXECUTABLE = 'codex'

# --ephemeral : aucune session laissée sur le disque.
# -s read-only : le modèle peut lire pour répondre, jamais écrire.
# --ignore-user-config : le chat n'hérite ni du config.toml ni des consignes
#   personnelles de l'utilisateur ; l'authentification, elle, reste lue.
ARGUMENTS = ['exec', '--skip-git-repo-check', '--ephemeral',
             '--ignore-user-config', '-s', 'read-only', '--color', 'never']

RAISON = 'CLI codex introuvable — l\'installer puis « codex login »'

# CREATE_NO_WINDOW : sans lui, une console noire clignote par-dessus Revit
# à chaque message.
_SANS_FENETRE = 0x08000000

SYSTEME = ("Tu assistes un architecte dans Autodesk Revit. Réponds en "
           "français, brièvement. Les #références citent des éléments de la "
           "maquette ; tu n'y as pas encore accès, demande-les si besoin.")


class ErreurCLI(Exception):
    """Échec d'appel : CLI absent, non connecté, ou sortie illisible."""


class _JamaisLevee(Exception):
    """Repli de branche ``except`` sous Python 2, où rien ne la lève."""


_EXPIRATION = getattr(subprocess, 'TimeoutExpired', _JamaisLevee)


def chemin():
    """Chemin de l'exécutable, ``None`` s'il est introuvable."""
    if which is not None:
        return which(EXECUTABLE)
    return EXECUTABLE


def pret():
    return bool(chemin())


def invite(messages):
    """Aplatit l'échange : ``codex exec`` ne garde rien d'un appel à l'autre."""
    lignes = [SYSTEME, '']
    for role, texte in messages:
        lignes.append('{0} : {1}'.format(
            'Utilisateur' if role == 'user' else 'Toi', texte))
    return '\n'.join(lignes)


def repondre(messages, timeout=180, **_kwargs):
    """Renvoie le texte de la réponse, ou lève ``ErreurCLI``."""
    executable = chemin()
    if not executable:
        raise ErreurCLI(RAISON)

    # -o : le CLI écrit la réponse finale seule, ce qui évite d'avoir à
    # démêler sa trace de progression sur stdout.
    descripteur, sortie = tempfile.mkstemp(prefix='openarchi_', suffix='.txt')
    os.close(descripteur)
    try:
        processus = subprocess.Popen(
            [executable] + ARGUMENTS + ['-o', sortie, '-'],
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

        if processus.returncode != 0:
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


def _fin(erreur):
    """Dernière ligne utile de stderr : le reste n'est que de la bannière."""
    if not erreur:
        return ''
    if not isinstance(erreur, type('')):
        erreur = erreur.decode('utf-8', 'replace')
    lignes = [ligne.strip() for ligne in erreur.splitlines() if ligne.strip()]
    return lignes[-1] if lignes else ''
