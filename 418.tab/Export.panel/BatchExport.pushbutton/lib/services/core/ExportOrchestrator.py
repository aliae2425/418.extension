# -*- coding: utf-8 -*-
# Orchestrateur d'export: exécute les exports PDF/DWG par collection.

from __future__ import unicode_literals

import os
import tempfile
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
    def __init__(self, namespace='batch_export', config=None):
        # Config utilisateur. `config` INJECTE l'instance UserConfig partagée
        # du ViewModel : indispensable pour que l'orchestrateur lise les MÊMES
        # valeurs (flags de séparation, motifs de nommage) que celles écrites
        # par le VM/la modale. Sans injection, l'orchestrateur crée sa propre
        # UserConfig qui, en contexte pyRevit, lit '<absent>' (instances de
        # config distinctes) -> séparation ignorée + carnet nommé par repli.
        self._external_cfg = config
        if config is not None:
            self._cfg = config
        else:
            try:
                from core.UserConfig import UserConfig
            except Exception:
                try:
                    from lib.core.UserConfig import UserConfig
                except Exception:
                    UserConfig = None  # type: ignore
            self._cfg = UserConfig(namespace) if UserConfig is not None else None
        # Services
        try:
            from services.formats.PdfExporterService import PdfExporterService
            from services.formats.DwgExporterService import DwgExporterService
        except Exception:
            try:
                from lib.services.formats.PdfExporterService import PdfExporterService
                from lib.services.formats.DwgExporterService import DwgExporterService
            except Exception:
                PdfExporterService = None  # type: ignore
                DwgExporterService = None  # type: ignore
        # Injecter aussi la config partagée dans les services PDF/DWG : ils
        # lisent le SETUP d'impression (get_saved_setup) et l'option "séparer
        # par vue" depuis la config -> même bug '<absent>' que les flags sans
        # injection (PDF exporté avec un setup PAR DÉFAUT, page/couleurs fausses).
        self._pdf = PdfExporterService(config=config) if PdfExporterService is not None else None
        self._dwg = DwgExporterService(config=config) if DwgExporterService is not None else None
        # Données auxiliaires
        try:
            from services.DestinationService import DestinationService
            from data.naming.NamingPatternStore import NamingPatternStore
            from data.naming.NamingResolver import NamingResolver
        except Exception:
            try:
                from lib.services.DestinationService import DestinationService
                from lib.data.naming.NamingPatternStore import NamingPatternStore
                from lib.data.naming.NamingResolver import NamingResolver
            except Exception:
                DestinationService = None  # type: ignore
                NamingPatternStore = None  # type: ignore
                NamingResolver = None  # type: ignore
        self._dest = DestinationService(config=config) if DestinationService is not None else None
        self._nstore = NamingPatternStore(config=config) if NamingPatternStore is not None else None
        self._nres = None  # Sera initialisé avec le doc dans run()
        self._NamingResolver_cls = NamingResolver
        self._destination_override = None  # Chemin passé explicitement depuis le ViewModel
        # NamingService : résout les motifs à JETONS ({numero}, {titre}, ...).
        # Contrairement à NamingResolver (rows uniquement), il comprend les
        # chaînes à jetons enregistrées par la modale de nommage. Initialisé
        # avec le doc dans run()/run_manual(). C'est LA source de nommage.
        try:
            from services.NamingService import NamingService
        except Exception:
            try:
                from lib.services.NamingService import NamingService
            except Exception:
                NamingService = None  # type: ignore
        self._NamingService_cls = NamingService
        self._naming = None
        self._log_cb = None  # câblé pendant run() pour le diagnostic destination

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
            # Inverser la logique : si le param Carnet est True = compiler (per_sheet=False), si False = par feuille (per_sheet=True)
            carnet_flag = self._read_flag_from_param(coll, pname_per_sheet, default=False) if pname_per_sheet else False
            per_sheet = not carnet_flag  # Inversion : True dans le paramètre = carnet = per_sheet False
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
            if self._destination_override:
                base = self._destination_override
            else:
                base = self._dest.get()
        except Exception:
            base = None
        base = base or os.getcwd()

        # Lecture des flags de séparation.
        sub = False
        sep = False
        try:
            sub = bool(self._dest.get_create_subfolders())
        except Exception:
            sub = False
        try:
            sep = bool(self._dest.get_separate_formats())
        except Exception:
            sep = False

        # Diagnostic (#2 séparation) : loguer la valeur BRUTE persistée + le
        # résultat booléen, pour discriminer write-side / read-side / comparaison.
        try:
            if self._log_cb is not None:
                raw_sub = self._dest._cfg.get('create_subfolders', '<absent>') if getattr(self._dest, '_cfg', None) is not None else '<no cfg>'
                raw_sep = self._dest._cfg.get('separate_format_folders', '<absent>') if getattr(self._dest, '_cfg', None) is not None else '<no cfg>'
                self._log_cb(u"[DEST] create_subfolders brut={!r} -> {} | separate_format_folders brut={!r} -> {}".format(
                    raw_sub, sub, raw_sep, sep))
        except Exception:
            pass

        if sub and collection_name:
            base = os.path.join(base, collection_name)
        if sep and fmt_subfolder:
            base = os.path.join(base, fmt_subfolder)
        try:
            if self._log_cb is not None:
                self._log_cb(u"[DEST] base={!r} (collection={!r}, fmt={!r})".format(base, collection_name, fmt_subfolder))
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

    # ------------------- Détection des fichiers existants ------------------- #
    def _detect_existing_files(self, doc, plans):
        for plan in plans:
            if not plan.do_export: continue
            
            collection = self._find_collection_by_name(doc, plan.collection_name)
            sheets = self._get_collection_sheets(doc, collection) if collection else []
            # Tri des feuilles par numéro croissant
            try:
                sheets = sorted(sheets, key=lambda sh: u'{}'.format(getattr(sh, 'SheetNumber', '') or ''))
            except Exception:
                pass
            
            base_pdf = self._get_destination_base('PDF', plan.collection_name) if plan.do_pdf else None
            base_dwg = self._get_destination_base('DWG', plan.collection_name) if plan.do_dwg else None
            
            # Check PDF
            if plan.do_pdf and base_pdf:
                if plan.per_sheet:
                    for sh in sheets:
                        rows = self._get_rows_for_sheet(sh)
                        name = self._resolve_name_no_ext(sh, rows)
                        if os.path.exists(os.path.join(base_pdf, name + '.pdf')): return True
                else:
                    # Collection PDF (carnet) : même nommage qu'à l'export réel.
                    name = self._resolve_name(
                        collection, 'set',
                        fallback=self._collection_fallback_name(collection, sheets))
                    if os.path.exists(os.path.join(base_pdf, name + '.pdf')): return True

            # Check DWG (always per sheet)
            if plan.do_dwg and base_dwg:
                for sh in sheets:
                    rows = self._get_rows_for_sheet(sh)
                    name = self._resolve_name_no_ext(sh, rows)
                    if os.path.exists(os.path.join(base_dwg, name + '.dwg')): return True
                    
        return False

    # ------------------- Exécution ------------------- #
    def run(self, doc, get_ctrl, progress_cb=None, log_cb=None, ui_win=None, destination=None):
        self._destination_override = destination or None
        try:
            return self._run_impl(doc, get_ctrl, progress_cb=progress_cb, log_cb=log_cb, ui_win=ui_win)
        finally:
            self._destination_override = None

    def _run_impl(self, doc, get_ctrl, progress_cb=None, log_cb=None, ui_win=None):
        self._log_cb = log_cb
        # Initialiser le NamingResolver (legacy, rows) et le NamingService
        # (jetons) avec le document.
        if self._NamingResolver_cls is not None and self._nres is None:
            try:
                self._nres = self._NamingResolver_cls(doc)
            except Exception:
                self._nres = None
        if self._NamingService_cls is not None and self._naming is None:
            try:
                self._naming = self._NamingService_cls(doc, config=self._external_cfg)
            except Exception:
                self._naming = None
        
        plans = self.plan_exports_for_collections(doc, get_ctrl)

        # Diagnostic immédiat si aucun plan ne qualifie
        qualifying = [p for p in plans if p.do_export]
        if not qualifying:
            if log_cb:
                try:
                    if not plans:
                        log_cb(u"Aucun jeu de feuilles trouvé dans ce document.")
                    else:
                        log_cb(
                            u"Aucun jeu qualifié pour l'export ({} jeu(x) trouvé(s), "
                            u"tous exclus par le mappage des paramètres). "
                            u"Vérifiez les paramètres Export/Carnet/DWG dans Réglages.".format(len(plans))
                        )
                except Exception:
                    pass
            if progress_cb:
                try:
                    progress_cb(0, 1, u"Aucun export — voir statut.")
                except Exception:
                    pass
            return True

        total = len(plans)

        # --- Check existing files ---
        overwrite = False
        try:
            if self._detect_existing_files(doc, plans):
                from pyrevit import forms
                res = forms.alert(
                    "Des fichiers existent déjà.\nVoulez-vous les remplacer ?",
                    options=["Remplacer", "Renommer (garder les deux)"],
                    footer="Les fichiers existants seront écrasés si vous choisissez Remplacer."
                )
                if res == "Remplacer":
                    overwrite = True
        except Exception:
            pass
        # ----------------------------

        if progress_cb:
            progress_cb(0, max(total, 1), 'Préparation...')

        # Remove non-error logs

        pdf_sep = self._pdf.get_separate(False) if self._pdf is not None else False
        dwg_sep = self._dwg.get_separate(False) if self._dwg is not None else False
        # Diagnostic : confirmer que les services PDF/DWG lisent bien le SETUP
        # depuis la config injectée (et non '<absent>' -> setup par défaut).
        try:
            if self._log_cb is not None:
                self._log_cb(u"[SETUP] pdf={!r} dwg={!r}".format(
                    self._pdf.get_saved_setup() if self._pdf is not None else None,
                    self._dwg.get_saved_setup() if self._dwg is not None else None))
        except Exception:
            pass
        pdf_opt = self._get_pdf_options(doc)
        dwg_opt = self._get_dwg_options(doc)

        for i, plan in enumerate(plans):
            if progress_cb:
                progress_cb(i, total, 'Collection: {}'.format(plan.collection_name))
            if not plan.do_export:
                continue

            collection = self._find_collection_by_name(doc, plan.collection_name)
            sheets = self._get_collection_sheets(doc, collection) if collection is not None else []
            # Tri des feuilles par numéro croissant
            try:
                sheets = sorted(sheets, key=lambda sh: u'{}'.format(getattr(sh, 'SheetNumber', '') or ''))
            except Exception:
                pass
            base_pdf = self._get_destination_base('PDF', plan.collection_name) if plan.do_pdf else None
            base_dwg = self._get_destination_base('DWG', plan.collection_name) if plan.do_dwg else None

            if plan.per_sheet:
                for sh in sheets:
                    rows = self._get_rows_for_sheet(sh)
                    if plan.do_pdf and base_pdf:
                        if progress_cb:
                            try:
                                progress_cb(i, total, u'{}: {} (PDF)'.format(plan.collection_name, self._safe_sheet_name(sh)))
                            except Exception:
                                pass
                        ok, path = self._export_pdf_sheet(doc, sh, rows, base_pdf, pdf_opt, separate=pdf_sep, overwrite=overwrite, log_cb=log_cb)
                    if plan.do_dwg and base_dwg:
                        if progress_cb:
                            try:
                                progress_cb(i, total, u'{}: {} (DWG)'.format(plan.collection_name, self._safe_sheet_name(sh)))
                            except Exception:
                                pass
                        ok, path = self._export_dwg_sheet(doc, sh, rows, base_dwg, dwg_opt, overwrite=overwrite, log_cb=log_cb)
            else:
                # Utiliser le pattern 'set' (carnet) s'il existe, sinon fallback sur sheet/default
                rows = self._get_rows_for_set()
                if not rows:
                    rows = self._get_rows_for_sheet(sheets[0]) if sheets else [{'Name': plan.collection_name, 'Prefix': '', 'Suffix': ''}]

                if plan.do_pdf and base_pdf:
                    if progress_cb:
                        try:
                            progress_cb(i, total, u'{}: PDF (combiné)'.format(plan.collection_name))
                        except Exception:
                            pass
                    ok, path = self._export_pdf_collection(doc, sheets, rows, base_pdf, pdf_opt, collection=collection, overwrite=overwrite, log_cb=log_cb)
                if plan.do_dwg and base_dwg:
                    for sh in sheets:
                        rows_sh = self._get_rows_for_sheet(sh)
                        if progress_cb:
                            try:
                                progress_cb(i, total, u'{}: {} (DWG)'.format(plan.collection_name, self._safe_sheet_name(sh)))
                            except Exception:
                                pass
                        ok, path = self._export_dwg_sheet(doc, sh, rows_sh, base_dwg, dwg_opt, overwrite=overwrite, log_cb=log_cb)

        if progress_cb:
            progress_cb(total, max(total, 1), u'')
        return True

    def run_manual(self, doc, sheet_vms, combine_pdf=False, pdf_title=u'',
                   progress_cb=None, log_cb=None, destination=None):
        """Export manuel : feuilles sélectionnées une par une (ou PDF combiné).

        sheet_vms  : liste de ManualSheetVM (ExportPdf / ExportDwg / Elem / Numero).
        combine_pdf: fusionner toutes les feuilles PDF en un seul fichier.
        pdf_title  : nom du fichier PDF combiné (ignoré si combine_pdf=False).
        destination: chemin de destination explicite (prioritaire sur DestinationService).
        """
        self._destination_override = destination or None
        try:
            return self._run_manual_impl(doc, sheet_vms, combine_pdf=combine_pdf,
                                         pdf_title=pdf_title, progress_cb=progress_cb,
                                         log_cb=log_cb)
        finally:
            self._destination_override = None

    def _run_manual_impl(self, doc, sheet_vms, combine_pdf=False, pdf_title=u'',
                         progress_cb=None, log_cb=None):
        self._log_cb = log_cb
        if self._NamingResolver_cls is not None and self._nres is None:
            try:
                self._nres = self._NamingResolver_cls(doc)
            except Exception:
                self._nres = None
        if self._NamingService_cls is not None and self._naming is None:
            try:
                self._naming = self._NamingService_cls(doc, config=self._external_cfg)
            except Exception:
                self._naming = None

        pdf_vms = [s for s in (sheet_vms or []) if s.ExportPdf]
        dwg_vms = [s for s in (sheet_vms or []) if s.ExportDwg]
        total = len(pdf_vms) + len(dwg_vms)

        if progress_cb:
            progress_cb(0, max(total, 1), u'Préparation...')

        pdf_opt = self._get_pdf_options(doc)
        dwg_opt = self._get_dwg_options(doc)
        pdf_sep = self._pdf.get_separate(False) if self._pdf is not None else False

        done = 0

        if pdf_vms:
            base_pdf = self._get_destination_base('PDF', None)
            if combine_pdf:
                elems = [s.Elem for s in pdf_vms if s.Elem is not None]
                rows = [{'Name': pdf_title or u'export', 'Prefix': u'', 'Suffix': u''}]
                if progress_cb:
                    progress_cb(done, max(total, 1), u'PDF combiné...')
                ok, path = self._export_pdf_collection(doc, elems, rows, base_pdf, pdf_opt, log_cb=log_cb)
                done += len(pdf_vms)
            else:
                for svm in pdf_vms:
                    if svm.Elem is None:
                        done += 1
                        continue
                    rows = self._get_rows_for_sheet(svm.Elem)
                    if progress_cb:
                        try:
                            progress_cb(done, max(total, 1), u'{} (PDF)'.format(svm.Numero))
                        except Exception:
                            pass
                    ok, path = self._export_pdf_sheet(doc, svm.Elem, rows, base_pdf, pdf_opt,
                                                      separate=pdf_sep, log_cb=log_cb)
                    done += 1

        for svm in dwg_vms:
            if svm.Elem is None:
                done += 1
                continue
            rows = self._get_rows_for_sheet(svm.Elem)
            base_dwg = self._get_destination_base('DWG', None)
            if progress_cb:
                try:
                    progress_cb(done, max(total, 1), u'{} (DWG)'.format(svm.Numero))
                except Exception:
                    pass
            ok, path = self._export_dwg_sheet(doc, svm.Elem, rows, base_dwg, dwg_opt, log_cb=log_cb)
            done += 1

        if progress_cb:
            progress_cb(total, max(total, 1), u'')
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

    def _get_rows_for_set(self):
        patt, rows = self._nstore.load('set') if self._nstore is not None else ('', [])
        return rows

    def _collection_fallback_name(self, collection, sheets=None):
        """Nom de repli d'un carnet quand le motif 'set' est absent/vide :
        le NOM (titre) de la collection. Repli ultime : nom de la 1re feuille."""
        try:
            nm = getattr(collection, 'Name', None)
            if nm and nm.strip():
                return nm
        except Exception:
            pass
        try:
            if sheets:
                return self._safe_sheet_name(sheets[0])
        except Exception:
            pass
        return u'export'

    def _resolve_name(self, elem, kind, fallback=u''):
        """Résout le nom de fichier (sans extension) pour `elem` à partir du
        MOTIF À JETONS enregistré pour `kind` ('sheet' ou 'set'), via
        NamingService (qui comprend les chaînes `{...}` ; NamingResolver, lui,
        n'itère que des rows et ne peut PAS résoudre un motif à jetons -> c'est
        la cause du carnet nommé 'untitled'). Repli sur `fallback` (nom LITTÉRAL,
        pas un lookup de paramètre) si le motif est absent ou résout vide.
        Toujours assaini via DestinationService.sanitize."""
        pattern = u''
        try:
            if self._naming is not None:
                pattern = self._naming.load(kind)[0] or u''
        except Exception:
            pattern = u''
        name = u''
        if pattern and elem is not None:
            try:
                name = self._naming.resolve_for_element(elem, pattern) or u''
            except Exception:
                name = u''
        if not name or not name.strip():
            name = fallback or u''
        if self._dest is not None:
            return self._dest.sanitize(name)
        return name or u'untitled'

    def _resolve_name_no_ext(self, elem, rows):
        """Nom (sans extension) d'une FEUILLE. Résout le motif 'sheet' à jetons
        via NamingService, repli sur `SheetNumber_Name`. Le paramètre `rows`
        (legacy) est conservé pour compat d'appel mais n'est plus la source du
        nommage -- les rows sont vides avec le nouveau système à jetons, ce qui
        rendait le nom vide (cf. bug carnet 'untitled')."""
        return self._resolve_name(elem, 'sheet', fallback=self._safe_sheet_name(elem))

    def _unique_with_ext(self, folder, file_no_ext, ext, overwrite=False):
        try:
            base = os.path.join(folder, file_no_ext + '.' + ext)
            if overwrite:
                return base
            return self._dest.unique_path(base) if self._dest is not None else base
        except Exception:
            return os.path.join(folder, file_no_ext + '.' + ext)

    def _export_pdf_sheet(self, doc, sheet, rows, base_folder, options, separate=True, overwrite=False, log_cb=None):
        def _log(msg):
            if log_cb:
                try:
                    log_cb(msg)
                except Exception:
                    pass
        label = self._safe_sheet_name(sheet)
        name_no_ext = self._resolve_name_no_ext(sheet, rows)
        try:
            self._dest.ensure(base_folder)
        except Exception:
            pass
        path = self._unique_with_ext(base_folder, name_no_ext, 'pdf', overwrite=overwrite)
        folder = os.path.dirname(path)
        file_no_ext = os.path.splitext(os.path.basename(path))[0]
        ok = False
        try:
            if DB is not None and hasattr(DB, 'PDFExportOptions') and options is not None:
                try:
                    from System.Collections.Generic import List as Clist  # type: ignore
                    views = Clist[DB.ElementId]()
                    views.Add(sheet.Id)
                except Exception as _ve:
                    _log(u"PDF [{}] : préparation vues : {}".format(label, _ve))
                    views = None
                try:
                    if hasattr(options, 'Combine'):
                        # Toujours combiner pour forcer l'utilisation du FileName exact
                        # (sinon Revit utilise FileName comme préfixe)
                        options.Combine = True
                except Exception:
                    pass
                try:
                    if hasattr(options, 'FileName'):
                        options.FileName = file_no_ext
                except Exception:
                    pass
                _log(u"PDF [{}] : dossier={!r} | fichier={!r}".format(label, folder, file_no_ext))
                if views is not None:
                    try:
                        raw = doc.Export(folder, views, options)
                        ok = bool(raw)
                        _log(u"PDF [{}] : retour Export={!r} ok={}".format(label, raw, ok))
                        if ok:
                            expected = os.path.join(folder, file_no_ext + '.pdf')
                            _log(u"PDF [{}] : fichier existe={} path={!r}".format(label, os.path.exists(expected), expected))
                    except Exception as _e1:
                        _log(u"PDF [{}] : Export 3-arg echoue : {}".format(label, _e1))
                        try:
                            raw = doc.Export(folder, file_no_ext, views, options)
                            ok = bool(raw)
                            _log(u"PDF [{}] : retour Export 4-arg={!r} ok={}".format(label, raw, ok))
                        except Exception as _e2:
                            _log(u"PDF [{}] : Export API : {} / {}".format(label, _e1, _e2))
                            ok = False
            elif options is None:
                _log(u"PDF [{}] : options d'export non disponibles (PDFExportOptions introuvable ou config vide).".format(label))
        except Exception as _e:
            _log(u"PDF [{}] : erreur inattendue : {}".format(label, _e))
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
            except Exception as _e:
                _log(u"PDF [{}] : PrintManager fallback : {}".format(label, _e))
                ok = False
        return ok, path

    def _export_dwg_sheet(self, doc, sheet, rows, base_folder, options, overwrite=False, log_cb=None):
        def _log(msg):
            if log_cb:
                try:
                    log_cb(msg)
                except Exception:
                    pass
        label = self._safe_sheet_name(sheet)
        name_no_ext = self._resolve_name_no_ext(sheet, rows)
        try:
            self._dest.ensure(base_folder)
        except Exception:
            pass
        final_path = self._unique_with_ext(base_folder, name_no_ext, 'dwg', overwrite=overwrite)
        try:
            tmp_dir = tempfile.mkdtemp(prefix='batchexport_dwg_')
        except Exception:
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

                # Force MergedViews to True to ensure single file output (no XREFs)
                try:
                    options.MergedViews = True
                except Exception:
                    pass

                # DWG export requires a prefix name in most overloads
                _log(u"DWG [{}] : tmp_dir={!r}".format(label, tmp_dir))
                raw = doc.Export(tmp_dir, "export", views, options)
                ok = bool(raw)
                _log(u"DWG [{}] : retour Export={!r} ok={}".format(label, raw, ok))
                if ok:
                    _log(u"DWG [{}] : contenu tmp_dir={}".format(label, os.listdir(tmp_dir) if os.path.isdir(tmp_dir) else 'ABSENT'))
            elif options is None:
                _log(u"DWG [{}] : options d'export non disponibles (DWGExportOptions introuvable ou config vide).".format(label))
        except Exception as _e:
            _log(u"DWG [{}] : Export API : {}".format(label, _e))
            ok = False
        
        try:
            if ok:
                # Prioritize the main file "export.dwg"
                exported_file = None
                expected_main = os.path.join(tmp_dir, "export.dwg")

                if os.path.exists(expected_main):
                    exported_file = expected_main
                else:
                    # Fallback: pick the most recent DWG
                    cands = [os.path.join(tmp_dir, f) for f in os.listdir(tmp_dir) if f.lower().endswith('.dwg')]
                    if cands:
                        cands.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                        exported_file = cands[0]

                if exported_file:
                    try:
                        if os.path.exists(final_path):
                            os.remove(final_path)
                        os.rename(exported_file, final_path)
                    except Exception:
                        import shutil
                        shutil.copy2(exported_file, final_path)
                        try:
                            os.remove(exported_file)
                        except Exception:
                            pass

                    # Copy referenced raster files from tmp to final folder to preserve XREFs
                    try:
                        import shutil
                        exts = {'.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.gif'}
                        for root, dirs, files in os.walk(tmp_dir):
                            rel = os.path.relpath(root, tmp_dir)
                            dest_root = base_folder if rel == '.' else os.path.join(base_folder, rel)
                            try:
                                self._dest.ensure(dest_root)
                            except Exception:
                                pass
                            for fn in files:
                                ext = os.path.splitext(fn)[1].lower()
                                if ext in exts:
                                    src = os.path.join(root, fn)
                                    dst = os.path.join(dest_root, fn)
                                    try:
                                        shutil.copy2(src, dst)
                                    except Exception:
                                        try:
                                            shutil.copy(src, dst)
                                        except Exception:
                                            pass
                    except Exception:
                        pass
        except Exception:
            ok = False
            
        try:
            if os.path.isdir(tmp_dir):
                import shutil
                shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass
        return ok, final_path

    def _export_pdf_collection(self, doc, sheets, rows, base_folder, options, collection=None, overwrite=False, log_cb=None):
        def _log(msg):
            if log_cb:
                try:
                    log_cb(msg)
                except Exception:
                    pass
        # Nommage du PDF combiné, selon le contexte :
        #  - AUTO (carnet) : `collection` fournie -> résoudre le motif 'set' à
        #    jetons via NamingService, repli sur le titre de la collection.
        #  - MANUEL (combiné) : `collection` None -> le nom est un TITRE
        #    LITTÉRAL saisi par l'utilisateur, passé dans `rows[0]['Name']`
        #    (à NE PAS résoudre comme un paramètre : c'était la cause du
        #    'untitled' côté manuel aussi).
        try:
            if collection is not None:
                name_no_ext = self._resolve_name(
                    collection, 'set',
                    fallback=self._collection_fallback_name(collection, sheets))
            else:
                literal = u''
                try:
                    literal = (rows[0].get('Name') if rows else u'') or u''
                except Exception:
                    literal = u''
                name_no_ext = self._dest.sanitize(literal or u'export') if self._dest is not None else (literal or u'export')
        except Exception:
            name_no_ext = u'export'
        try:
            self._dest.ensure(base_folder)
        except Exception:
            pass
        path = self._unique_with_ext(base_folder, name_no_ext or 'export', 'pdf', overwrite=overwrite)
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
                _log(u"PDF combiné [{}] : dossier={!r} | fichier={!r}".format(file_no_ext, folder, file_no_ext))
                try:
                    raw = doc.Export(folder, views, options)
                    ok = bool(raw)
                    _log(u"PDF combiné [{}] : retour Export={!r} ok={}".format(file_no_ext, raw, ok))
                    if ok:
                        expected = os.path.join(folder, file_no_ext + '.pdf')
                        _log(u"PDF combiné [{}] : fichier existe={} path={!r}".format(file_no_ext, os.path.exists(expected), expected))
                except Exception as _e1:
                    _log(u"PDF combiné [{}] : Export 3-arg echoue : {}".format(file_no_ext, _e1))
                    try:
                        raw = doc.Export(folder, file_no_ext, views, options)
                        ok = bool(raw)
                        _log(u"PDF combiné [{}] : retour Export 4-arg={!r} ok={}".format(file_no_ext, raw, ok))
                    except Exception as _e2:
                        _log(u"PDF combiné [{}] : Export API : {} / {}".format(file_no_ext, _e1, _e2))
                        ok = False
            elif options is None:
                _log(u"PDF combiné : options d'export non disponibles.")
            elif not sheets:
                _log(u"PDF combiné : aucune feuille à exporter.")
        except Exception as _e:
            _log(u"PDF combiné : erreur inattendue : {}".format(_e))
            ok = False
        return ok, path
