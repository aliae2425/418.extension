# -*- coding: utf-8 -*-
"""
Recadre une image importee selon une region remplie ou une ligne de detail.

Selectionner une image + une region remplie (ou une ligne de detail) qui
delimite la zone a conserver, puis lancer la commande. L'image recadree
remplace l'image d'origine a la meme position.
"""
from __future__ import unicode_literals, division
#pylint: disable=E0401,W0621,W0631,C0413,C0111,C0103
__doc__ = 'Recadre une image selon une region remplie ou une ligne de detail.'
__author__ = 'Aliae'

import sys
import os

import clr
clr.AddReference('System')
clr.AddReference('System.IO')
clr.AddReference('System.Drawing')
from System import IO
from System.Drawing import (GraphicsUnit, Graphics, Rectangle, Bitmap)

import rpw
from rpw import doc, uidoc, DB, UI


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


img_element, img_type, element_bbox, crop_element = None, None, None, None
img_path = None
elements = get_selected_elements()
print('=' * 50)
print('[CropImage] {} element(s) selectionne(s)'.format(len(elements)))
for element in elements:
    # Region de decoupe : region remplie ou ligne de detail.
    if isinstance(element, (DB.FilledRegion, DB.DetailLine)):
        crop_element = element
        element_bbox = element.get_BoundingBox(doc.ActiveView)
        print('[CropImage] Cadre de decoupe : {} (id {})'.format(
            type(element).__name__, element.Id))
        continue

    for valid_type_id in element.GetValidTypes():
        valid_type = doc.GetElement(valid_type_id)

        if isinstance(valid_type, DB.ImageType):
            img_element = element
            img_type = valid_type

            # Definitions BIP du type
            bip_filename = DB.BuiltInParameter.RASTER_SYMBOL_FILENAME
            bip_height_px = DB.BuiltInParameter.RASTER_SYMBOL_PIXELHEIGHT
            bip_width_px = DB.BuiltInParameter.RASTER_SYMBOL_PIXELWIDTH
            bip_resolution = DB.BuiltInParameter.RASTER_SYMBOL_RESOLUTION

            # Parametres du type
            img_path = img_type.get_Parameter(bip_filename).AsString()
            img_width_px = img_type.get_Parameter(bip_width_px).AsInteger()
            img_height_px = img_type.get_Parameter(bip_height_px).AsInteger()
            img_resolution = img_type.get_Parameter(bip_resolution).AsInteger()

            # Definitions BIP de l'instance
            bip_scale = DB.BuiltInParameter.RASTER_VERTICAL_SCALE
            bip_width_ft = DB.BuiltInParameter.RASTER_SHEETWIDTH   # Largeur
            bip_height_ft = DB.BuiltInParameter.RASTER_SHEETHEIGHT  # Hauteur

            # Parametres de l'instance
            img_scale = img_element.get_Parameter(bip_scale).AsDouble()
            img_width = img_element.get_Parameter(bip_width_ft).AsDouble()
            img_height = img_element.get_Parameter(bip_height_ft).AsDouble()
            img_bbox = img_element.get_BoundingBox(doc.ActiveView)

            print('[CropImage] Image trouvee (id {})'.format(img_element.Id))
            print('[CropImage]   chemin     = {}'.format(img_path))
            print('[CropImage]   pixels     = {} x {} px'.format(
                img_width_px, img_height_px))
            print('[CropImage]   taille     = {} x {} ft'.format(
                img_width, img_height))
            print('[CropImage]   resolution = {} (param brut)'.format(
                img_resolution))
            break

if not img_element or not crop_element or not element_bbox:
    rpw.ui.forms.Alert(
        'Selectionner une image + une region remplie ou une ligne de detail.'
    )
elif not img_path:
    # Cas des images integrees au modele (pas de fichier externe sur disque).
    rpw.ui.forms.Alert(
        "Impossible de recuperer le chemin de l'image "
        "(elle est peut-etre integree au modele et non liee a un fichier)."
    )
elif not img_width or not img_height or not img_width_px or not img_height_px:
    rpw.ui.forms.Alert("Dimensions de l'image invalides (largeur/hauteur nulle).")
