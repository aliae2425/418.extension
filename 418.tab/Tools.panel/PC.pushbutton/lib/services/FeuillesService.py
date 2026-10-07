# -*- coding: utf-8 -*-
"""Les feuilles et les jeux d'un dossier d'urbanisme, créés DANS la maquette.

Deux moitiés, et la séparation est la raison d'être du fichier :

- ``planifier()`` est **pure**. Elle décide ce qui doit exister — numéros,
  noms, jeux, et ce qui est déjà là — sans toucher à Revit. C'est elle qui
  alimente l'aperçu, et c'est elle qu'on teste.
- ``creer()`` est la glu Revit. Elle n'invente rien : elle exécute le plan
  que l'aperçu a montré, dans UNE transaction.

Un aperçu qui diverge de l'action ne vaut rien. Ici les deux lisent le même
plan, pas deux calculs qui se ressemblent.
"""
from __future__ import unicode_literals
import collections

try:
    from core.sanitize import sanitize_revit_name
except Exception:
    from lib.core.sanitize import sanitize_revit_name

try:
    from Autodesk.Revit.DB import (ViewSheet, Viewport, ViewSet, PrintRange,
                                   ElementId, XYZ)
except Exception:
    ViewSheet = None
    Viewport = None
    ViewSet = None
    PrintRange = None
    ElementId = None
    XYZ = None


# `vue` : l'identifiant opaque d'une vue à poser (un ElementId en vrai), ou
# None quand la pièce n'est alimentée par aucune vue. `vue_nom` ne sert QU'À
# l'aperçu — savoir laquelle des trois coupes atterrit sur PC3.2 — et ne
# touche jamais le nom de la feuille. `existe` : une feuille porte déjà ce
# numéro, on n'y touchera pas.
Feuille = collections.namedtuple('Feuille', 'numero nom vue vue_nom existe')
Jeu = collections.namedtuple('Jeu', 'nom feuilles existe')
Plan = collections.namedtuple('Plan', 'jeux')

SEPARATEUR = ' - '


def nom_jeu(piece):
    """« PC3 - Plan en coupe du terrain ». Le code en tête : c'est lui qui
    ordonne la liste des jeux dans Revit."""
    return sanitize_revit_name(
        u'{0}{1}{2}'.format(piece.code, SEPARATEUR, piece.libelle))


def planifier(attributions, numeros_existants=(), jeux_existants=()):
    """Ce qu'il faut créer. Ne touche à rien.

    ``attributions`` : liste de ``(piece, [(vue, nom_de_vue), …])`` — les
    vues du projet qui alimentent cette pièce et n'ont pas encore de feuille.

    Le numéro suit le besoin : une seule feuille porte le code nu (« PC3 »),
    plusieurs se suffixent (« PC3.1 »). Une pièce sans vue reçoit quand même
    SA feuille — une notice se dépose sur une feuille comme le reste.

    **Le NOM d'une feuille est toujours l'intitulé de la pièce**, jamais
    celui de la vue posée dessus. C'est un titre contractuel : l'instructeur
    cherche « Plan en coupe du terrain et de la construction », pas
    « Coupe AA ». Trois feuilles de PC3 portent donc le même nom et se
    distinguent par leur numéro — ce qui est exactement la lecture du
    bordereau.
    """
    numeros = set(numeros_existants or ())
    jeux = set(jeux_existants or ())
    sortie = []
    for piece, vues in attributions:
        sortie.append(Jeu(nom=nom_jeu(piece),
                          feuilles=tuple(_feuilles(piece, vues, numeros)),
                          existe=nom_jeu(piece) in jeux))
    return Plan(jeux=tuple(sortie))


def _feuilles(piece, vues, numeros):
    vues = list(vues or [])
    if not vues:
        # Aucune vue ne l'alimente : une feuille nue, à remplir à la main.
        yield _feuille(piece.code, piece.libelle, None, u'', numeros)
        return
    unique = len(vues) == 1
    for rang, (vue, nom_vue) in enumerate(vues, start=1):
        numero = piece.code if unique else u'{0}.{1}'.format(piece.code, rang)
        yield _feuille(numero, piece.libelle, vue, nom_vue, numeros)


