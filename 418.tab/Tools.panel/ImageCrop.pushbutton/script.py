# -*- coding: utf-8 -*-
"""
Recadre une image importee selon une ou plusieurs zones de pochage.

Selectionner UNE image + une ou plusieurs regions remplies (ou lignes de
detail) qui delimitent les zones a conserver, puis lancer la commande.
Chaque zone produit un morceau d'image cale exactement dans son cadre.
L'image d'origine est conservee. Les zones de pochage sont conservees et,
une fois le crop resolu, affichees sans fond avec un cadre vert (override
graphique propre a la vue active, non destructif).
"""
from __future__ import unicode_literals, division
#pylint: disable=E0401,W0621,W0631,C0413,C0111,C0103
__doc__ = 'Recadre une image selon une ou plusieurs zones de pochage.'
__author__ = 'Aliae'

import sys
import os

import clr
clr.AddReference('System')
clr.AddReference('System.Drawing')
from System import IO
from System.Drawing import (GraphicsUnit, Graphics, Rectangle, Bitmap)
from pyrevit import revit, forms, DB, UI

doc = revit.doc
uidoc = revit.uidoc


def get_selected_elements():
    """ Retourne les elements actuellement selectionnes. """
    selection = uidoc.Selection
    selection_ids = selection.GetElementIds()
    if not selection_ids:
        UI.TaskDialog.Show('CropImage', 'Aucun element selectionne.')
        sys.exit(0)
    elements = []
    for element_id in selection_ids:
        elements.append(doc.GetElement(element_id))
    return elements


def get_bbox_center_pt(bbox):
    """ Retourne le centre XYZ de la BoundingBox (Z preserve pour rester
    dans le plan du cadre, y compris en coupe/elevation). """
    avg_x = (bbox.Min.X + bbox.Max.X) / 2
    avg_y = (bbox.Min.Y + bbox.Max.Y) / 2
    avg_z = (bbox.Min.Z + bbox.Max.Z) / 2
    return DB.XYZ(avg_x, avg_y, avg_z)


def create_img_copy(img_path):
    """ Cree une copie de l'image dans le meme dossier, avec un suffixe
    sequentiel (_cropped_N). Preserve l'extension et les points du chemin. """
    base, extension = os.path.splitext(img_path)  # extension inclut le point
    seq_start = 1
    while True:
        new_img_path = '{}_cropped_{}{}'.format(base, seq_start, extension)
        try:
            IO.File.Copy(img_path, new_img_path)
            return new_img_path
        except IO.IOException:
            # Le fichier existe deja : on essaie le numero suivant.
            seq_start += 1
        except Exception as errmsg:
            print('Unknown Error: {}'.format(new_img_path))
            print(errmsg)
            raise


def crop_image(img_path, rectangle_crop):
    """ Ecrit un fichier recadre (copie du source) selon rectangle_crop. """
    if not os.path.exists(img_path):
        raise Exception('Image source introuvable : {}'.format(img_path))
    source_bmp = Bitmap(img_path)
    new_img_path = create_img_copy(img_path)
    # Sans ceci, les images qui ne sont pas en 96 dpi sont recadrees hors echelle.
    source_bmp.SetResolution(96, 96)
    # Bitmap vide qui recevra l'image recadree.
    bmp = Bitmap(rectangle_crop.Width, rectangle_crop.Height)
    graphic = Graphics.FromImage(bmp)
    # Dessine la zone (rectangle_crop) de source_bmp a la position 0,0 du bmp.
    graphic.DrawImage(source_bmp, 0, 0, rectangle_crop, GraphicsUnit.Pixel)
    bmp.Save(new_img_path)
    return new_img_path


