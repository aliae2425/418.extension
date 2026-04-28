# -*- coding: utf-8 -*-
__title__ = "Échappée\nEscalier"
__doc__ = """
    Version 0.1
    Auteur : Aliae
    _____________________________________________

    Génère des volumes de contrôle 3D (DirectShape) représentant
    l'enveloppe d'échappée requise au-dessus de chaque marche.

    Lancer l'outil avec une sélection d'escaliers active pour ne traiter
    que ceux-ci, ou sans sélection pour traiter tout le document.
    _____________________________________________
"""
__author__ = 'Aliae'
__min_revit_ver__ = 2026

if __name__ == "__main__":
    import sys
    from pyrevit import forms, revit
    import config
    from lib.stair_collector import collect_stairs, collect_stairs_from_selection
    from lib.tread_geometry import extraire_faces_marches
    from lib.swept_blend_builder import supprimer_formes_existantes, construire_directshape_volee

    doc = __revit__.ActiveUIDocument.Document      # type: ignore
    uidoc = __revit__.ActiveUIDocument             # type: ignore

    # --- 1. Saisie de la hauteur ---
    hauteur_str = forms.ask_for_string(
        default=str(config.lire_hauteur()),
        prompt=u"Hauteur d'échappée minimale (en mètres) :",
        title=u"Échappée Escalier"
    )
    if not hauteur_str:
        sys.exit()

    try:
        hauteur_m = float(hauteur_str.replace(',', '.'))
        if hauteur_m <= 0:
            raise ValueError(u"hauteur <= 0")
    except (ValueError, TypeError):
        forms.alert(u"Hauteur invalide. Veuillez saisir un nombre positif.",
                    title=u"Échappée Escalier")
        sys.exit()

    config.sauver_hauteur(hauteur_m)
    hauteur_ft = hauteur_m / 0.3048  # conversion mètres → pieds (unité interne Revit)

    # --- 2. Sélection des escaliers ---
    escaliers = collect_stairs_from_selection(uidoc, doc)
    if not escaliers:
        escaliers = collect_stairs(doc)

    if not escaliers:
        forms.alert(u"Aucun escalier trouvé dans le document.",
                    title=u"Échappée Escalier")
        sys.exit()

    # --- 3. Génération dans une transaction ---
    nb_shapes = 0
    nb_volees_ignorees = 0

    with revit.Transaction(doc=doc, name=u"418 - Échappée Escalier"):
        supprimer_formes_existantes(doc)

        for escalier in escaliers:
            try:
                run_ids = escalier.GetStairsRuns()
            except Exception:
                continue

            for run_id in run_ids:
                run = doc.GetElement(run_id)
                if run is None:
                    continue

                faces = extraire_faces_marches(run)
                if not faces:
                    nb_volees_ignorees += 1
                    continue

                shape = construire_directshape_volee(doc, faces, hauteur_ft, run_id)
                if shape is not None:
                    nb_shapes += 1
                else:
                    nb_volees_ignorees += 1

    # --- 4. Compte-rendu ---
    msg = u"{} escalier(s) traité(s), {} DirectShape(s) créé(s).".format(
        len(escaliers), nb_shapes
    )
    if nb_volees_ignorees:
        msg += u"\n{} volée(s) ignorée(s) (géométrie non extractible).".format(
            nb_volees_ignorees
        )
    forms.alert(msg, title=u"Échappée Escalier")