def _feuille(numero, nom, vue, vue_nom, numeros):
    numero = sanitize_revit_name(numero)
    # Le numéro de feuille est unique dans Revit : s'il est pris, on ne
    # touche pas à l'existant — on le signale, et l'aperçu le dira.
    existe = numero in numeros
    if not existe:
        numeros.add(numero)
    return Feuille(numero=numero, nom=sanitize_revit_name(nom), vue=vue,
                   vue_nom=vue_nom or u'', existe=existe)


def a_creer(plan):
    """Les feuilles que ``creer()`` va réellement poser."""
    return [f for jeu in plan.jeux for f in jeu.feuilles if not f.existe]


def resume(crees, ignores, jeux, echecs):
    morceaux = []
    if crees:
        morceaux.append(u'{0} feuille(s) créée(s)'.format(crees))
    if jeux:
        morceaux.append(u'{0} jeu(x)'.format(jeux))
    if ignores:
        morceaux.append(u'{0} déjà là'.format(ignores))
    if echecs:
        morceaux.append(u'{0} en échec — {1}'.format(len(echecs), echecs[0]))
    return u', '.join(morceaux) if morceaux else u'Rien à créer.'


# --- glu Revit ------------------------------------------------------------

def creer(doc, plan, cartouche=None):
    """Exécute le plan dans la maquette. Rend ``(feuilles, jeux, échecs)``.

    À appeler DANS une transaction : c'est l'appelant qui la tient, pour que
    tout le dossier se défasse d'un seul Ctrl+Z.

    Ne lève pas sur une pièce : un cartouche refusé, un nom déjà pris par un
    jeu, et c'est le reste du dossier qui serait perdu. On compte, on
    continue, et on rend ce qui a manqué.
    """
    if ViewSheet is None:
        return 0, 0, [u'hors Revit']
    feuilles, jeux, echecs = 0, 0, []
    for jeu in plan.jeux:
        posees = []
        for feuille in jeu.feuilles:
            if feuille.existe:
                continue
            try:
                posees.append(_poser_feuille(doc, feuille, cartouche))
                feuilles += 1
            except Exception as e:
                echecs.append(u'{0} : {1}'.format(feuille.numero, e))
        if jeu.existe or not posees:
            continue
        try:
            _creer_jeu(doc, jeu.nom, posees)
            jeux += 1
        except Exception as e:
            echecs.append(u'jeu {0} : {1}'.format(jeu.nom, e))
    return feuilles, jeux, echecs


def _poser_feuille(doc, feuille, cartouche):
    """Crée la feuille, la nomme, et y pose sa vue s'il y en a une."""
    identifiant = cartouche if cartouche is not None else ElementId.InvalidElementId
    nouvelle = ViewSheet.Create(doc, identifiant)
    # Le numéro AVANT le nom : s'il est refusé (doublon créé entre-temps),
    # autant que la feuille ne porte pas déjà un nom qui ment.
    nouvelle.SheetNumber = feuille.numero
    nouvelle.Name = feuille.nom
    if feuille.vue is not None:
        _poser_vue(doc, nouvelle, feuille.vue)
    return nouvelle


def _poser_vue(doc, feuille, vue):
    """Centre la vue sur la feuille. Un échec ici ne perd pas la feuille."""
    try:
        if not Viewport.CanAddViewToSheet(doc, feuille.Id, vue):
            return
        Viewport.Create(doc, feuille.Id, vue, _centre(feuille))
    except Exception:
        pass


def _centre(feuille):
    """Le milieu du cartouche, en coordonnées de feuille."""
    try:
        contour = feuille.Outline
        return XYZ((contour.Min.U + contour.Max.U) / 2.0,
                   (contour.Min.V + contour.Max.V) / 2.0, 0.0)
    except Exception:
        return XYZ(0, 0, 0)


def _creer_jeu(doc, nom, feuilles):
    """Un `ViewSheetSet` ne se crée pas directement : il passe par le
    gestionnaire d'impression, qui enregistre la sélection courante sous un
    nom. C'est l'API, aussi détournée qu'elle paraisse."""
    gestionnaire = doc.PrintManager
    gestionnaire.PrintRange = PrintRange.Select
    reglage = gestionnaire.ViewSheetSetting
    ensemble = ViewSet()
    for feuille in feuilles:
        ensemble.Insert(feuille)
    reglage.CurrentViewSheetSet.Views = ensemble
    reglage.SaveAs(nom)