def read_image_info(img_element, img_type):
    """ Lit une fois tous les parametres de l'image source (partages entre
    toutes les zones de pochage). Retourne un dict. """
    bip_filename = DB.BuiltInParameter.RASTER_SYMBOL_FILENAME
    bip_width_px = DB.BuiltInParameter.RASTER_SYMBOL_PIXELWIDTH
    bip_height_px = DB.BuiltInParameter.RASTER_SYMBOL_PIXELHEIGHT
    bip_resolution = DB.BuiltInParameter.RASTER_SYMBOL_RESOLUTION
    bip_width_ft = DB.BuiltInParameter.RASTER_SHEETWIDTH
    bip_height_ft = DB.BuiltInParameter.RASTER_SHEETHEIGHT

    info = {
        'path': img_type.get_Parameter(bip_filename).AsString(),
        'width_px': img_type.get_Parameter(bip_width_px).AsInteger(),
        'height_px': img_type.get_Parameter(bip_height_px).AsInteger(),
        'resolution': img_type.get_Parameter(bip_resolution).AsInteger(),
        'width': img_element.get_Parameter(bip_width_ft).AsDouble(),
        'height': img_element.get_Parameter(bip_height_ft).AsDouble(),
        'bbox': img_element.get_BoundingBox(doc.ActiveView),
        'bip_width_ft': bip_width_ft,
    }

    # Resolution DPI : AsInteger() peut renvoyer 0 selon le stockage du
    # parametre. On la recalcule depuis pixels / taille physique
    # (DPI = pixels / pouces ; width est en pieds -> * 12 pouces).
    if not info['resolution'] or info['resolution'] <= 0:
        inches_w = info['width'] * 12.0
        info['resolution'] = (int(round(info['width_px'] / inches_w))
                              if inches_w else 0)
        print('[CropImage] Resolution recalculee = {} DPI'.format(
            info['resolution']))
    return info


def crop_and_place(img_info, region):
    """ Recadre l'image source selon la bbox de 'region' et place le morceau
    dans son cadre. Retourne l'ImageInstance creee, ou None si la region est
    invalide (sans bbox, hors image, trop fine...). """
    view = doc.ActiveView
    region_bbox = region.get_BoundingBox(view)
    if not region_bbox:
        print('[CropImage] Region {} sans bounding box, ignoree.'.format(
            region.Id))
        return None

    # Dimensions absolues du cadre.
    cropbox_height_ft = region_bbox.Max.Y - region_bbox.Min.Y
    cropbox_width_ft = region_bbox.Max.X - region_bbox.Min.X

    # Origine relative de la decoupe par rapport au coin de l'image.
    lw_left_crop_pt = region_bbox.Min - img_info['bbox'].Min
    up_left_crop_pt = lw_left_crop_pt + DB.XYZ(0, cropbox_height_ft, 0)
    crop_pt_x_ft = up_left_crop_pt.X
    crop_pt_y_ft = img_info['height'] - up_left_crop_pt.Y

    # Conversion pieds -> pixels.
    x_scale = img_info['width_px'] / img_info['width']
    y_scale = img_info['height_px'] / img_info['height']
    rectangle_crop = Rectangle(int(round(crop_pt_x_ft * x_scale)),
                               int(round(crop_pt_y_ft * y_scale)),
                               int(round(cropbox_width_ft * x_scale)),
                               int(round(cropbox_height_ft * y_scale)))
    print('[CropImage] Region {} -> rectangle px x={} y={} w={} h={}'.format(
        region.Id, rectangle_crop.X, rectangle_crop.Y,
        rectangle_crop.Width, rectangle_crop.Height))

    if rectangle_crop.Width <= 0 or rectangle_crop.Height <= 0:
        print('[CropImage] Region {} : zone vide/hors image, ignoree.'.format(
            region.Id))
        return None

    # Fichier recadre sur disque.
    new_img_path = crop_image(img_info['path'], rectangle_crop)
    print('[CropImage] Fichier recadre : {}'.format(new_img_path))

    # Type d'image (False = chemin absolu).
    type_options = DB.ImageTypeOptions(
        new_img_path, False, DB.ImageTypeSource.Import)
    if img_info['resolution'] and img_info['resolution'] > 0:
        type_options.Resolution = img_info['resolution']
    new_img_type = DB.ImageType.Create(doc, type_options)

    # Regenere avant de placer l'instance (sinon "internal error").
    doc.Regenerate()

    # Instance centree exactement sur le centre du cadre.
    placement = DB.ImagePlacementOptions(
        get_bbox_center_pt(region_bbox), DB.BoxPlacement.Center)
    new_instance = DB.ImageInstance.Create(
        doc, view, new_img_type.Id, placement)

    # Cale la largeur sur le cadre (la hauteur suit le ratio, identique).
    width_param = new_instance.get_Parameter(img_info['bip_width_ft'])
    if width_param and not width_param.IsReadOnly:
        width_param.Set(cropbox_width_ft)

    print('[CropImage] Region {} : morceau place (id {}).'.format(
        region.Id, new_instance.Id))
    return new_instance


