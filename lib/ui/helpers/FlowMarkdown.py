# -*- coding: utf-8 -*-
"""Markdown analysé → ``FlowDocument``, pour les bulles du chat.

Un ``TextBox`` n'affiche que du texte brut ; un ``TextBlock`` met en forme
mais ne se sélectionne pas sous WPF. Les bulles doivent faire les deux, d'où
le ``RichTextBox`` en lecture seule.

**Trois plantages de Revit, et ce qu'on en retient.** Relus ensemble, ils
disent que la configuration la plus simple n'avait jamais été essayée :

- 1re : ``RichTextBox`` direct, ``Document`` pouvant valoir ``null`` — il
  refuse ``null``, la liaison lève, ``XamlParseException``, process mort ;
- 2e et 3e : un ``ContentControl`` qui bascule de gabarit par ``DataTrigger``
  et ``StaticResource``. Jamais élucidées — mais c'est la seule pièce que la
  1re n'avait pas.

D'où la forme d'aujourd'hui : **un seul gabarit, un ``RichTextBox`` direct,
et un ``Document`` qui n'est JAMAIS ``null``**. Pas de bascule, pas de
``ContentControl``. Et une surface WPF réduite au minimum : trois types.

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

# Surface WPF volontairement MINIMALE : FlowDocument, Paragraph, Run, et
# quatre assignations de propriété. Pas de Table, pas de TableCell, pas de
# TextAlignment — les tableaux sont rendus en colonnes de texte calées à
# l'espace. Chaque type WPF de plus est une façon de plus de tomber, et on
# est déjà tombés trois fois.
try:
    from System.Windows import Thickness, FontWeights, FontStyles
    from System.Windows.Documents import FlowDocument, Paragraph, Run
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


def document(texte, mise_en_forme=True):
    """``FlowDocument`` prêt pour un RichTextBox. ``None`` seulement hors .NET.

    **Ne rend JAMAIS None quand WPF est là.** C'est le contrat : la liaison
    du panneau pose cette valeur sur ``RichTextBox.Document``, qui refuse
    ``null`` — un None ici lève pendant l'inflation du DataTemplate et tue
    Revit. Trois replis en cascade plutôt qu'un seul.

    ``mise_en_forme`` à faux rend le texte en un seul paragraphe, sans
    analyse : c'est le mode de bissection de ``/format``.
    """
    if FlowDocument is None:
        return None
    if mise_en_forme:
        try:
            return _bati(texte)
        except Exception:
            pass                       # on tente plus simple juste en dessous
    try:
        secours = _vide()
        secours.Blocks.Add(_paragraphe_simple(md.texte_nu(texte)))
        return secours
    except Exception:
        return _vide()                 # vide mais valide : jamais None


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
            for para in _tableau(parts):
                doc.Blocks.Add(para)
        else:
            doc.Blocks.Add(_paragraphe(genre, niveau, parts))
    return doc


def _tableau(rangees):
    """Un tableau rendu en paragraphes calés à l'espace, PAS en ``Table``.

    Un vrai ``Table`` WPF, c'est cinq types de plus (Table, TableColumn,
    TableRowGroup, TableRow, TableCell) et un moteur de mise en page à part.
    Après trois plantages, la colonne alignée à l'espace en police fixe rend
    le même service pour un dixième de la surface exposée.
    """
    largeurs = _largeurs(rangees)
    paragraphes = []
    for rang, rangee in enumerate(rangees):
        para = Paragraph()
        para.Margin = Thickness(_RETRAIT, 0, 0, 0)
        if rang == 0:
            para.FontWeight = FontWeights.Bold
        for colonne, cellule in enumerate(rangee):
            plat = ''.join(contenu for _style, contenu in cellule)
            # Dernière colonne : pas de remplissage, sinon la bulle s'élargit
            # d'espaces invisibles.
            if colonne < len(rangee) - 1:
                plat = plat.ljust(largeurs[colonne] + 2)
            morceau = _morceau(md.CODE, plat)
            morceau.FontWeight = (FontWeights.Bold if rang == 0
                                  else FontWeights.Normal)
            para.Inlines.Add(morceau)
        paragraphes.append(para)
    return paragraphes


def _largeurs(rangees):
    largeurs = []
    for rangee in rangees:
        for colonne, cellule in enumerate(rangee):
            plat = ''.join(contenu for _style, contenu in cellule)
            if colonne >= len(largeurs):
                largeurs.append(len(plat))
            else:
                largeurs[colonne] = max(largeurs[colonne], len(plat))
    return largeurs


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
