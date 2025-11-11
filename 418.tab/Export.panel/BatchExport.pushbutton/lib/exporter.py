# -*- coding: utf-8 -*-
"""Exporteur centralisé pour PDF et DWG.

Responsabilités:
- Lire les sélections UI (paramètres Export/Carnet/DWG) et déterminer, par collection,
  s'il faut exporter, en PDF et/ou DWG, et si c'est par feuille ou groupé.
- Respecter les toggles destination: create_subfolders, separate_format_folders.
- Respecter le nommage paramétré (patterns via module naming/piker).

Limites (implémentation initiale):
- Les appels Revit d'export sont esquissés (placeholders) pour éviter les dépendances fortes.
  On construit les chemins et options; l'appel concret DB.ViewSheet/PrintManager/DWG export
  sera à compléter ou adapter selon la version Revit.
"""

from __future__ import unicode_literals

import os
from collections import namedtuple

try:
    from Autodesk.Revit import DB  # type: ignore
except Exception:
    DB = None  # type: ignore

from .config import UserConfigStore
from .destination import (
    get_saved_destination,
    ensure_directory,
    unique_path,
    sanitize_filename,
)
from .naming import load_pattern, build_pattern_from_rows, resolve_rows_for_element
from .pdf_export import (
    list_all_pdf_setups,
    get_saved_pdf_setup,
    get_saved_pdf_separate,
    build_pdf_export_options,
    get_custom_pdf_setup_data,
)
from .dwg_export import (
    list_all_dwg_setups,
    get_saved_dwg_setup,
    get_saved_dwg_separate,
    build_dwg_export_options,
    get_custom_dwg_setup_data,
)


CONFIG = UserConfigStore('batch_export')

ExportPlan = namedtuple('ExportPlan', [
    'collection_name',
    'do_export',
    'per_sheet',
    'do_dwg',
    'do_pdf',
])


def _get_destination_base(fmt_subfolder=None, collection_name=None):
    base = get_saved_destination()
    # Sous-dossiers par collection ?
    try:
        if CONFIG.get('create_subfolders', '') == '1' and collection_name:
            base = os.path.join(base, collection_name)
    except Exception:
        pass
    # Dossiers séparés par format ?
    try:
        if CONFIG.get('separate_format_folders', '') == '1' and fmt_subfolder:
            base = os.path.join(base, fmt_subfolder)
    except Exception:
        pass
    ensure_directory(base)
    return base


def _get_pdf_options(doc):
    setup_name = get_saved_pdf_setup()
    # Si setup custom enregistré avec ce nom
    custom = get_custom_pdf_setup_data(setup_name) if setup_name else None
    if custom:
        # TODO: mapper custom dict -> PDFExportOptions
        # Pour l'instant, créer instance simple
        return build_pdf_export_options(doc, setup_name=None)
    return build_pdf_export_options(doc, setup_name=setup_name)


def _get_dwg_options(doc):
    setup_name = get_saved_dwg_setup()
    custom = get_custom_dwg_setup_data(setup_name) if setup_name else None
    if custom:
        return build_dwg_export_options(doc, setup_name=None)
    return build_dwg_export_options(doc, setup_name=setup_name)


def _collect_collections(doc):
    """Retourne liste [(collection_element, name)]."""
    out = []
    if DB is None or doc is None:
        return out
    try:
        col = DB.FilteredElementCollector(doc).OfClass(DB.SheetCollection).ToElements()
        for sc in col:
            try:
                out.append((sc, sc.Name))
            except Exception:
                continue
    except Exception:
        pass
    return out


def _get_collection_sheets(doc, collection):
    res = []
    try:
        all_sheets = DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet).ToElements()
        for vs in all_sheets:
            try:
                if vs.SheetCollectionId == collection.Id:
                    res.append(vs)
            except Exception:
                continue
    except Exception:
        pass
    return res


