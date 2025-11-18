# -*- coding: utf-8 -*-
# Orchestrateur d'export: exécute les exports PDF/DWG par collection.

from __future__ import unicode_literals

import os
from collections import namedtuple

try:
    from Autodesk.Revit import DB  # type: ignore
except Exception:
    DB = None  # type: ignore

ExportPlan = namedtuple('ExportPlan', [
    'collection_name',
    'do_export',
    'per_sheet',
    'do_dwg',
    'do_pdf',
])

class ExportOrchestrator(object):
    def __init__(self, namespace='batch_export'):
        # Config utilisateur
        try:
            from ...core.UserConfig import UserConfig
        except Exception:
            UserConfig = None  # type: ignore
        self._cfg = UserConfig(namespace) if UserConfig is not None else None
        # Services
        try:
            from ...services.formats.PdfExporterService import PdfExporterService
            from ...services.formats.DwgExporterService import DwgExporterService
        except Exception:
            PdfExporterService = None  # type: ignore
            DwgExporterService = None  # type: ignore
        self._pdf = PdfExporterService() if PdfExporterService is not None else None
        self._dwg = DwgExporterService() if DwgExporterService is not None else None
        # Données auxiliaires
        try:
            from ...data.destination.DestinationStore import DestinationStore
            from ...data.naming.NamingPatternStore import NamingPatternStore
            from ...data.naming.NamingResolver import NamingResolver
        except Exception:
            DestinationStore = None  # type: ignore
            NamingPatternStore = None  # type: ignore
            NamingResolver = None  # type: ignore
        self._dest = DestinationStore() if DestinationStore is not None else None
        self._nstore = NamingPatternStore() if NamingPatternStore is not None else None
        self._nres = NamingResolver() if NamingResolver is not None else None

    # ------------------- Planification ------------------- #
    def _get_ui_selected_param_names(self, get_ctrl):
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

    def _collect_collections(self, doc):
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

    def _find_collection_by_name(self, doc, name):
        try:
            for sc, nm in self._collect_collections(doc):
                if nm == name:
                    return sc
        except Exception:
            pass
        return None

    def _get_collection_sheets(self, doc, collection):
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

    def _read_flag_from_param(self, elem, param_name, default=False):
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

    def plan_exports_for_collections(self, doc, get_ctrl):
        names = self._get_ui_selected_param_names(get_ctrl)
        pname_export = names.get('ExportationCombo')
        pname_per_sheet = names.get('CarnetCombo')
        pname_dwg = names.get('DWGCombo')
        plans = []
        for coll, cname in self._collect_collections(doc):
            do_export = self._read_flag_from_param(coll, pname_export, default=False) if pname_export else False
            per_sheet = self._read_flag_from_param(coll, pname_per_sheet, default=False) if pname_per_sheet else False
            do_dwg = self._read_flag_from_param(coll, pname_dwg, default=False) if pname_dwg else False
            do_pdf = bool(do_export)
            plans.append(ExportPlan(cname, do_export, per_sheet, do_dwg, do_pdf))
        return plans

    # ------------------- Préférences / Destinations ------------------- #
    def _get_flag(self, key, default='0'):
        try:
            return (self._cfg.get(key, default) if self._cfg is not None else default) or default
        except Exception:
            return default

    def _get_destination_base(self, fmt_subfolder=None, collection_name=None):
        base = None
        try:
            base = self._dest.get()
        except Exception:
            base = None
        base = base or os.getcwd()
        try:
            if self._get_flag('create_subfolders', '0') == '1' and collection_name:
                base = os.path.join(base, collection_name)
        except Exception:
            pass
        try:
            if self._get_flag('separate_format_folders', '0') == '1' and fmt_subfolder:
                base = os.path.join(base, fmt_subfolder)
        except Exception:
            pass
        try:
            self._dest.ensure(base)
        except Exception:
            pass
        return base

    def _get_pdf_options(self, doc):
        if self._pdf is None:
            return None
        setup_name = self._pdf.get_saved_setup()
        # Config custom non mappée pour l'instant
        return self._pdf.build_options(doc, setup_name=setup_name)

    def _get_dwg_options(self, doc):
        if self._dwg is None:
            return None
        setup_name = self._dwg.get_saved_setup()
        return self._dwg.build_options(doc, setup_name=setup_name)

    # ------------------- Exécution ------------------- #
    def run(self, doc, get_ctrl, progress_cb=None, log_cb=None, ui_win=None):
        # UI status component for live updates
        ui_comp = None
        try:
            from ...ui.components.CollectionPreviewComponent import CollectionPreviewComponent
            ui_comp = CollectionPreviewComponent()
        except Exception:
            ui_comp = None
        plans = self.plan_exports_for_collections(doc, get_ctrl)
        total = len(plans)
        if progress_cb:
            progress_cb(0, max(total, 1), 'Préparation...')

        pdf_sep = self._pdf.get_separate(False) if self._pdf is not None else False
        dwg_sep = self._dwg.get_separate(False) if self._dwg is not None else False
        pdf_opt = self._get_pdf_options(doc)
        dwg_opt = self._get_dwg_options(doc)

        for i, plan in enumerate(plans):
            if progress_cb:
                progress_cb(i, total, 'Collection: {}'.format(plan.collection_name))
            if not plan.do_export:
                if log_cb:
                    log_cb(u"Ignoré: {} (Export=0)".format(plan.collection_name))
                continue
            try:
                if ui_win is not None and ui_comp is not None:
                    ui_comp.set_collection_status(ui_win, plan.collection_name, 'progress')
                    ui_comp.refresh_grid(ui_win)
            except Exception:
                pass

            collection = self._find_collection_by_name(doc, plan.collection_name)
            sheets = self._get_collection_sheets(doc, collection) if collection is not None else []
            base_pdf = self._get_destination_base('PDF', plan.collection_name) if plan.do_pdf else None
            base_dwg = self._get_destination_base('DWG', plan.collection_name) if plan.do_dwg else None

            if plan.per_sheet:
                for sh in sheets:
                    rows = self._get_rows_for_sheet(sh)
                    if plan.do_pdf and base_pdf:
                        try:
                            if ui_win is not None and ui_comp is not None:
                                ui_comp.set_detail_status(ui_win, plan.collection_name, self._safe_sheet_name(sh), 'PDF', 'progress')
                                ui_comp.refresh_grid(ui_win)
                        except Exception:
                            pass
                        self._export_pdf_sheet(doc, sh, rows, base_pdf, pdf_opt, separate=pdf_sep)
                        try:
                            if ui_win is not None and ui_comp is not None:
                                ui_comp.set_detail_status(ui_win, plan.collection_name, self._safe_sheet_name(sh), 'PDF', 'ok')
                                ui_comp.refresh_grid(ui_win)
                        except Exception:
                            pass
                    if plan.do_dwg and base_dwg:
                            try:
                                if ui_win is not None and ui_comp is not None:
                                    ui_comp.set_detail_status(ui_win, plan.collection_name, self._safe_sheet_name(sh), 'DWG', 'progress')
                                    ui_comp.refresh_grid(ui_win)
                            except Exception:
                                pass
                        self._export_dwg_sheet(doc, sh, rows, base_dwg, dwg_opt)
                            try:
                                if ui_win is not None and ui_comp is not None:
                                    ui_comp.set_detail_status(ui_win, plan.collection_name, self._safe_sheet_name(sh), 'DWG', 'ok')
                                    ui_comp.refresh_grid(ui_win)
                            except Exception:
                                pass
            else:
                rows = self._get_rows_for_sheet(sheets[0]) if sheets else [{'Name': plan.collection_name, 'Prefix': '', 'Suffix': ''}]
                if plan.do_pdf and base_pdf:
                        try:
                            if ui_win is not None and ui_comp is not None:
                                name_preview = self._safe_sheet_name(sheets[0]) if sheets else plan.collection_name
                                ui_comp.set_detail_status(ui_win, plan.collection_name, name_preview, 'PDF (combiné)', 'progress')
                                ui_comp.refresh_grid(ui_win)
                        except Exception:
                            pass
                    self._export_pdf_collection(doc, sheets, rows, base_pdf, pdf_opt)
                        try:
                            if ui_win is not None and ui_comp is not None:
                                name_preview = self._safe_sheet_name(sheets[0]) if sheets else plan.collection_name
                                ui_comp.set_detail_status(ui_win, plan.collection_name, name_preview, 'PDF (combiné)', 'ok')
                                ui_comp.refresh_grid(ui_win)
                        except Exception:
                            pass
                if plan.do_dwg and base_dwg:
                    for sh in sheets:
                        rows_sh = self._get_rows_for_sheet(sh)
                            try:
                                if ui_win is not None and ui_comp is not None:
                                    ui_comp.set_detail_status(ui_win, plan.collection_name, self._safe_sheet_name(sh), 'DWG', 'progress')
                                    ui_comp.refresh_grid(ui_win)
                            except Exception:
                                pass
                        self._export_dwg_sheet(doc, sh, rows_sh, base_dwg, dwg_opt)
                            try:
                                if ui_win is not None and ui_comp is not None:
                                    ui_comp.set_detail_status(ui_win, plan.collection_name, self._safe_sheet_name(sh), 'DWG', 'ok')
                                    ui_comp.refresh_grid(ui_win)
                            except Exception:
                                pass

                try:
                    if ui_win is not None and ui_comp is not None:
                        ui_comp.set_collection_status(ui_win, plan.collection_name, 'ok')
                        ui_comp.refresh_grid(ui_win)
                except Exception:
                    pass

        if progress_cb:
            progress_cb(total, max(total, 1), 'Terminé')
        return True

    # ------------------- Helpers noms/export ------------------- #
    def _safe_sheet_name(self, sheet):
        try:
            return sheet.SheetNumber + '_' + sheet.Name
        except Exception:
            try:
                return getattr(sheet, 'Name', 'Sheet')
            except Exception:
                return 'Sheet'

    def _get_rows_for_sheet(self, sheet):
        patt, rows = self._nstore.load('sheet') if self._nstore is not None else ('', [])
        if not rows:
            display_name = None
            try:
                display_name = sheet.SheetNumber + '_' + sheet.Name
            except Exception:
                display_name = getattr(sheet, 'Name', 'Sheet')
            return [{'Name': display_name, 'Prefix': '', 'Suffix': ''}]
        return rows

    def _resolve_name_no_ext(self, elem, rows):
        try:
            s = self._nres.resolve_for_element(elem, rows, empty_fallback=False) if self._nres is not None else ''
            return self._dest.sanitize(s or getattr(elem, 'Name', 'export')) if self._dest is not None else (s or 'export')
        except Exception:
            return 'export'

    def _unique_with_ext(self, folder, file_no_ext, ext):
        try:
            base = os.path.join(folder, file_no_ext + '.' + ext)
            return self._dest.unique_path(base) if self._dest is not None else base
        except Exception:
            return os.path.join(folder, file_no_ext + '.' + ext)

    def _export_pdf_sheet(self, doc, sheet, rows, base_folder, options, separate=True):
        name_no_ext = self._resolve_name_no_ext(sheet, rows)
        try:
            self._dest.ensure(base_folder)
        except Exception:
            pass
        path = self._unique_with_ext(base_folder, name_no_ext, 'pdf')
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

    def _export_dwg_sheet(self, doc, sheet, rows, base_folder, options):
        name_no_ext = self._resolve_name_no_ext(sheet, rows)
        try:
            self._dest.ensure(base_folder)
        except Exception:
            pass
        final_path = self._unique_with_ext(base_folder, name_no_ext, 'dwg')
        tmp_dir = os.path.join(base_folder, '_tmp_dwg')
        try:
            self._dest.ensure(tmp_dir)
        except Exception:
            pass
        ok = False
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

    def _export_pdf_collection(self, doc, sheets, rows, base_folder, options):
        try:
            name_no_ext = self._dest.sanitize('' if not sheets else self._nres.resolve_for_element(sheets[0], rows, empty_fallback=False)) if (self._dest is not None and self._nres is not None) else 'export'
        except Exception:
            name_no_ext = 'export'
        try:
            self._dest.ensure(base_folder)
        except Exception:
            pass
        path = self._unique_with_ext(base_folder, name_no_ext or 'export', 'pdf')
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
