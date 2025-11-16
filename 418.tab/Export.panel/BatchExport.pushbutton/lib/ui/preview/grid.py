# -*- coding: utf-8 -*-

# Aperçu: DataGrid des collections et détails

from ..state import REVIT_API_AVAILABLE, Brushes

# TODO: ce module reste fortement couplé au modèle de données (dictionnaires)


def _get_ancestor_of_type(element, target_type_name):
    # Remonte l'arbre visuel pour trouver un ancêtre de type donné
    try:
        from System.Windows.Media import VisualTreeHelper  # type: ignore
    except Exception:
        VisualTreeHelper = None  # type: ignore
    if element is None or VisualTreeHelper is None:
        return None
    cur = element
    for _ in range(100):
        try:
            parent = VisualTreeHelper.GetParent(cur)
        except Exception:
            parent = None
        if parent is None:
            return None
        try:
            tname = str(type(parent))
            if target_type_name in tname:
                return parent
        except Exception:
            pass
        cur = parent
    return None


def _on_collection_grid_click(win, sender, args):
    # Toggle expand/collapse au clic sur une ligne
    try:
        grid = getattr(win, 'CollectionGrid', None)
        if grid is None:
            return
        src = getattr(args, 'OriginalSource', None)
        if src is None:
            return
        row = _get_ancestor_of_type(src, 'DataGridRow')
        if row is None:
            return
        try:
            item = getattr(row, 'Item', None)
        except Exception:
            item = None
        if not isinstance(item, dict):
            return
        try:
            cur = bool(item.get('IsExpanded', False))
            item['IsExpanded'] = (not cur)
        except Exception:
            return
        _refresh_collection_grid(win)
    except Exception:
        pass


def _refresh_collection_grid(win):
    # Rafraîchit la vue des items (Collections + détails)
    try:
        grid = getattr(win, 'CollectionGrid', None)
        if grid is None:
            return
        try:
            from System.Windows.Data import CollectionViewSource  # type: ignore
            view = CollectionViewSource.GetDefaultView(grid.ItemsSource)
            if view is not None:
                view.Refresh()
            else:
                grid.ItemsSource = list(grid.ItemsSource or [])
        except Exception:
            try:
                grid.Items.Refresh()
            except Exception:
                pass
    except Exception:
        pass


def _set_collection_status(win, collection_name, state):
    # Met à jour le statut d'une collection
    try:
        items = getattr(win, '_preview_items', []) or []
        color = None
        txt = u""
        if state == 'progress':
            txt = u"En cours…"
            color = getattr(Brushes, 'DarkOrange', None) or getattr(Brushes, 'Orange', None) or getattr(Brushes, 'Gray', None)
        elif state == 'ok':
            txt = u"Terminé"
            color = getattr(Brushes, 'Green', None)
        elif state == 'error':
            txt = u"Erreur"
            color = getattr(Brushes, 'Red', None)
        for it in items:
            try:
                if it.get('Nom') == collection_name:
                    it['StatutText'] = txt
                    it['StatutColor'] = color
                    break
            except Exception:
                continue
    except Exception:
        pass


def _set_detail_status(win, collection_name, detail_name, detail_format, state):
    # Met à jour le statut d'un détail (feuille)
    try:
        items = getattr(win, '_preview_items', []) or []
        color = None
        txt = u""
        if state == 'progress':
            txt = u"En cours…"
            color = getattr(Brushes, 'DarkOrange', None) or getattr(Brushes, 'Orange', None) or getattr(Brushes, 'Gray', None)
        elif state == 'ok':
            txt = u"Terminé"
            color = getattr(Brushes, 'Green', None)
        elif state == 'error':
            txt = u"Erreur"
            color = getattr(Brushes, 'Red', None)
        for it in items:
            try:
                if it.get('Nom') != collection_name:
                    continue
                for d in it.get('Details', []) or []:
                    try:
                        if (d.get('Nom') == detail_name) and (d.get('Format') == detail_format):
                            d['StatutText'] = txt
                            d['StatutColor'] = color
                            return
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception:
        pass