def _read_flag_from_param(elem, param_name, default=False):
    try:
        for p in elem.Parameters:
            try:
                if p.Definition and p.Definition.Name == param_name:
                    # Oui/Non param: AsInteger() 0/1
                    v = 0
                    try:
                        v = p.AsInteger()
                    except Exception:
                        pass
                    return bool(v)
            except Exception:
                continue
    except Exception:
        pass
    return default


def _get_ui_selected_param_names(get_ctrl):
    """get_ctrl(name)->control: récupère les noms choisis dans ExportationCombo/CarnetCombo/DWGCombo.
    get_ctrl est une fonction fournie par l'appelant (GUI) pour accéder au SelectedItem.
    """
    names = {}
    for cname in ('ExportationCombo', 'CarnetCombo', 'DWGCombo'):
        ctrl = get_ctrl(cname)
        val = None
        try:
            val = str(getattr(ctrl, 'SelectedItem', None)) if ctrl is not None else None
        except Exception:
            val = None
        names[cname] = val
    return names


def _build_filename_rows_for_sheet(sheet):
    # Utiliser le pattern 'sheet' sauvegardé et injecter Name={sheet_name}
    patt, rows = load_pattern('sheet')
    # rows contiennent des entrées {Name, Prefix, Suffix}. Ici, le Name fait
    # référence à un paramètre; pour un MVP on remplace {Name} par le nom de la vue/feuille.
    # Amélioration ultérieure: résoudre les paramètres Revit des feuilles.
    display_name = None
    try:
        display_name = sheet.SheetNumber + '_' + sheet.Name
    except Exception:
        display_name = getattr(sheet, 'Name', 'Sheet')
    # Si aucune row, fallback sur le nom calculé
    if not rows:
        return [{'Name': display_name, 'Prefix': '', 'Suffix': ''}]
    # Les rows représentent des tokens; la résolution est faite plus tard
    return rows


def plan_exports_for_collections(doc, get_ctrl):
    """Construit un plan d'export par collection d'après les sélections UI.

    Retourne: liste de ExportPlan.
    """
    names = _get_ui_selected_param_names(get_ctrl)
    pname_export = names.get('ExportationCombo')
    pname_per_sheet = names.get('CarnetCombo')  # interprété ici comme "par feuille" (bool)
    pname_dwg = names.get('DWGCombo')

    plans = []
    for coll, cname in _collect_collections(doc):
        do_export = _read_flag_from_param(coll, pname_export, default=False) if pname_export else False
        per_sheet = _read_flag_from_param(coll, pname_per_sheet, default=False) if pname_per_sheet else False
        do_dwg = _read_flag_from_param(coll, pname_dwg, default=False) if pname_dwg else False
        # Pour PDF: si Export est vrai, on exporte en PDF; DWG est activé/désactivé séparément
        do_pdf = bool(do_export)
        plans.append(ExportPlan(cname, do_export, per_sheet, do_dwg, do_pdf))
    return plans


