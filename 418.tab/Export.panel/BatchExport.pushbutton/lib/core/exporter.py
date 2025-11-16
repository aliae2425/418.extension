# -*- coding: utf-8 -*-
"""Core export orchestrator: plans and execution for PDF/DWG."""

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
from ..exports.pdf import (
    list_all_pdf_setups,
    get_saved_pdf_setup,
    get_saved_pdf_separate,
    build_pdf_export_options,
    get_custom_pdf_setup_data,
)
from ..exports.dwg import (
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
    try:
        if CONFIG.get('create_subfolders', '') == '1' and collection_name:
            base = os.path.join(base, collection_name)
    except Exception:
        pass
    try:
        if CONFIG.get('separate_format_folders', '') == '1' and fmt_subfolder:
            base = os.path.join(base, fmt_subfolder)
    except Exception:
        pass
    ensure_directory(base)
    return base


def _get_pdf_options(doc):
    setup_name = get_saved_pdf_setup()
    custom = get_custom_pdf_setup_data(setup_name) if setup_name else None
    if custom:
        return build_pdf_export_options(doc, setup_name=None)
    return build_pdf_export_options(doc, setup_name=setup_name)


def _get_dwg_options(doc):
    setup_name = get_saved_dwg_setup()
    custom = get_custom_dwg_setup_data(setup_name) if setup_name else None
    if custom:
        return build_dwg_export_options(doc, setup_name=None)
    return build_dwg_export_options(doc, setup_name=setup_name)


def _collect_collections(doc):
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
    patt, rows = load_pattern('sheet')
    display_name = None
    try:
        display_name = sheet.SheetNumber + '_' + sheet.Name
    except Exception:
        display_name = getattr(sheet, 'Name', 'Sheet')
    if not rows:
        return [{'Name': display_name, 'Prefix': '', 'Suffix': ''}]
    return rows


def plan_exports_for_collections(doc, get_ctrl):
    names = _get_ui_selected_param_names(get_ctrl)
    pname_export = names.get('ExportationCombo')
    pname_per_sheet = names.get('CarnetCombo')
    pname_dwg = names.get('DWGCombo')

    plans = []
    for coll, cname in _collect_collections(doc):
        do_export = _read_flag_from_param(coll, pname_export, default=False) if pname_export else False
        per_sheet = _read_flag_from_param(coll, pname_per_sheet, default=False) if pname_per_sheet else False
        do_dwg = _read_flag_from_param(coll, pname_dwg, default=False) if pname_dwg else False
        do_pdf = bool(do_export)
        plans.append(ExportPlan(cname, do_export, per_sheet, do_dwg, do_pdf))
    return plans


def execute_exports(doc, get_ctrl, progress_cb=None, log_cb=None, ui_win=None):
    plans = plan_exports_for_collections(doc, get_ctrl)
    total = len(plans)
    if progress_cb:
        progress_cb(0, max(total, 1), 'Préparation...')

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
        try:
            if ui_win is not None:
                from ..ui.preview.grid import _set_collection_status, _refresh_collection_grid  # type: ignore
                _set_collection_status(ui_win, plan.collection_name, 'progress')
                _refresh_collection_grid(ui_win)
        except Exception:
            pass
        sheets = _get_collection_sheets(doc, _find_collection_by_name(doc, plan.collection_name))
        base_pdf = _get_destination_base('PDF', plan.collection_name) if plan.do_pdf else None
        base_dwg = _get_destination_base('DWG', plan.collection_name) if plan.do_dwg else None

        if plan.per_sheet:
            for sh in sheets:
                rows = _build_filename_rows_for_sheet(sh)
                if plan.do_pdf and base_pdf:
                    try:
                        if ui_win is not None:
                            from ..ui.preview.grid import _set_detail_status, _refresh_collection_grid  # type: ignore
                            _set_detail_status(ui_win, plan.collection_name, _safe_sheet_name(sh), 'PDF', 'progress')
                            _refresh_collection_grid(ui_win)
                    except Exception:
                        pass
                    ok_path = _export_pdf_sheet(doc, sh, rows, base_pdf, pdf_opt, separate=pdf_sep)
                    try:
                        if ui_win is not None:
                            from ..ui.preview.grid import _set_detail_status, _refresh_collection_grid  # type: ignore
                            _set_detail_status(ui_win, plan.collection_name, _safe_sheet_name(sh), 'PDF', 'ok')
                            _refresh_collection_grid(ui_win)
                    except Exception:
                        pass
                if plan.do_dwg and base_dwg:
                    try:
                        if ui_win is not None:
                            from ..ui.preview.grid import _set_detail_status, _refresh_collection_grid  # type: ignore
                            _set_detail_status(ui_win, plan.collection_name, _safe_sheet_name(sh), 'DWG', 'progress')
                            _refresh_collection_grid(ui_win)
                    except Exception:
                        pass
                    _export_dwg_sheet(doc, sh, rows, base_dwg, dwg_opt)
                    try:
                        if ui_win is not None:
                            from ..ui.preview.grid import _set_detail_status, _refresh_collection_grid  # type: ignore
                            _set_detail_status(ui_win, plan.collection_name, _safe_sheet_name(sh), 'DWG', 'ok')
                            _refresh_collection_grid(ui_win)
                    except Exception:
                        pass
        else:
            rows = _build_filename_rows_for_sheet(sheets[0]) if sheets else [{'Name': plan.collection_name, 'Prefix': '', 'Suffix': ''}]
            if plan.do_pdf and base_pdf:
                try:
                    if ui_win is not None:
                        from ..ui.preview.grid import _set_detail_status, _refresh_collection_grid  # type: ignore
                        name_preview = _safe_sheet_name(sheets[0]) if sheets else plan.collection_name
                        _set_detail_status(ui_win, plan.collection_name, name_preview, 'PDF (combiné)', 'progress')
                        _refresh_collection_grid(ui_win)
                except Exception:
                    pass
                _export_pdf_collection(doc, sheets, rows, base_pdf, pdf_opt)
                try:
                    if ui_win is not None:
                        from ..ui.preview.grid import _set_detail_status, _refresh_collection_grid  # type: ignore
                        name_preview = _safe_sheet_name(sheets[0]) if sheets else plan.collection_name
                        _set_detail_status(ui_win, plan.collection_name, name_preview, 'PDF (combiné)', 'ok')
                        _refresh_collection_grid(ui_win)
                except Exception:
                    pass
            if plan.do_dwg and base_dwg:
                for sh in sheets:
                    rows_sh = _build_filename_rows_for_sheet(sh)
                    try:
                        if ui_win is not None:
                            from ..ui.preview.grid import _set_detail_status, _refresh_collection_grid  # type: ignore
                            _set_detail_status(ui_win, plan.collection_name, _safe_sheet_name(sh), 'DWG', 'progress')
                            _refresh_collection_grid(ui_win)
                    except Exception:
                        pass
                    _export_dwg_sheet(doc, sh, rows_sh, base_dwg, dwg_opt)
                    try:
                        if ui_win is not None:
                            from ..ui.preview.grid import _set_detail_status, _refresh_collection_grid  # type: ignore
                            _set_detail_status(ui_win, plan.collection_name, _safe_sheet_name(sh), 'DWG', 'ok')
                            _refresh_collection_grid(ui_win)
                    except Exception:
                        pass
        try:
            if ui_win is not None:
                from ..ui.preview.grid import _set_collection_status, _refresh_collection_grid  # type: ignore
                _set_collection_status(ui_win, plan.collection_name, 'ok')
                _refresh_collection_grid(ui_win)
        except Exception:
            pass

    if progress_cb:
        progress_cb(total, max(total, 1), 'Terminé')
    return True


def _safe_sheet_name(sheet):
    try:
        return sheet.SheetNumber + '_' + sheet.Name
    except Exception:
        try:
            return getattr(sheet, 'Name', 'Sheet')
        except Exception:
            return 'Sheet'


def _find_collection_by_name(doc, name):
    try:
        for sc, nm in _collect_collections(doc):
            if nm == name:
                return sc
    except Exception:
        pass
    return None


# --- Revit export placeholders ---

def _export_pdf_sheet(doc, sheet, rows, base_folder, options, separate=True):
    desired_name_no_ext = sanitize_filename(resolve_rows_for_element(sheet, rows, empty_fallback=False) or getattr(sheet, 'Name', 'Sheet'))
    ensure_directory(base_folder)
    path = unique_path(os.path.join(base_folder, desired_name_no_ext + '.pdf'))
    folder = os.path.dirname(path)
    file_no_ext = os.path.splitext(os.path.basename(path))[0]
    ok = False
    try:
        if DB is not None and hasattr(DB, 'PDFExportOptions') and options is not None:
            try:
                from System.Collections.Generic import List as Clist  # type: ignore
                views = Clist[DB.ElementId]()
                views.Add(sheet.Id)
            except Exception:
                views = None
            try:
                if hasattr(options, 'Combine'):
                    options.Combine = False
            except Exception:
                pass
            try:
                if hasattr(options, 'FileName'):
                    options.FileName = file_no_ext
            except Exception:
                pass
            if views is not None:
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
            vs = DB.ViewSet()
            try:
                vs.Insert(sheet)
            except Exception:
                pass
            ok = bool(pm.SubmitPrint(vs))
        except Exception:
            ok = False
    print('[PDF] {} -> {} ({})'.format(getattr(sheet, 'Name', 'Sheet'), path, 'OK' if ok else 'FAIL'))
    return path


def _export_dwg_sheet(doc, sheet, rows, base_folder, options):
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
    try:
        if ok:
            cands = [os.path.join(tmp_dir, f) for f in os.listdir(tmp_dir) if f.lower().endswith('.dwg')]
            if cands:
                cands.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                exported_file = cands[0]
                try:
                    os.rename(exported_file, final_path)
                except Exception:
                    import shutil
                    shutil.copy2(exported_file, final_path)
                    try:
                        os.remove(exported_file)
                    except Exception:
                        pass
    except Exception:
        ok = False
    try:
        if os.path.isdir(tmp_dir) and not os.listdir(tmp_dir):
            os.rmdir(tmp_dir)
    except Exception:
        pass
    print('[DWG] {} -> {} ({})'.format(getattr(sheet, 'Name', 'Sheet'), final_path, 'OK' if ok else 'FAIL'))
    return final_path


def _export_pdf_collection(doc, sheets, rows, base_folder, options):
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
    return None


__all__ = ['plan_exports_for_collections', 'execute_exports']
