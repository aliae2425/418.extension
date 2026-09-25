# -*- coding: utf-8 -*-
"""Markdown analysé → ``FlowDocument``, pour les bulles du chat.

Un ``TextBox`` n'affiche que du texte brut ; un ``TextBlock`` met en forme
mais ne se sélectionne pas sous WPF. Les bulles doivent faire les deux, d'où
le ``RichTextBox`` en lecture seule.

**Ce qui a fait tomber Revit la première fois, et comment on s'en garde** :
``RichTextBox.Document`` REFUSE ``null``. Une liaison vers une propriété qui
peut valoir ``None`` lève pendant l'inflation du DataTemplate, l'exception
remonte en ``XamlParseException`` et le process meurt. Deux verrous depuis :

1. ``document()`` ne rend jamais ``None`` quand WPF est là — un document vide
   plutôt que rien ;
2. le XAML ne montre le ``RichTextBox`` que si ``MiseEnForme`` est vrai, via
   un ``ContentControl`` qui change de gabarit — le contrôle n'est même pas
   construit dans l'autre cas.

L'analyse vit dans ``core.markdown_simple`` (pure, testable) ; ici on ne fait
qu'assembler des objets WPF.
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
    from System.Windows import Thickness, FontWeights, FontStyles, TextAlignment
    from System.Windows.Documents import (FlowDocument, Paragraph, Run, Table,
                                          TableColumn, TableRowGroup, TableRow,
                                          TableCell)
    from System.Windows.Media import FontFamily
except Exception:
    FlowDocument = None

_RETRAIT = 14
_ENTRE_BLOCS = 4
_TAILLE = 12.0
_TAILLE_TITRE = {1: 1.30, 2: 1.18, 3: 1.08}


def disponible():
    """WPF est-il là pour construire un document ? Le XAML s'y fie."""
    return FlowDocument is not None


def document(texte):
    """``FlowDocument`` prêt pour un RichTextBox. ``None`` seulement hors .NET.

    Ne lève jamais : une bulle sans mise en forme vaut mieux qu'un volet mort.
    """
    if FlowDocument is None:
        return None
    try:
        return _bati(texte)
    except Exception:
        # Repli : le texte nu dans un document valide. Rendre None ici
        # ferait lever la liaison, et c'est ce qui a tué Revit.
        try:
            secours = _vide()
            secours.Blocks.Add(_paragraphe_simple(md.texte_nu(texte)))
            return secours
        except Exception:
            return _vide()


def _vide():
    doc = FlowDocument()
    # Sans ça, WPF ajoute une marge d'impression et découpe en colonnes.
    doc.PagePadding = Thickness(0)
    doc.FontSize = _TAILLE
    return doc


def _bati(texte):
    doc = _vide()
    for genre, niveau, parts in md.blocs(texte):
        if genre == md.TABLEAU:
            doc.Blocks.Add(_tableau(parts))
        else:
            doc.Blocks.Add(_paragraphe(genre, niveau, parts))
    return doc


def _paragraphe_simple(texte):
    para = Paragraph()
    para.Margin = Thickness(0)
    para.Inlines.Add(Run(texte or ''))
    return para


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
        para.FontSize = _TAILLE * _TAILLE_TITRE.get(niveau, 1.0)
    elif genre == md.BLOC_CODE:
        para.Margin = Thickness(_RETRAIT, 0, 0, 0)
    for style, contenu in parts:
        para.Inlines.Add(_morceau(style, contenu))
    return para


def _tableau(rangees):
    """Un vrai ``Table`` : les colonnes s'alignent et le texte se replie.

    La première rangée sert d'en-tête — c'est la convention Markdown, et la
    ligne « |---| » qui l'annonce a déjà été écartée par l'analyse.
    """
    table = Table()
    table.CellSpacing = 0
    table.Margin = Thickness(0, 0, 0, _ENTRE_BLOCS)
    largeur = max(len(rangee) for rangee in rangees)
    for _ in range(largeur):
        table.Columns.Add(TableColumn())
    groupe = TableRowGroup()
    for rang, rangee in enumerate(rangees):
        ligne = TableRow()
        if rang == 0:
            ligne.FontWeight = FontWeights.Bold
        for cellule in rangee:
            ligne.Cells.Add(_cellule(cellule))
        # Une rangée plus courte que les autres laisserait un trou : WPF
        # décale alors toutes les colonnes suivantes.
        for _ in range(largeur - len(rangee)):
            ligne.Cells.Add(_cellule([(md.BRUT, '')]))
        groupe.Rows.Add(ligne)
    table.RowGroups.Add(groupe)
    return table


def _cellule(parts):
    para = Paragraph()
    para.Margin = Thickness(0)
    para.TextAlignment = TextAlignment.Left
    for style, contenu in parts:
        para.Inlines.Add(_morceau(style, contenu))
    cellule = TableCell(para)
    cellule.Padding = Thickness(0, 1, 8, 1)
    return cellule


def _morceau(style, contenu):
    morceau = Run(contenu)
    if style == md.GRAS:
        morceau.FontWeight = FontWeights.Bold
    elif style == md.ITAL:
        morceau.FontStyle = FontStyles.Italic
    elif style == md.SOULIGNE:
        morceau.TextDecorations = _souligne()
    elif style == md.CODE and _MONO is not None:
        morceau.FontFamily = _MONO
    return morceau


def _souligne():
    from System.Windows import TextDecorations
    return TextDecorations.Underline


def _police_mono():
    try:
        return FontFamily('Consolas, Courier New, monospace')
    except Exception:
        return None


_MONO = _police_mono() if FlowDocument is not None else None