def execute_exports(doc, get_ctrl, progress_cb=None, log_cb=None):
    """Exécute l'export selon plan.

    - get_ctrl(name) -> contrôle (permet d'accéder aux SelectedItem si besoin)
    - progress_cb(i, n, text) -> MAJ progress bar
    - log_cb(text) -> afficher un message
    """
    plans = plan_exports_for_collections(doc, get_ctrl)
    total = len(plans)
    if progress_cb:
        progress_cb(0, max(total, 1), 'Préparation...')

    # Options & toggles globaux
    pdf_sep = get_saved_pdf_separate(False)
    dwg_sep = get_saved_dwg_separate(False)
    pdf_opt = _get_pdf_options(doc)
    dwg_opt = _get_dwg_options(doc)

    for i, plan in enumerate(plans):
        if progress_cb:
            progress_cb(i, total, 'Collection: {}'.format(plan.collection_name))
        if not plan.do_export:
            if log_cb:
                log_cb(u"Ignoré: {} (Export=0)".format(plan.collection_name))
            continue
        sheets = _get_collection_sheets(doc, _find_collection_by_name(doc, plan.collection_name))
        # Bases de destination
        base_pdf = _get_destination_base('PDF', plan.collection_name) if plan.do_pdf else None
        base_dwg = _get_destination_base('DWG', plan.collection_name) if plan.do_dwg else None

        if plan.per_sheet:
            # Export chaque feuille individuellement
            for sh in sheets:
                rows = _build_filename_rows_for_sheet(sh)
                if plan.do_pdf and base_pdf:
                    _export_pdf_sheet(doc, sh, rows, base_pdf, pdf_opt, separate=pdf_sep)
                # Pour DWG: toujours par feuille (on respecte le nommage des feuilles)
                if plan.do_dwg and base_dwg:
                    _export_dwg_sheet(doc, sh, rows, base_dwg, dwg_opt)
        else:
            # Export groupé (PDF et/ou DWG) -> un fichier par format
            rows = _build_filename_rows_for_sheet(sheets[0]) if sheets else [{'Name': plan.collection_name, 'Prefix': '', 'Suffix': ''}]
            if plan.do_pdf and base_pdf:
                _export_pdf_collection(doc, sheets, rows, base_pdf, pdf_opt)
            # DWG: exporter malgré tout par feuille pour contrôler les noms
            if plan.do_dwg and base_dwg:
                for sh in sheets:
                    rows_sh = _build_filename_rows_for_sheet(sh)
                    _export_dwg_sheet(doc, sh, rows_sh, base_dwg, dwg_opt)

    if progress_cb:
        progress_cb(total, max(total, 1), 'Terminé')
    return True


def _find_collection_by_name(doc, name):
    try:
        for sc, nm in _collect_collections(doc):
            if nm == name:
                return sc
    except Exception:
        pass
    return None


# ---------------------- Placeholders d'export Revit ---------------------- #

def _export_pdf_sheet(doc, sheet, rows, base_folder, options, separate=True):
    # Résoudre le nom via les paramètres de la feuille; fallback sur token si vide
    desired_name_no_ext = sanitize_filename(resolve_rows_for_element(sheet, rows, empty_fallback=False) or getattr(sheet, 'Name', 'Sheet'))
    ensure_directory(base_folder)
    path = unique_path(os.path.join(base_folder, desired_name_no_ext + '.pdf'))
    folder = os.path.dirname(path)
    file_no_ext = os.path.splitext(os.path.basename(path))[0]
    # Essayer l'API PDFExportOptions si disponible
    ok = False
    try:
        if DB is not None and hasattr(DB, 'PDFExportOptions') and options is not None:
            # Construire la liste des vues
            try:
                from System.Collections.Generic import List as Clist  # type: ignore
                views = Clist[DB.ElementId]()
                views.Add(sheet.Id)
            except Exception:
                views = None
            # Config options
            try:
                if hasattr(options, 'Combine'):
                    options.Combine = False  # une feuille = un fichier
            except Exception:
                pass
            try:
                # Si FileName est supporté, l'utiliser
                if hasattr(options, 'FileName'):
                    options.FileName = file_no_ext
            except Exception:
                pass
            if views is not None:
                # Essayer différentes surcharges Export
                try:
                    ok = bool(doc.Export(folder, views, options))
                except Exception:
                    try:
                        ok = bool(doc.Export(folder, file_no_ext, views, options))
                    except Exception:
                        ok = False
    except Exception:
        ok = False
    if not ok:
        # Fallback: PrintManager -> Microsoft Print to PDF
        try:
            pm = doc.PrintManager
            pm.PrintToFile = True
            pm.PrintToFileName = path
            try:
                pm.SelectNewPrintDriver('Microsoft Print to PDF')
            except Exception:
                pass
            try:
                pm.PrintRange = DB.PrintRange.Select
            except Exception:
                pass
            # Préparer ViewSet
            vs = DB.ViewSet()
            try:
                vs.Insert(sheet)
            except Exception:
                pass
            # Soumettre l'impression
            ok = bool(pm.SubmitPrint(vs))
        except Exception:
            ok = False
    print('[PDF] {} -> {} ({})'.format(getattr(sheet, 'Name', 'Sheet'), path, 'OK' if ok else 'FAIL'))
    return path


