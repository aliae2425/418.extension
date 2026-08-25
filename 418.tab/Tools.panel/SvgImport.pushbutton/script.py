# -*- coding: utf-8 -*-
"""Importe un fichier SVG dans la vue active, via un DXF intermédiaire.

Revit ne sait pas lire le SVG. Le trajet est : `xml.etree` lit le fichier,
WPF (`Geometry.Parse`) comprend déjà la syntaxe des chemins SVG et aplatit
courbes de Bézier et arcs, chaque figure devient une POLYLINE dans un DXF R12
temporaire, et `Document.Import` fait entrer le tout en UN appel.

Variante de `feat/svgImport`, qui créait un `DetailCurve` par segment : des
milliers d'appels API, donc lent, et un résultat en miettes. Ici l'import est
un objet unique — plus rapide et plus propre, mais à décomposer à la main
(sélection → Décomposer complètement) pour obtenir des lignes éditables :
l'API Revit n'expose aucune méthode d'explosion.

Seuls les contours sont importés : les remplissages (`fill`) et les textes
sont ignorés. La largeur demandée est une largeur *dans le modèle* — sur une
feuille, elle apparaîtra divisée par l'échelle de la vue.
"""
from __future__ import unicode_literals, division

__title__ = "Importer\nSVG"
__doc__ = "Importe un fichier SVG dans la vue active via un DXF temporaire."
__author__ = 'Aliae'
__min_revit_ver__ = 2026

import os
import sys
import tempfile
import time

import clr
clr.AddReference('WindowsBase')
clr.AddReference('PresentationCore')
from System.Windows.Media import (Geometry, ToleranceType,
                                  PolyLineSegment, LineSegment)

from Autodesk.Revit.DB import (DWGImportOptions, ElementTransformUtils,
                               ImportPlacement, ImportUnit, ViewType, XYZ)
from Autodesk.Revit.Exceptions import OperationCanceledException
from pyrevit import forms

try:
    from core.transaction import revit_transaction
except ImportError:
    from lib.core.transaction import revit_transaction

from lib import dxf
from lib.svg_paths import appliquer, cadrer, lire_svg
from lib.views.TailleSvgView import TailleSvgView

try:
    uidoc = __revit__.ActiveUIDocument  # type: ignore
    doc = uidoc.Document
except Exception:
    uidoc = None
    doc = None

# Écart de corde maximal de l'aplatissement des courbes, en mm dans la vue.
# C'est LE bouton de réglage de la finesse des courbes. Le coût d'un sommet de
# POLYLINE est très inférieur à celui d'une ligne de détail, donc on peut se
# permettre plus fin qu'avec l'autre méthode.
TOLERANCE_MM = 0.15

# Vues 2D qui acceptent un import CAD propre à la vue.
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
    """Aplatit un tracé SVG en (points 2D, fermée), coordonnées SVG locales.

    La fermeture est rendue par le drapeau et non en répétant le premier point :
    une POLYLINE DXF a un bit « fermée » (groupe 70).
    """
    geo = Geometry.Parse(chemin).GetFlattenedPathGeometry(
        tolerance, ToleranceType.Absolute)
    for figure in geo.Figures:
        points = [(figure.StartPoint.X, figure.StartPoint.Y)]
        for segment in figure.Segments:
            if isinstance(segment, PolyLineSegment):
                points.extend((p.X, p.Y) for p in segment.Points)
            elif isinstance(segment, LineSegment):
                points.append((segment.Point.X, segment.Point.Y))
        yield points, figure.IsClosed


# Deux sommets plus proches que ça (en mm) sont fusionnés : ils ne se voient
# pas et une POLYLINE à sommets confondus fait tiquer l'import de Revit.
FUSION_MM = 0.001


