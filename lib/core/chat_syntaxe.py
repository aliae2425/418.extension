# -*- coding: utf-8 -*-
"""Socle commun aux clients de chat.

Trois choses que ``chat_cli``, ``chat_oauth`` et ``chat_openai`` partagent :
la syntaxe des messages (commandes ``/x``, références ``#y``), l'invite
système, et la lecture des erreurs HTTP. Elles vivaient en trois copies —
l'invite au caractère près — ce qui garantissait qu'elles finissent par
diverger sans que rien ne le signale.

Logique pure (aucun import Revit ni WPF) pour rester testable hors Revit.
"""
from __future__ import unicode_literals
import json
import re

# Une seule invite pour tous les clients : trois copies, c'était trois
# comportements qui s'éloignent au premier ajustement.
SYSTEME = ("Tu assistes un architecte dans Autodesk Revit. Réponds en "
           "français, brièvement. Les #références citent des éléments de la "
           "maquette ; tu n'y as pas encore accès, demande-les si besoin.")

# Ajouté à SYSTEME par le client UNIQUEMENT quand des outils sont réellement
# fournis. L'écrire dans SYSTEME ferait promettre au modèle, chez les clients
# qui n'ont pas de boucle d'outils, des yeux qu'il n'a pas.
OUTILLE = (
    "\n\nTu disposes d'outils sur la maquette ouverte (préfixe revit_). "
    "Appelle librement ceux qui LISENT, plutôt que de supposer ou de demander "
    "à l'architecte ce que tu peux voir toi-même. Les longueurs et les "
    "coordonnées sont en PIEDS, l'unité interne de Revit.\n"
    "\n"
    "Les outils qui ÉCRIVENT ne s'appellent jamais pour explorer, seulement "
    "sur une demande claire, et tu annonces ce que tu vas faire avant :\n"
    "- revit_place_family, revit_color_splash, revit_clear_colors posent une "
    "transaction que l'architecte peut annuler au Ctrl+Z ;\n"
    "- revit_execute_code, revit_save_document, revit_sync_with_central, "
    "revit_open_document et revit_close_document sont IRRÉVERSIBLES : aucun "
    "Ctrl+Z ne les défait. Tu ne les appelles que si l'architecte les a "
    "demandés explicitement dans son dernier message. Un « fais le "
    "nécessaire » ou un « vas-y » ne suffit pas : dans le doute, tu décris "
    "l'appel exact que tu ferais et tu attends qu'il le confirme.\n"
    "\n"
    "revit_execute_code est un dernier recours : si un autre outil fait le "
    "travail, prends-le. Quand tu l'emploies, laisse use_transaction à true "
    "sauf pour une opération d'interface pure, et explique ton code.")

# Une commande n'est reconnue qu'EN TÊTE de message : une barre oblique au
# milieu d'une phrase (« 1/2 », un chemin, une URL) n'en est pas une.
_RE_COMMANDE = re.compile(r'^/([A-Za-z][\w-]*)\s*(.*)$', re.DOTALL)

# #{Nom avec espaces} pour les noms composés, #Nom pour le cas courant.
_RE_REFERENCE = re.compile(r'#(?:\{([^}]*)\}|([\w.\-]+))')


class Analyse(object):
    """Résultat de l'analyse d'un message saisi."""

    def __init__(self, texte, commande=None, arguments='', references=None):
        self.texte = texte
        self.commande = commande
        self.arguments = arguments
        self.references = references or []

    @property
    def est_commande(self):
        return self.commande is not None


def detail_http(erreur):
    """``HTTPError`` → « HTTP 400 — <message de l'API> ».

    Les fournisseurs logent leur message à trois endroits différents selon
    l'endpoint (``error.message``, ``error_description``, ``detail``) ; sans
    ce tri, l'utilisateur reçoit le corps JSON brut ou juste un code nu.
    """
    code = getattr(erreur, 'code', '?')
    try:
        corps = json.loads(erreur.read().decode('utf-8'))
    except Exception:
        return 'HTTP {0} — {1}'.format(code, getattr(erreur, 'reason', '') or '')
    if not isinstance(corps, dict):
        corps = {}
    erreur_ = corps.get('error')
    message = (corps.get('error_description') or
               (erreur_ if _est_texte(erreur_)
                else (erreur_ or {}).get('message')) or
               (corps.get('detail') if _est_texte(corps.get('detail')) else ''))
    return 'HTTP {0} — {1}'.format(code, message or 'sans détail')


def _est_texte(valeur):
    return isinstance(valeur, type(''))


def analyser(texte):
    texte = (texte or '').strip()
    commande = None
    arguments = ''
    trouve = _RE_COMMANDE.match(texte)
    if trouve:
        commande = trouve.group(1).lower()
        arguments = trouve.group(2).strip()

    references = []
    for accolades, nu in _RE_REFERENCE.findall(texte):
        nom = (accolades or nu).strip()
        if nom and nom not in references:
            references.append(nom)

    return Analyse(texte, commande, arguments, references)