def _export_dwg_sheet(doc, sheet, rows, base_folder, options):
    # Construire le nom désiré et exporter dans un sous-dossier temporaire, puis renommer
    desired_name_no_ext = sanitize_filename(resolve_rows_for_element(sheet, rows, empty_fallback=False) or getattr(sheet, 'Name', 'Sheet'))
    ensure_directory(base_folder)
    final_path = unique_path(os.path.join(base_folder, desired_name_no_ext + '.dwg'))
    tmp_dir = os.path.join(base_folder, '_tmp_dwg')
    ensure_directory(tmp_dir)
    ok = False
    exported_file = None
    try:
        if DB is not None and options is not None:
            from System.Collections.Generic import List as Clist  # type: ignore
            views = Clist[DB.ElementId]()
            views.Add(sheet.Id)
            ok = bool(doc.Export(tmp_dir, views, options))
    except Exception:
        ok = False
    # Déplacer le fichier exporté
    try:
        if ok:
            cands = [os.path.join(tmp_dir, f) for f in os.listdir(tmp_dir) if f.lower().endswith('.dwg')]
            if cands:
                # Prendre le plus récent
                cands.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                exported_file = cands[0]
                try:
                    # Si un fichier de destination existe, unique_path l'a déjà évité
                    os.rename(exported_file, final_path)
                except Exception:
                    # Fallback: copier puis supprimer
                    import shutil
                    shutil.copy2(exported_file, final_path)
                    try:
                        os.remove(exported_file)
                    except Exception:
                        pass
    except Exception:
        ok = False
    # Nettoyage du dossier temporaire s'il est vide
    try:
        if os.path.isdir(tmp_dir) and not os.listdir(tmp_dir):
            os.rmdir(tmp_dir)
    except Exception:
        pass
    print('[DWG] {} -> {} ({})'.format(getattr(sheet, 'Name', 'Sheet'), final_path, 'OK' if ok else 'FAIL'))
    return final_path


def _export_pdf_collection(doc, sheets, rows, base_folder, options):
    # Nom combiné basé sur le premier sheet ou libellé; combine=True si possible
    name_no_ext = sanitize_filename('' if not sheets else resolve_rows_for_element(sheets[0], rows, empty_fallback=False)) or 'export'
    ensure_directory(base_folder)
    path = unique_path(os.path.join(base_folder, name_no_ext + '.pdf'))
    folder = os.path.dirname(path)
    file_no_ext = os.path.splitext(os.path.basename(path))[0]
    ok = False
    try:
        if DB is not None and hasattr(DB, 'PDFExportOptions') and options is not None and sheets:
            from System.Collections.Generic import List as Clist  # type: ignore
            views = Clist[DB.ElementId]()
            for sh in sheets:
                try:
                    views.Add(sh.Id)
                except Exception:
                    continue
            try:
                if hasattr(options, 'Combine'):
                    options.Combine = True
            except Exception:
                pass
            try:
                if hasattr(options, 'FileName'):
                    options.FileName = file_no_ext
            except Exception:
                pass
            try:
                ok = bool(doc.Export(folder, views, options))
            except Exception:
                try:
                    ok = bool(doc.Export(folder, file_no_ext, views, options))
                except Exception:
                    ok = False
    except Exception:
        ok = False
    print('[PDF] collection({} feuilles) -> {} ({})'.format(len(sheets) if sheets else 0, path, 'OK' if ok else 'FAIL'))
    return path


def _export_dwg_collection(doc, sheets, rows, base_folder, options):
    # Non utilisé (DWG exporté par feuille pour nommer précisément)
    return None


__all__ = ['plan_exports_for_collections', 'execute_exports']
