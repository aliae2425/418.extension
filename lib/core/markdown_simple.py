# -*- coding: utf-8 -*-
"""Markdown minimal : ce qu'un modèle écrit vraiment dans une bulle de chat.

Ni un parseur complet, ni une dépendance à installer — gras, italique, code,
listes et titres. Le reste passe en texte tel quel : mieux vaut afficher un
``[lien](url)`` littéral que de rater une réponse.

Analyse PURE (aucun WPF, aucun Revit) : elle se teste hors Revit, et c'est
``ui.helpers.FlowMarkdown`` qui en fait un document affichable.
"""
from __future__ import unicode_literals
import re

# Styles d'un morceau de ligne.
BRUT = ''
GRAS = 'gras'
ITAL = 'ital'
CODE = 'code'

# Genres de bloc.
PARAGRAPHE = 'p'
PUCE = 'puce'
NUMERO = 'numero'
TITRE = 'titre'
BLOC_CODE = 'bloc_code'

_PUCE = re.compile(r'^\s*[-*+]\s+(.*)$')
_NUMERO = re.compile(r'^\s*(\d+)[.)]\s+(.*)$')
_TITRE = re.compile(r'^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$')
_CLOTURE = re.compile(r'^\s*```')

# Un seul passage, alternatives ordonnées : ``**`` doit gagner sur ``*``,
# sinon « **gras** » se lit comme un italique vide suivi d'un astérisque.
#
# Les ``_`` collés à un mot ne marquent rien : sans ces bornes,
# « revit_list_views » affiche « list » en italique — et le modèle cite les
# noms d'outils à chaque réponse. C'est aussi la règle de CommonMark.
_MORCEAUX = re.compile(
    r'(`[^`\n]+`'
    r'|\*\*(?:[^*\n]|\*(?!\*))+\*\*'
    r'|(?<!\w)__(?:[^_\n]|_(?!_))+__(?!\w)'
    r'|\*[^*\n]+\*'
    r'|(?<!\w)_[^_\n]+_(?!\w))')


def morceaux(ligne):
    """Ligne → liste de ``(style, texte)``. Jamais vide pour une ligne pleine."""
    sortie = []
    for part in _MORCEAUX.split(ligne):
        if not part:
            continue
        sortie.append((_style(part), _nu(part)))
    return sortie


def _style(part):
    if part.startswith('`') and part.endswith('`'):
        return CODE
    if ((part.startswith('**') and part.endswith('**')) or
            (part.startswith('__') and part.endswith('__'))):
        return GRAS
    if ((part.startswith('*') and part.endswith('*')) or
            (part.startswith('_') and part.endswith('_'))):
        return ITAL
    return BRUT


def _nu(part):
    for marque in ('**', '__', '`', '*', '_'):
        if (part.startswith(marque) and part.endswith(marque) and
                len(part) > 2 * len(marque)):
            return part[len(marque):-len(marque)]
    return part


def blocs(texte):
    """Texte → liste de ``(genre, niveau, morceaux)``.

    ``niveau`` ne sert qu'aux titres (1 à 6) ; il vaut 0 ailleurs. Les lignes
    vides disparaissent : l'espacement est une affaire de mise en page, pas de
    contenu.
    """
    sortie = []
    dans_code = False
    for ligne in (texte or '').splitlines():
        if _CLOTURE.match(ligne):
            # La clôture ouvre ou ferme ; dans les deux cas elle ne s'affiche
            # pas. Un bloc laissé ouvert se referme à la fin du texte.
            dans_code = not dans_code
            continue
        if dans_code:
            sortie.append((BLOC_CODE, 0, [(CODE, ligne)]))
            continue
        if not ligne.strip():
            continue
        sortie.append(_bloc(ligne))
    return sortie


def _bloc(ligne):
    titre = _TITRE.match(ligne)
    if titre:
        return (TITRE, len(titre.group(1)), morceaux(titre.group(2)))
    puce = _PUCE.match(ligne)
    if puce:
        return (PUCE, 0, morceaux(puce.group(1)))
    numero = _NUMERO.match(ligne)
    if numero:
        return (NUMERO, 0,
                [(BRUT, numero.group(1) + '. ')] + morceaux(numero.group(2)))
    return (PARAGRAPHE, 0, morceaux(ligne.strip()))


def texte_nu(texte):
    """Le même contenu, marques retirées. Utile hors WPF et pour les tests."""
    lignes = []
    for genre, _niveau, parts in blocs(texte):
        plat = ''.join(contenu for _style_, contenu in parts)
        lignes.append('• ' + plat if genre == PUCE else plat)
    return '\n'.join(lignes)
