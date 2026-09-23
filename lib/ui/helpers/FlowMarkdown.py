# -*- coding: utf-8 -*-
"""Markdown analysé → ``FlowDocument``, pour les bulles du chat.

Un ``TextBox`` ne sait afficher que du texte brut : il rendait « **gras** »
avec ses astérisques. Un ``TextBlock`` saurait mettre en forme mais ne se
sélectionne pas sous WPF, et les bulles doivent rester copiables — d'où le
``RichTextBox`` en lecture seule, qui sait faire les deux.

L'analyse vit dans ``core.markdown_simple`` (pure, testable) ; ici on ne fait
qu'assembler des objets WPF. ``document()`` renvoie ``None`` hors .NET.
"""
from __future__ import unicode_literals

try:
    from ui.helpers.wpf_runtime import ensure_wpf as _ensure_wpf
    _ensure_wpf()
except Exception:
    try:
        from lib.ui.helpers.wpf_runtime import ensure_wpf as _ensure_wpf
        _ensure_wpf()
    except Exception:
        pass

try:
    from core import markdown_simple as md
except Exception:
    from lib.core import markdown_simple as md

try:
    from System.Windows import Thickness, FontWeights, FontStyles
    from System.Windows.Documents import FlowDocument, Paragraph, Run
except Exception:
    FlowDocument = None

# Retrait des listes, et espace entre blocs. Assez serré pour qu'une bulle de
# trois lignes n'occupe pas un écran.
_RETRAIT = 14
_ENTRE_BLOCS = 4

# Le corps vient du RichTextBox ; seuls les titres s'en écartent, et de peu :
# une bulle de chat n'est pas un document.
_TAILLE_TITRE = {1: 1.30, 2: 1.18, 3: 1.08}


def document(texte):
    """``FlowDocument`` prêt à poser dans un RichTextBox, ``None`` hors .NET."""
    if FlowDocument is None:
        return None
    doc = FlowDocument()
    # Sans ça, WPF ajoute une marge d'impression et découpe en colonnes dès
    # que la bulle s'élargit.
    doc.PagePadding = Thickness(0)
    doc.ColumnWidth = 1e9
    for genre, niveau, parts in md.blocs(texte):
        doc.Blocks.Add(_paragraphe(genre, niveau, parts))
    return doc


def _paragraphe(genre, niveau, parts):
    para = Paragraph()
    para.Margin = Thickness(0, 0, 0, _ENTRE_BLOCS)
    if genre == md.PUCE:
        para.Margin = Thickness(_RETRAIT, 0, 0, _ENTRE_BLOCS)
        para.TextIndent = -_RETRAIT
        para.Inlines.Add(_morceau(md.BRUT, '• '))
    elif genre == md.NUMERO:
        para.Margin = Thickness(_RETRAIT, 0, 0, _ENTRE_BLOCS)
        para.TextIndent = -_RETRAIT
    elif genre == md.TITRE:
        para.FontWeight = FontWeights.Bold
        para.FontSize = _taille_titre(niveau)
    elif genre == md.BLOC_CODE:
        para.Margin = Thickness(_RETRAIT, 0, 0, 0)
    for style, contenu in parts:
        para.Inlines.Add(_morceau(style, contenu))
    return para


def _taille_titre(niveau):
    # FontSize est absolu dans un FlowDocument : pas d'héritage relatif ici,
    # on part de la taille des bulles (12, cf. le style BulleRiche).
    return 12.0 * _TAILLE_TITRE.get(niveau, 1.0)


def _morceau(style, contenu):
    morceau = Run(contenu)
    if style == md.GRAS:
        morceau.FontWeight = FontWeights.Bold
    elif style == md.ITAL:
        morceau.FontStyle = FontStyles.Italic
    elif style == md.CODE and _MONO is not None:
        morceau.FontFamily = _MONO
    return morceau


def _police_mono():
    try:
        from System.Windows.Media import FontFamily
        return FontFamily('Consolas, Courier New, monospace')
    except Exception:
        return None


_MONO = _police_mono()