else:
    print('[CropImage] Image + cadre OK, calcul du recadrage...')

    # Resolution DPI : AsInteger() peut renvoyer 0 selon le stockage du
    # parametre. On la recalcule alors depuis pixels / taille physique
    # (DPI = pixels / pouces ; img_width est en pieds -> * 12 pouces).
    if not img_resolution or img_resolution <= 0:
        inches_w = img_width * 12.0
        img_resolution = int(round(img_width_px / inches_w)) if inches_w else 0
        print('[CropImage] Resolution recalculee = {} DPI'.format(img_resolution))

    # Hauteur/largeur absolues de la boite de decoupe.
    cropbox_height_ft = element_bbox.Max.Y - element_bbox.Min.Y
    cropbox_width_ft = element_bbox.Max.X - element_bbox.Min.X

    # Coordonnee relative de la boite de decoupe / coin de l'image.
    lw_left_crop_pt = element_bbox.Min - img_bbox.Min
    up_left_crop_pt = lw_left_crop_pt + DB.XYZ(0, cropbox_height_ft, 0)

    # Origine relative pour le recadrage.
    crop_pt_x_ft = up_left_crop_pt.X
    crop_pt_y_ft = img_height - up_left_crop_pt.Y

    # Facteur de conversion pieds -> pixels.
    x_ft_to_px_scale = img_width_px / img_width
    y_ft_to_px_scale = img_height_px / img_height

    # Conversion de l'espace en pieds vers l'espace en pixels.
    crop_pt_x_px = crop_pt_x_ft * x_ft_to_px_scale
    crop_pt_y_px = crop_pt_y_ft * y_ft_to_px_scale
    cropbox_width_px = cropbox_width_ft * x_ft_to_px_scale
    cropbox_height_px = cropbox_height_ft * y_ft_to_px_scale

    # System.Drawing.Rectangle attend des entiers.
    rectangle_crop = Rectangle(int(round(crop_pt_x_px)),
                               int(round(crop_pt_y_px)),
                               int(round(cropbox_width_px)),
                               int(round(cropbox_height_px)))

    print('[CropImage] Cadre : {} x {} ft'.format(
        cropbox_width_ft, cropbox_height_ft))
    print('[CropImage] Rectangle de decoupe (px) : x={} y={} w={} h={}'.format(
        rectangle_crop.X, rectangle_crop.Y,
        rectangle_crop.Width, rectangle_crop.Height))

    if rectangle_crop.Width <= 0 or rectangle_crop.Height <= 0:
        rpw.ui.forms.Alert(
            "La zone de decoupe est vide ou hors de l'image "
            "(region trop fine ou en dehors de l'image)."
        )
        sys.exit(0)

    new_img_path = crop_image(img_path, rectangle_crop)
    print('[CropImage] Fichier recadre cree : {}'.format(new_img_path))

    # Point de placement = centre du cadre forme par la region / les lignes.
    placement_pt = get_bbox_center_pt(element_bbox)
    print('[CropImage] Point de placement (centre cadre) : {}, {}, {}'.format(
        placement_pt.X, placement_pt.Y, placement_pt.Z))

    # Cree la nouvelle image dans Revit et la cale dans le cadre.
    # Transaction explicite : rpw.db.Transaction pouvait avaler l'exception
    # (rollback silencieux -> fichier cree mais rien dans Revit).
    t = DB.Transaction(doc, 'Crop Image')
    t.Start()
    try:
        # 1. Type d'image a partir du fichier recadre.
        #    False = chemin absolu (et non relatif au projet).
        type_options = DB.ImageTypeOptions(
            new_img_path, False, DB.ImageTypeSource.Import)
        # Resolution : uniquement si strictement positive (sinon Revit rejette).
        if img_resolution and img_resolution > 0:
            type_options.Resolution = img_resolution
        else:
            print('[CropImage] Resolution non definie, valeur par defaut utilisee.')
        new_img_type = DB.ImageType.Create(doc, type_options)
        print('[CropImage] ImageType cree (id {})'.format(new_img_type.Id))

        # Force la mise a jour du document avant de placer l'instance,
        # sinon ImageInstance.Create peut lever une "internal error".
        doc.Regenerate()

        # 2. Instance centree exactement sur le centre du cadre.
        placement = DB.ImagePlacementOptions(
            placement_pt, DB.BoxPlacement.Center)
        new_img_instance = DB.ImageInstance.Create(
            doc, doc.ActiveView, new_img_type.Id, placement)
        print('[CropImage] ImageInstance placee (id {})'.format(
            new_img_instance.Id))

        # 3. Ajuste la largeur pour caler l'image exactement dans le cadre
        #    (la hauteur suit le ratio, identique a celui du cadre).
        new_img_width = new_img_instance.get_Parameter(bip_width_ft)
        if new_img_width and not new_img_width.IsReadOnly:
            new_img_width.Set(cropbox_width_ft)
            print('[CropImage] Largeur calee sur le cadre : {} ft'.format(
                cropbox_width_ft))
        else:
            print('[CropImage] Parametre largeur introuvable ou en lecture seule.')

        # 4. Supprime l'image d'origine et le cadre de decoupe.
        doc.Delete(img_element.Id)
        doc.Delete(crop_element.Id)
        print('[CropImage] Image d\'origine et cadre supprimes.')

        t.Commit()
        print('[CropImage] Termine avec succes.')
    except Exception:
        t.RollBack()
        import traceback
        print('[CropImage] ECHEC :')
        print(traceback.format_exc())
        UI.TaskDialog.Show(
            'CropImage - Erreur',
            "Echec de la creation de l'image dans Revit :\n\n{}".format(
                traceback.format_exc())
        )
        raise
