# -*- coding: utf-8 -*-
"""Remplacer une sentinelle par la vraie clé, dans les en-têtes sortants.

Pourquoi une sentinelle plutôt qu'un en-tête ajouté de rien : sans l'en-tête
au départ, le navigateur ne l'annonce pas dans son préflight CORS, et on
dépendrait de l'ordre entre son contrôle et notre interception. Avec, le
préflight est exact et on ne fait que substituer une valeur.

Le code vit ici, et non dans le volet, pour une seule raison : il décide si la
clé atteint l'API, et il ne s'éprouve pas dans Revit. Le volet garde la
plomberie WebView2 ; cette fonction ne connaît qu'un objet à trois méthodes.
"""
from __future__ import unicode_literals

try:
    from core.journal import journal
except Exception:
    from lib.core.journal import journal

_log = journal('signature')

# Chaque fournisseur a SON en-tête — `Authorization: Bearer` chez OpenAI,
# `x-api-key` nu chez Anthropic — et donc sa propre sentinelle. Les filtres
# restent étroits : la page n'a rien à demander ailleurs, mais c'est le genre
# de porte qu'on laisse fermée.
SIGNATURES = (
    {'fournisseur': 'openai',
     'filtre': 'https://api.openai.com/*',
     'entete': 'Authorization',
     'sentinelle': 'Bearer 418-hote',
     'prefixe': 'Bearer '},
    {'fournisseur': 'anthropic',
     'filtre': 'https://api.anthropic.com/*',
     'entete': 'x-api-key',
     'sentinelle': '418-hote',
     'prefixe': ''},
)


def signer(entetes, lire_cle, signatures=SIGNATURES):
    """Pose la vraie clé là où la page a laissé une sentinelle.

    ``entetes`` expose ``Contains``, ``GetHeader`` et ``SetHeader`` — c'est le
    contrat de `CoreWebView2HttpRequestHeaders`, et rien de plus n'est requis.

    Rend le fournisseur signé, ``''`` si rien ne l'a été. Ne lève JAMAIS :
    on est sur le fil d'interface de Revit.
    """
    for signature in signatures:
        try:
            # `Contains` AVANT `GetHeader` : ce dernier lève quand l'en-tête
            # est absent, et une requête vers Anthropic n'a pas
            # d'`Authorization`. Sans ce garde, la signature d'OpenAI levait
            # la première et emportait le reste de la boucle — la clé
            # Anthropic n'était jamais posée, pour un 401 muet.
            if not entetes.Contains(signature['entete']):
                continue
            # On ne signe QUE ce qui porte la sentinelle. Un en-tête différent
            # part tel quel et prend un 401 — un refus franc vaut mieux qu'un
            # appel anonyme signé par hasard.
            if entetes.GetHeader(signature['entete']) != signature['sentinelle']:
                continue
            valeur = lire_cle(signature['fournisseur'])
            if not valeur:
                return ''                  # /logout est passé par là
            entetes.SetHeader(signature['entete'],
                              signature['prefixe'] + valeur)
            return signature['fournisseur']
        except Exception:
            # Un fournisseur qui échoue ne doit pas priver les autres de leur
            # signature : chacun est gardé pour lui-même.
            _log.exception('signature %s', signature['fournisseur'])
    return ''
