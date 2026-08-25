# -*- coding: utf-8 -*-
"""Importe un fichier SVG dans la vue active sous forme de lignes de détail.

Revit ne sait pas lire le SVG. Le trajet est : `xml.etree` lit le fichier,
WPF (`Geometry.Parse`) comprend déjà la syntaxe des chemins SVG et aplatit
courbes de Bézier et arcs, puis chaque polyligne devient un `DetailCurve`
dans la vue. Aucune dépendance, aucun fichier intermédiaire.

Seuls les contours sont importés : les remplissages (`fill`) et les textes
sont ignorés. La largeur demandée est une largeur *dans le modèle* — sur une
feuille, elle apparaîtra divisée par l'échelle de la vue.
"""
from __future__ import unicode_literals, division

__title__ = "Importer\nSVG"
__doc__ = "Importe un fichier SVG dans la vue active en lignes de détail."
__author__ = 'Aliae'
__min_revit_ver__ = 2026

import sys

import clr
clr.AddReference('WindowsBase')
clr.AddReference('PresentationCore')
from System.Windows.Media import (Geometry, ToleranceType,
                                  PolyLineSegment, LineSegment)

from Autodesk.Revit.DB import Line, ViewType
from Autodesk.Revit.Exceptions import OperationCanceledException
from pyrevit import forms

try:
    from core.transaction import revit_transaction
except ImportError:
    from lib.core.transaction import revit_transaction

from lib.svg_paths import lire_svg, appliquer

try:
    uidoc = __revit__.ActiveUIDocument  # type: ignore
    doc = uidoc.Document
except Exception:
    uidoc = None
    doc = None

# Écart de corde maximal de l'aplatissement des courbes, en mm dans la vue.
TOLERANCE_MM = 0.15
# Au-delà, Revit devient pénible à manipuler : on demande confirmation.
SEUIL_CONFIRMATION = 5000
MM_PAR_PIED = 304.8

# Vues 2D qui acceptent des lignes de détail.
VUES_VALIDES = (ViewType.FloorPlan, ViewType.CeilingPlan, ViewType.AreaPlan,
                ViewType.EngineeringPlan, ViewType.Section, ViewType.Elevation,
                ViewType.Detail, ViewType.DraftingView)


def bornes_svg(traces):
    """(min_x, min_y, max_x, max_y) de tous les tracés, en unités SVG.

    Utilise `Geometry.Bounds` (sans aplatissement) : assez précis pour
    calculer l'échelle, et disponible avant de connaître la tolérance.
    """
    xs, ys = [], []
    for chemin, matrice in traces:
        rect = Geometry.Parse(chemin).Bounds
        if rect.IsEmpty:
            continue
        for cx, cy in ((rect.Left, rect.Top), (rect.Right, rect.Top),
                       (rect.Right, rect.Bottom), (rect.Left, rect.Bottom)):
            x, y = appliquer(matrice, cx, cy)
            xs.append(x)
            ys.append(y)
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def polylignes(chemin, tolerance):
    """Aplatit un tracé SVG en listes de points 2D (coordonnées SVG locales)."""
    geo = Geometry.Parse(chemin).GetFlattenedPathGeometry(
        tolerance, ToleranceType.Absolute)
    for figure in geo.Figures:
        points = [(figure.StartPoint.X, figure.StartPoint.Y)]
        for segment in figure.Segments:
            if isinstance(segment, PolyLineSegment):
                points.extend((p.X, p.Y) for p in segment.Points)
            elif isinstance(segment, LineSegment):
                points.append((segment.Point.X, segment.Point.Y))
        if figure.IsClosed:
            points.append(points[0])
        yield points