def _populate_sheet_sets(win):
    # Remplit le tableau des collections et leurs détails
    try:
        lst = getattr(win, 'CollectionGrid', None)
        try:
            doc = __revit__.ActiveUIDocument.Document  # type: ignore
        except Exception:
            doc = None
        if lst is None or doc is None or not REVIT_API_AVAILABLE:
            return

        try:
            from Autodesk.Revit import DB  # type: ignore
        except Exception:
            DB = None  # type: ignore

        def _collections(document):
            if DB is None:
                return []
            # Try native SheetCollection (if present). If none, fall back to ViewSheetSets via PrintManager.
            try:
                cols = list(DB.FilteredElementCollector(document).OfClass(DB.SheetCollection).ToElements())
            except Exception:
                cols = []
            if cols:
                return cols
            # Fallback: use print manager's saved sheet sets
            sets = []
            try:
                pm = getattr(document, 'PrintManager', None)
                if pm is not None:
                    vss = pm.ViewSheetSetting.ViewSheetSets
                    try:
                        for s in vss:
                            sets.append(s)
                    except Exception:
                        # Try iterator API
                        try:
                            it = vss.ForwardIterator()
                            while it.MoveNext():
                                sets.append(it.Current)
                        except Exception:
                            pass
            except Exception:
                pass
            return sets

        def _sheets_in(document, collection):
            if DB is None:
                return []
            # If collection is a native SheetCollection, filter by SheetCollectionId
            try:
                _ = collection.Id
                # Likely a DB.Element subclass (SheetCollection)
                out = []
                try:
                    for vs in DB.FilteredElementCollector(document).OfClass(DB.ViewSheet).ToElements():
                        try:
                            if getattr(vs, 'SheetCollectionId', None) == collection.Id:
                                out.append(vs)
                        except Exception:
                            continue
                except Exception:
                    pass
                return out
            except Exception:
                pass
            # Otherwise, assume it's a ViewSheetSet (from PrintManager)
            try:
                vset = None
                # Some API versions expose Views; others use GetViewSet()
                try:
                    vset = collection.Views
                except Exception:
                    try:
                        vset = collection.GetViewSet()
                    except Exception:
                        vset = None
                out = []
                if vset is not None:
                    try:
                        for v in vset:
                            try:
                                if isinstance(v, DB.ViewSheet):
                                    out.append(v)
                            except Exception:
                                # Fall back to type name check
                                try:
                                    if 'ViewSheet' in str(type(v)):
                                        out.append(v)
                                except Exception:
                                    pass
                    except Exception:
                        pass
                return out
            except Exception:
                return []

        from ...naming import load_pattern, resolve_rows_for_element  # type: ignore
        try:
            _, sheet_rows = load_pattern('sheet')
        except Exception:
            sheet_rows = []
        from ...destination import sanitize_filename  # type: ignore

        items = []
        cols = _collections(doc)
        cols_sorted = sorted(cols, key=lambda c: (getattr(c, 'Name', '') or '').lower())

        # Récupérer les sélections courantes via win (helpers importés ailleurs)
        try:
            from ..params.combo_state import _get_selected_values  # lazy import pour éviter cycles
            selected = _get_selected_values(win)
        except Exception:
            selected = {}
        pname_export = selected.get('ExportationCombo')
        pname_carnet = selected.get('CarnetCombo')
        pname_dwg = selected.get('DWGCombo')

        def _read_flag(elem, pname, default=False):
            if not pname:
                return default
            try:
                for p in elem.Parameters:
                    try:
                        d = getattr(p, 'Definition', None)
                        if d is not None and d.Name == pname:
                            try:
                                v = p.AsInteger()
                                return bool(v)
                            except Exception:
                                return default
                    except Exception:
                        continue
            except Exception:
                pass
            return default

        for coll in cols_sorted:
            try:
                # If the collection doesn't carry parameters (e.g., ViewSheetSet), use permissive defaults to show data
                has_params = hasattr(coll, 'Parameters')
                do_export = _read_flag(coll, pname_export, False) if has_params else True
                per_sheet = _read_flag(coll, pname_carnet, False) if has_params else True
                do_dwg = _read_flag(coll, pname_dwg, False) if has_params else False
                do_pdf = bool(do_export)
                sheets = _sheets_in(doc, coll)

                details = []
                if do_pdf:
                    if per_sheet:
                        for sh in sheets:
                            try:
                                base = sanitize_filename(resolve_rows_for_element(sh, sheet_rows, empty_fallback=False)) or getattr(sh, 'Name', 'Sheet')
                                details.append({'Nom': base, 'Format': 'PDF', 'StatutText': u'', 'StatutColor': Brushes.Green if Brushes is not None else None})
                            except Exception:
                                continue
                    else:
                        base = ''
                        try:
                            if sheets:
                                base = sanitize_filename(resolve_rows_for_element(sheets[0], sheet_rows, empty_fallback=False))
                        except Exception:
                            base = ''
                        if not base:
                            try:
                                base = getattr(coll, 'Name', '') or getattr(coll, 'name', '') or ''
                            except Exception:
                                base = ''
                        details.append({'Nom': base, 'Format': 'PDF (combiné)', 'StatutText': u'', 'StatutColor': Brushes.Green if Brushes is not None else None})
                if do_dwg:
                    for sh in sheets:
                        try:
                            base = sanitize_filename(resolve_rows_for_element(sh, sheet_rows, empty_fallback=False)) or getattr(sh, 'Name', 'Sheet')
                            details.append({'Nom': base, 'Format': 'DWG', 'StatutText': u'', 'StatutColor': Brushes.Green if Brushes is not None else None})
                        except Exception:
                            continue

                try:
                    details.sort(key=lambda d: (d.get('Nom','') or '').lower())
                except Exception:
                    pass

                items.append({
                    'Nom': getattr(coll, 'Name', '') or getattr(coll, 'name', '') or 'Set',
                    'Feuilles': len(sheets),
                    'ExportText': u"\u2713" if do_pdf else u"\u2717",
                    'ExportColor': Brushes.Green if (Brushes is not None and do_pdf) else (Brushes.Gray if Brushes is not None else None),
                    'CarnetText': u"\u2713" if per_sheet else u"\u2717",
                    'CarnetColor': Brushes.Green if (Brushes is not None and per_sheet) else (Brushes.Gray if Brushes is not None else None),
                    'DWGText': u"\u2713" if do_dwg else u"\u2717",
                    'DWGColor': Brushes.Green if (Brushes is not None and do_dwg) else (Brushes.Gray if Brushes is not None else None),
                    'StatutText': u"",
                    'StatutColor': Brushes.Green if False else None,
                    'IsExpanded': False,
                    'Details': details,
                })
            except Exception:
                continue

        try:
            items.sort(key=lambda i: (i.get('Nom','') or '').lower())
        except Exception:
            pass

        try:
            win._preview_items = items
        except Exception:
            win._preview_items = items
        try:
            counter = getattr(win, 'PreviewCounterText', None)
            if counter is not None:
                ncoll = len(items)
                nelems = sum(len(it.get('Details', []) or []) for it in items)
                counter.Text = u"Collections: {} • Éléments: {}".format(ncoll, nelems)
        except Exception:
            pass
        try:
            lst.ItemsSource = win._preview_items
        except Exception:
            pass
    except Exception:
        pass
