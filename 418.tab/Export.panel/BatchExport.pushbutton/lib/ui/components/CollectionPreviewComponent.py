# -*- coding: utf-8 -*-
# Composant UI: tableau de prévisualisation des collections

class CollectionPreviewComponent(object):
    def __init__(self):
        pass

    def populate(self, win, selected_names):
        try:
            from Autodesk.Revit import DB  # type: ignore
        except Exception:
            DB = None  # type: ignore
        try:
            from System.Windows.Media import Brushes  # type: ignore
        except Exception:
            Brushes = None  # type: ignore
        try:
            doc = __revit__.ActiveUIDocument.Document  # type: ignore
        except Exception:
            doc = None
        if DB is None or doc is None:
            try:
                win._preview_items = []
                if getattr(win, 'CollectionGrid', None) is not None:
                    win.CollectionGrid.ItemsSource = win._preview_items
            except Exception:
                pass
            return

        def _collections(document):
            try:
                return list(DB.FilteredElementCollector(document).OfClass(DB.SheetCollection).ToElements())
            except Exception:
                return []

        def _sheets_in(document, collection):
            out = []
            try:
                for vs in DB.FilteredElementCollector(document).OfClass(DB.ViewSheet).ToElements():
                    try:
                        if vs.SheetCollectionId == collection.Id:
                            out.append(vs)
                    except Exception:
                        continue
            except Exception:
                pass
            return out

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

        # Récup rows de nommage pour aperçu
        try:
            from ...data.naming.NamingPatternStore import NamingPatternStore
            from ...data.naming.NamingResolver import NamingResolver
            from ...data.destination.DestinationStore import DestinationStore
            nstore = NamingPatternStore()
            nres = NamingResolver()
            dest = DestinationStore()
            _, sheet_rows = nstore.load('sheet')
        except Exception:
            sheet_rows = []
            nres = None
            dest = None

        def _name_for(viewsheet):
            try:
                base = nres.resolve_for_element(viewsheet, sheet_rows, empty_fallback=False) if nres is not None else ''
                base = dest.sanitize(base) if (dest is not None and base) else base
                if not base:
                    base = getattr(viewsheet, 'Name', 'Sheet')
                return base
            except Exception:
                return getattr(viewsheet, 'Name', 'Sheet')

        pname_export = selected_names.get('ExportationCombo')
        pname_carnet = selected_names.get('CarnetCombo')
        pname_dwg = selected_names.get('DWGCombo')

        items = []
        cols = _collections(doc)
        cols_sorted = sorted(cols, key=lambda c: (getattr(c, 'Name', '') or '').lower())
        for coll in cols_sorted:
            try:
                do_export = _read_flag(coll, pname_export, False)
                per_sheet = _read_flag(coll, pname_carnet, False)
                do_dwg = _read_flag(coll, pname_dwg, False)
                do_pdf = bool(do_export)
                sheets = _sheets_in(doc, coll)

                details = []
                if do_pdf:
                    if per_sheet:
                        for sh in sheets:
                            try:
                                base = _name_for(sh)
                                details.append({'Nom': base, 'Format': 'PDF', 'StatutText': u'', 'StatutColor': getattr(Brushes, 'Green', None) if Brushes is not None else None})
                            except Exception:
                                continue
                    else:
                        base = ''
                        try:
                            if sheets:
                                base = _name_for(sheets[0])
                        except Exception:
                            base = ''
                        if not base:
                            base = coll.Name
                        details.append({'Nom': base, 'Format': 'PDF (combiné)', 'StatutText': u'', 'StatutColor': getattr(Brushes, 'Green', None) if Brushes is not None else None})
                if do_dwg:
                    for sh in sheets:
                        try:
                            base = _name_for(sh)
                            details.append({'Nom': base, 'Format': 'DWG', 'StatutText': u'', 'StatutColor': getattr(Brushes, 'Green', None) if Brushes is not None else None})
                        except Exception:
                            continue

                try:
                    details.sort(key=lambda d: (d.get('Nom','') or '').lower())
                except Exception:
                    pass

                items.append({
                    'Nom': coll.Name,
                    'Feuilles': len(sheets),
                    'ExportText': u"\u2713" if do_pdf else u"\u2717",
                    'ExportColor': getattr(Brushes, 'Green', None) if (Brushes is not None and do_pdf) else (getattr(Brushes, 'Gray', None) if Brushes is not None else None),
                    'CarnetText': u"\u2713" if per_sheet else u"\u2717",
                    'CarnetColor': getattr(Brushes, 'Green', None) if (Brushes is not None and per_sheet) else (getattr(Brushes, 'Gray', None) if Brushes is not None else None),
                    'DWGText': u"\u2713" if do_dwg else u"\u2717",
                    'DWGColor': getattr(Brushes, 'Green', None) if (Brushes is not None and do_dwg) else (getattr(Brushes, 'Gray', None) if Brushes is not None else None),
                    'StatutText': u"",
                    'StatutColor': None,
                    'Details': details,
                    'IsExpanded': False,
                })
            except Exception:
                continue

        try:
            items.sort(key=lambda i: (i.get('Nom','') or '').lower())
        except Exception:
            pass

        try:
            win._preview_items = items
            if hasattr(win, 'PreviewCounterText') and win.PreviewCounterText is not None:
                ncoll = len(items)
                nelems = sum(len(it.get('Details', []) or []) for it in items)
                win.PreviewCounterText.Text = u"Collections: {} • Éléments: {}".format(ncoll, nelems)
            grid = getattr(win, 'CollectionGrid', None)
            if grid is not None:
                grid.ItemsSource = win._preview_items
        except Exception:
            pass

    # Force un refresh de la grille si possible
    def refresh_grid(self, win):
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

    def set_collection_status(self, win, collection_name, state):
        try:
            from System.Windows.Media import Brushes  # type: ignore
        except Exception:
            Brushes = None  # type: ignore
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

    def set_detail_status(self, win, collection_name, detail_name, detail_format, state):
        try:
            from System.Windows.Media import Brushes  # type: ignore
        except Exception:
            Brushes = None  # type: ignore
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