def construire_lignes(traces, tolerance, vers_revit, mini):
    """Convertit les tracés en `Line` Revit.

    Retourne (lignes, nombre_de_segments_écartés) : un segment plus court que
    `mini` (ShortCurveTolerance) est refusé par Revit, on l'absorbe dans le
    suivant en conservant l'ancre.
    """
    lignes = []
    ecartes = 0
    for chemin, matrice in traces:
        for points in polylignes(chemin, tolerance):
            ancre = None
            for x, y in points:
                point = vers_revit(*appliquer(matrice, x, y))
                if ancre is None:
                    ancre = point
                elif ancre.DistanceTo(point) >= mini:
                    lignes.append(Line.CreateBound(ancre, point))
                    ancre = point
                else:
                    ecartes += 1
    return lignes, ecartes


if __name__ == '__main__':
    vue = doc.ActiveView
    print('[ImportSVG] document {0} | vue « {1} » ({2}) | échelle 1:{3}'.format(
        'famille' if doc.IsFamilyDocument else 'projet',
        vue.Name, vue.ViewType, vue.Scale))
    if vue.ViewType not in VUES_VALIDES:
        forms.alert("La vue active n'accepte pas de lignes de détail.\n"
                    "Ouvrir un plan, une coupe, une élévation ou une vue "
                    "de dessin.", title='Importer SVG', exitscript=True)

    fichier = forms.pick_file(file_ext='svg', title='Choisir un fichier SVG')
    if not fichier:
        sys.exit()

    try:
        traces = lire_svg(fichier)
    except Exception as erreur:
        forms.alert('Fichier SVG illisible :\n{0}'.format(erreur),
                    title='Importer SVG', exitscript=True)

    print('[ImportSVG] {0}'.format(fichier))
    print('[ImportSVG] {0} tracé(s) lu(s)'.format(len(traces)))

    bornes = bornes_svg(traces) if traces else None
    if not bornes or bornes[2] - bornes[0] <= 0:
        forms.alert('Aucun tracé exploitable dans ce SVG.\n'
                    "Les textes et les images intégrées ne sont pas importés.",
                    title='Importer SVG', exitscript=True)

    saisie = forms.ask_for_string(
        default='100',
        prompt='Largeur cible dans le modèle (mm) :',
        title='Importer SVG')
    try:
        largeur_mm = float((saisie or '').replace(',', '.'))
    except ValueError:
        largeur_mm = 0.0
    if largeur_mm <= 0:
        forms.alert('Largeur invalide : « {0} ». Import annulé.'.format(saisie),
                    title='Importer SVG', exitscript=True)

    min_x, min_y, max_x, max_y = bornes
    # Pieds par unité SVG : la largeur dessinée vaut exactement la demande.
    echelle = (largeur_mm / MM_PAR_PIED) / (max_x - min_x)
    tolerance = TOLERANCE_MM / MM_PAR_PIED / echelle
    print('[ImportSVG] bornes SVG : x {0:.2f} → {1:.2f} | y {2:.2f} → {3:.2f}'
          .format(min_x, max_x, min_y, max_y))
    print('[ImportSVG] échelle {0:.8f} pied/unité | tolérance {1:.4f} unité'
          .format(echelle, tolerance))
    print('[ImportSVG] taille visée {0:.1f} × {1:.1f} mm'.format(
        largeur_mm, largeur_mm * (max_y - min_y) / (max_x - min_x)))

    # PickPoint bloque en attendant un clic DANS la vue Revit ; la seule
    # indication est la barre d'état, d'où le message explicite ici.
    print('[ImportSVG] Cliquer le point d\'insertion dans la vue « {0} » '
          '(coin haut-gauche du SVG).'.format(vue.Name))
    try:
        origine = uidoc.Selection.PickPoint(
            "Point d'insertion du SVG (coin haut-gauche)")
    except OperationCanceledException:
        print('[ImportSVG] Annulé : aucun point sélectionné.')
        sys.exit()
    except Exception as erreur:
        forms.alert("Impossible de choisir un point dans cette vue :\n"
                    '{0} : {1}'.format(type(erreur).__name__, erreur),
                    title='Importer SVG', exitscript=True)

    print('[ImportSVG] Insertion en {0}'.format(origine))
    droite, haut = vue.RightDirection, vue.UpDirection

    def vers_revit(x, y):
        """Point SVG -> XYZ dans le plan de la vue (Y du SVG pointe en bas)."""
        return (origine + droite * ((x - min_x) * echelle)
                - haut * ((y - min_y) * echelle))

    mini = doc.Application.ShortCurveTolerance
    lignes, ecartes = construire_lignes(traces, tolerance, vers_revit, mini)

    print('[ImportSVG] {0} ligne(s) à créer | {1} segment(s) écarté(s) '
          '(< {2:.3f} mm)'.format(len(lignes), ecartes, mini * MM_PAR_PIED))
    if not lignes:
        forms.alert('Aucune ligne à créer : le SVG est peut-être vide ou '
                    'la largeur demandée est trop petite.',
                    title='Importer SVG', exitscript=True)

    longueurs = sorted(ligne.Length * MM_PAR_PIED for ligne in lignes)
    print('[ImportSVG] longueurs : min {0:.3f} | médiane {1:.3f} | '
          'max {2:.3f} mm'.format(longueurs[0],
                                  longueurs[len(longueurs) // 2],
                                  longueurs[-1]))
    coins = (vers_revit(min_x, min_y), vers_revit(max_x, max_y))
    print('[ImportSVG] étendue modèle : {0} → {1}'.format(*coins))

    if len(lignes) > SEUIL_CONFIRMATION and not forms.alert(
            '{0} lignes de détail vont être créées. '
            'Revit risque de devenir lent.\nContinuer ?'.format(len(lignes)),
            title='Importer SVG', yes=True, no=True):
        print('[ImportSVG] Annulé par l\'utilisateur.')
        sys.exit()

    # ponytail: création une par une plutôt que NewDetailCurveArray. Plus lent,
    # mais un refus isolé de Revit ne fait plus échouer tout l'import et on sait
    # QUELLE courbe pose problème. Repasser au lot si la lenteur devient gênante.
    # En famille, `doc.Create` est un FamilyItemFactory : fabrique différente.
    fabrique = doc.FamilyCreate if doc.IsFamilyDocument else doc.Create
    print('[ImportSVG] fabrique : {0}'.format(type(fabrique).__name__))

    crees, echecs, premiere_erreur = 0, 0, None
    try:
        with revit_transaction(doc, 'Importer SVG'):
            for index, ligne in enumerate(lignes):
                try:
                    fabrique.NewDetailCurve(vue, ligne)
                    crees += 1
                except Exception as erreur:
                    echecs += 1
                    if premiere_erreur is None:
                        premiere_erreur = (
                            '#{0} ({1:.3f} mm, {2} → {3}) : {4} : {5}'.format(
                                index, ligne.Length * MM_PAR_PIED,
                                ligne.GetEndPoint(0), ligne.GetEndPoint(1),
                                type(erreur).__name__, erreur))
    except Exception:
        import traceback
        print('[ImportSVG] ÉCHEC de la transaction :')
        print(traceback.format_exc())
        raise

    if premiere_erreur:
        print('[ImportSVG] {0} refus de Revit. Premier : {1}'.format(
            echecs, premiere_erreur))
    print('[ImportSVG] {0} ligne(s) de détail créée(s) dans « {1} » '
          'depuis {2}'.format(crees, vue.Name, fichier))
    if not crees:
        forms.alert('Revit a refusé les {0} lignes.\nVoir la console pyRevit '
                    'pour le détail.'.format(echecs), title='Importer SVG')
        sys.exit()

    # Un SVG de 100 mm placé à l'origine est invisible dans une vue zoomée sur
    # un bâtiment : on cadre dessus pour que le résultat soit visible.
    try:
        for ui_vue in uidoc.GetOpenUIViews():
            if ui_vue.ViewId == vue.Id:
                ui_vue.ZoomAndCenterRectangle(coins[0], coins[1])
                break
    except Exception as erreur:
        print('[ImportSVG] Zoom impossible ({0}), cadrer à la main sur {1}.'
              .format(type(erreur).__name__, coins[0]))