# Couleur du cadre applique aux zones resolues (vert). Modifier ici au besoin.
GREEN = DB.Color(0, 176, 80)


def mark_region_solved(region):
    """ Marque une zone de pochage comme "resolue" dans la vue active :
    aucun remplissage (patterns masques) + contour vert. Override propre a
    la vue, non destructif (l'element et son type ne sont pas modifies). """
    ogs = DB.OverrideGraphicSettings()
    # Sans fond : masque les motifs de surface et de coupe (avant + arriere).
    ogs.SetSurfaceForegroundPatternVisible(False)
    ogs.SetSurfaceBackgroundPatternVisible(False)
    ogs.SetCutForegroundPatternVisible(False)
    ogs.SetCutBackgroundPatternVisible(False)
    # Cadre vert.
    ogs.SetProjectionLineColor(GREEN)
    ogs.SetCutLineColor(GREEN)
    ogs.SetProjectionLineWeight(4)
    doc.ActiveView.SetElementOverrides(region.Id, ogs)


# --------------------------------------------------------------------------
# Selection : 1 image source + N zones de pochage.
# --------------------------------------------------------------------------
img_element, img_type = None, None
crop_elements = []

elements = get_selected_elements()
print('=' * 50)
print('[CropImage] {} element(s) selectionne(s)'.format(len(elements)))
for element in elements:
    # Zone de pochage : region remplie ou ligne de detail.
    if isinstance(element, (DB.FilledRegion, DB.DetailLine)):
        crop_elements.append(element)
        print('[CropImage] Zone de pochage : {} (id {})'.format(
            type(element).__name__, element.Id))
        continue

    # Sinon, cherche une image parmi les types valides.
    for valid_type_id in element.GetValidTypes():
        valid_type = doc.GetElement(valid_type_id)
        if isinstance(valid_type, DB.ImageType):
            if img_element is not None:
                print('[CropImage] Plusieurs images selectionnees : '
                      'seule la derniere est utilisee.')
            img_element = element
            img_type = valid_type
            print('[CropImage] Image source (id {})'.format(img_element.Id))
            break


# --------------------------------------------------------------------------
# Validation puis traitement.
# --------------------------------------------------------------------------
if not img_element or not crop_elements:
    forms.alert(
        'Selectionner UNE image + au moins une zone de pochage '
        '(region remplie ou ligne de detail).'
    )
else:
    img_info = read_image_info(img_element, img_type)
    print('[CropImage] chemin     = {}'.format(img_info['path']))
    print('[CropImage] pixels     = {} x {} px'.format(
        img_info['width_px'], img_info['height_px']))
    print('[CropImage] taille     = {} x {} ft'.format(
        img_info['width'], img_info['height']))
    print('[CropImage] zones a decouper = {}'.format(len(crop_elements)))

    if not img_info['path']:
        # Image integree au modele (pas de fichier externe sur disque).
        forms.alert(
            "Impossible de recuperer le chemin de l'image "
            "(elle est peut-etre integree au modele et non liee a un fichier)."
        )
    elif (not img_info['width'] or not img_info['height']
          or not img_info['width_px'] or not img_info['height_px']):
        forms.alert(
            "Dimensions de l'image invalides (largeur/hauteur nulle)."
        )
    else:
        # Une seule transaction pour toutes les zones.
        t = DB.Transaction(doc, 'Crop Image')
        t.Start()
        try:
            placed = 0
            for region in crop_elements:
                instance = crop_and_place(img_info, region)
                if instance is not None:
                    # Zone conservee, stylisee "resolue" : sans fond + cadre vert.
                    mark_region_solved(region)
                    print('[CropImage] Zone {} stylisee (resolue).'.format(
                        region.Id))
                    placed += 1
            # L'image d'origine est CONSERVEE (pas de suppression).

            t.Commit()
            print('[CropImage] Termine : {} morceau(x) cree(s) sur {} zone(s).'
                  .format(placed, len(crop_elements)))
            if placed == 0:
                forms.alert(
                    "Aucune zone valide : verifier que les zones de pochage "
                    "sont bien situees sur l'image."
                )
        except Exception:
            t.RollBack()
            import traceback
            print('[CropImage] ECHEC :')
            print(traceback.format_exc())
            UI.TaskDialog.Show(
                'CropImage - Erreur',
                "Echec de la creation des images dans Revit :\n\n{}".format(
                    traceback.format_exc())
            )
            raise