def construire_polylignes(traces, tolerance, vers_mm):
    """Convertit les tracés en polylignes millimétriques prêtes pour le DXF.

    Retourne (polylignes, sommets_fusionnés) où chaque polyligne est un couple
    (points, fermée).
    """
    resultat = []
    fusionnes = 0
    for chemin, matrice in traces:
        for points, fermee in polylignes(chemin, tolerance):
            propres = []
            for x, y in points:
                point = vers_mm(*appliquer(matrice, x, y))
                if propres and (abs(point[0] - propres[-1][0]) < FUSION_MM
                                and abs(point[1] - propres[-1][1]) < FUSION_MM):
                    fusionnes += 1
                    continue
                propres.append(point)
            if len(propres) >= 2:
                resultat.append((propres, fermee))
    return resultat, fusionnes


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

    min_x, min_y, max_x, max_y = bornes
    dialogue = TailleSvgView(
        defaut='100',
        info='Tracé source : {0:.0f} × {1:.0f} unités SVG, {2} tracé(s). '
             'Le ratio est conservé.'.format(
                 max_x - min_x, max_y - min_y, len(traces)))
    dialogue.show()
    if dialogue.valeur is None:
        print('[ImportSVG] Annulé : largeur non saisie.')
        sys.exit()

    try:
        largeur_mm = float(dialogue.valeur.replace(',', '.'))
    except ValueError:
        largeur_mm = 0.0
    if largeur_mm <= 0:
        forms.alert('Largeur invalide : « {0} ». Import annulé.'.format(
            dialogue.valeur), title='Importer SVG', exitscript=True)

    # Millimètres par unité SVG : la largeur dessinée vaut exactement la demande.
    # `vers_mm` recadre le coin haut-gauche en (0, 0) et retourne l'axe Y.
    echelle_mm, vers_mm = cadrer(bornes, largeur_mm)
    tolerance = TOLERANCE_MM / echelle_mm
    print('[ImportSVG] bornes SVG : x {0:.2f} → {1:.2f} | y {2:.2f} → {3:.2f}'
          .format(min_x, max_x, min_y, max_y))
    print('[ImportSVG] échelle {0:.6f} mm/unité | tolérance {1:.4f} unité'
          .format(echelle_mm, tolerance))
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

    # Le placement dans la vue est fait après import, en recalant la boîte
    # englobante sur le point cliqué.
    depart = time.time()
    polys, fusionnes = construire_polylignes(traces, tolerance, vers_mm)
    sommets = sum(len(points) for points, _ in polys)
    print('[ImportSVG] {0} polyligne(s), {1} sommet(s), {2} fusionné(s) | '
          'aplatissement {3:.1f} s'.format(
              len(polys), sommets, fusionnes, time.time() - depart))
    if not polys:
        forms.alert('Aucun tracé à importer : le SVG est peut-être vide ou '
                    'la largeur demandée est trop petite.',
                    title='Importer SVG', exitscript=True)

    dossier = tempfile.mkdtemp(prefix='svgimport_')
    chemin_dxf = os.path.join(
        dossier, os.path.splitext(os.path.basename(fichier))[0] + '.dxf')
    ecrites = dxf.ecrire(chemin_dxf, polys)
    print('[ImportSVG] DXF écrit : {0} entité(s), {1} Ko -> {2}'.format(
        ecrites, os.path.getsize(chemin_dxf) // 1024, chemin_dxf))

    options = DWGImportOptions()
    options.Unit = ImportUnit.Millimeter
    options.Placement = ImportPlacement.Origin
    options.ThisViewOnly = True      # équivalent « détail » : propre à la vue
    options.OrientToView = True

    depart = time.time()
    try:
        with revit_transaction(doc, 'Importer SVG'):
            resultat = doc.Import(chemin_dxf, options, vue)
            # `Import` a un paramètre `out ElementId` : selon le pont .NET il
            # revient en tuple (succès, id) ou directement en id.
            if isinstance(resultat, tuple):
                _, element_id = resultat
            else:
                element_id = resultat

            instance = doc.GetElement(element_id)
            if instance is None:
                raise RuntimeError(
                    'Import refusé par Revit (aucun élément créé).')

            # La bbox n'est renseignée qu'après régénération.
            doc.Regenerate()
            boite = instance.get_BoundingBox(vue)
            if boite is not None:
                # Recale le coin haut-gauche sur le point cliqué, où que Revit
                # ait déposé l'import.
                coin = XYZ(boite.Min.X, boite.Max.Y, boite.Min.Z)
                ElementTransformUtils.MoveElement(doc, element_id, origine - coin)
    except Exception:
        import traceback
        print('[ImportSVG] ÉCHEC de l\'import :')
        print(traceback.format_exc())
        raise
    finally:
        # Import (et non lien) : la géométrie est copiée dans le modèle, le
        # fichier temporaire ne sert plus à rien.
        try:
            os.remove(chemin_dxf)
            os.rmdir(dossier)
        except OSError:
            pass

    print('[ImportSVG] import : {0:.1f} s | élément {1}'.format(
        time.time() - depart, element_id))
    print('[ImportSVG] {0} entité(s) importée(s) dans « {1} » depuis {2}'
          .format(ecrites, vue.Name, fichier))
    print('[ImportSVG] Pour des lignes éditables : sélectionner l\'import '
          '-> Décomposer complètement (pas d\'API d\'explosion).')

    # Un tracé de 100 mm est invisible dans une vue zoomée sur un bâtiment.
    try:
        boite = doc.GetElement(element_id).get_BoundingBox(vue)
        for ui_vue in uidoc.GetOpenUIViews():
            if ui_vue.ViewId == vue.Id and boite is not None:
                ui_vue.ZoomAndCenterRectangle(boite.Min, boite.Max)
                break
    except Exception as erreur:
        print('[ImportSVG] Zoom impossible ({0}), cadrer à la main sur {1}.'
              .format(type(erreur).__name__, origine))
