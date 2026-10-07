# -*- coding: utf-8 -*-
"""Les pièces d'un dossier d'urbanisme. **De la donnée, pas du code.**

Les intitulés sont recopiés des fiches service-public.gouv.fr (N319) :
F17578 pour la déclaration préalable, F1986 pour le permis de construire,
F17669 pour le permis de démolir — consultées le 2026-10-07. Les codes
(DP1, PC1…) sont ceux du bordereau de dépôt des pièces jointes du CERFA.

**Ce fichier se complète sans toucher au reste.** Les pièces complémentaires
— attestation RE2020, notice d'accessibilité d'un ERP, études d'impact — ne
sont PAS ici : leur numéro de bordereau se lit sur la notice du CERFA de
votre projet, et une liste réglementaire inventée coûte plus cher qu'une
liste courte. Ajouter une ligne au bon tuple suffit, le reste suit.

**Un type dont le tuple de pièces est vide est grisé dans la fenêtre.** C'est
le même champ qui décide de l'affichage ET de l'aiguillage — l'idiome du
catalogue d'OpenArchi. Écrire les pièces du PCMI l'allume, sans un drapeau
de plus à tenir d'accord.

Logique pure (aucun Revit, aucun WPF) : testable hors Revit.
"""
from __future__ import unicode_literals
import collections

# `obligatoire` = exigée dans tous les cas par la fiche. Les autres dépendent
# du projet : elles sont proposées décochées, à l'architecte de juger.
#
# `vues` = les NOMS de ViewType qui alimentent la pièce. C'est ce qui permet
# d'analyser le projet au lieu de demander un nombre : trois coupes dans la
# maquette, trois feuilles pour PC3. Des noms et pas des membres
# d'énumération — ce fichier doit rester importable hors Revit, où
# `DB.ViewType` n'existe pas.
#
# Tuple vide = aucune vue ne l'alimente (une notice, une photo). La pièce
# reçoit alors UNE feuille, à remplir à la main.
Piece = collections.namedtuple('Piece', 'code libelle obligatoire vues')
Dossier = collections.namedtuple('Dossier', 'code libelle pieces')


def _p(code, libelle, obligatoire=False, vues=()):
    return Piece(code, libelle, obligatoire, tuple(vues))


# Les familles de vues, nommées une fois. Trois seulement sont lisibles sans
# se tromper : une coupe est une coupe, une façade est une élévation, une
# perspective est une 3D. Le plan de situation et le plan de masse, eux, sont
# des plans d'étage comme les autres — rien dans le modèle ne les distingue
# d'un plan de niveau, et deviner sur le nom de la vue serait un piège.
COUPES = ('Section',)
FACADES = ('Elevation',)
PERSPECTIVES = ('ThreeD',)

# Pas de constante pour les plans, et c'est délibéré : le plan de situation
# et le plan de masse sont des plans d'étage comme les autres. Les y rattacher
# ferait remonter TOUS les niveaux du projet dans une pièce qui en attend un.
# Ils reçoivent donc une feuille, et l'architecte y pose la bonne vue.


# --- Déclaration préalable (F17578) --------------------------------------
# Seul le plan de situation est exigé « pour tous les projets » ; le reste
# dépend de ce que les travaux touchent — volume, profil du terrain, façades.
DP = (
    _p('DP1', 'Plan de situation du terrain', obligatoire=True),
    _p('DP2', 'Plan de masse des constructions à édifier ou à modifier'),
    _p('DP3', 'Plan en coupe du terrain et de la construction', vues=COUPES),
    _p('DP4', 'Plan des façades et des toitures', vues=FACADES),
    _p('DP5', 'Représentation de l\'aspect extérieur de la construction',
       vues=PERSPECTIVES),
    _p('DP6', 'Document graphique d\'insertion dans l\'environnement',
       vues=PERSPECTIVES),
    _p('DP7', 'Photographie situant le terrain dans l\'environnement proche'),
    _p('DP8', 'Photographie situant le terrain dans le paysage lointain'),
    _p('DP11', 'Notice décrivant le terrain et présentant le projet'),
)

# --- Permis de construire (F1986) ----------------------------------------
# « Tous les demandeurs doivent fournir » les huit : contrairement à la DP,
# aucune n'est conditionnelle.
PC = (
    _p('PC1', 'Plan de situation du terrain', obligatoire=True),
    _p('PC2', 'Plan de masse des constructions à édifier ou à modifier',
       obligatoire=True),
    _p('PC3', 'Plan en coupe du terrain et de la construction',
       obligatoire=True, vues=COUPES),
    _p('PC4', 'Notice décrivant le terrain et présentant le projet',
       obligatoire=True),
    _p('PC5', 'Plan des façades et des toitures', obligatoire=True,
       vues=FACADES),
    _p('PC6', 'Document graphique d\'insertion dans l\'environnement',
       obligatoire=True, vues=PERSPECTIVES),
    _p('PC7', 'Photographie situant le terrain dans l\'environnement proche',
       obligatoire=True),
    _p('PC8', 'Photographie situant le terrain dans le paysage lointain',
       obligatoire=True),
)

# --- Permis de démolir (F17669) ------------------------------------------
PD = (
    _p('PD1', 'Plan de situation du terrain', obligatoire=True),
    _p('PD2', 'Plan de masse des constructions', obligatoire=True),
    _p('PD3', 'Photographie du ou des bâtiments à démolir', obligatoire=True),
)

# --- Le catalogue ---------------------------------------------------------
# PCMI et PA sont DÉCLARÉS mais sans pièces : ils s'affichent grisés, ce qui
# annonce ce qui arrive au lieu de le cacher. Les retirer d'ici les ferait
# disparaître de la fenêtre.
CATALOGUE = (
    Dossier('DP', 'Déclaration préalable', DP),
    Dossier('PCMI', 'PC maison individuelle', ()),
    Dossier('PC', 'Permis de construire', PC),
    Dossier('PA', 'Permis d\'aménager', ()),
    Dossier('PD', 'Permis de démolir', PD),
)


def dossier(code):
    """Le dossier de ce code, ``None`` s'il n'est pas au catalogue."""
    for entree in CATALOGUE:
        if entree.code == code:
            return entree
    return None


def actif(code):
    """Un type sans pièce n'est pas proposable : rien à générer."""
    entree = dossier(code)
    return bool(entree and entree.pieces)


def premier_actif():
    """Le type retenu par défaut à l'ouverture."""
    for entree in CATALOGUE:
        if entree.pieces:
            return entree.code
    return None


def pieces(code):
    entree = dossier(code)
    return entree.pieces if entree else ()


def obligatoires(code):
    """Les codes cochés d'office — ce que la fiche exige dans tous les cas."""
    return tuple(p.code for p in pieces(code) if p.obligatoire)
