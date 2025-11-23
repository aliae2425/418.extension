# -*- coding: utf-8 -*-
# Composant UI: tableau de prévisualisation des collections

try:
    from System.ComponentModel import INotifyPropertyChanged, PropertyChangedEventArgs
    from System.Collections.ObjectModel import ObservableCollection
    
    class ObservableItem(INotifyPropertyChanged):
        """Classe observable pour le binding WPF avec dictionnaires"""
        def __init__(self, data_dict):
            self._data = data_dict
            self._property_changed_handlers = []
            
        def add_PropertyChanged(self, handler):
            self._property_changed_handlers.append(handler)
            
        def remove_PropertyChanged(self, handler):
            if handler in self._property_changed_handlers:
                self._property_changed_handlers.remove(handler)
        
        def __getitem__(self, key):
            return self._data.get(key)
            
        def __setitem__(self, key, value):
            if self._data.get(key) != value:
                self._data[key] = value
                self._notify_property_changed(key)
        
        def _notify_property_changed(self, property_name):
            for handler in self._property_changed_handlers:
                handler(self, PropertyChangedEventArgs(property_name))
                
        def get(self, key, default=None):
            return self._data.get(key, default)
except Exception:
    # Fallback si System n'est pas disponible
    class ObservableItem(object):
        def __init__(self, data_dict):
            self._data = data_dict
        def __getitem__(self, key):
            return self._data.get(key)
        def __setitem__(self, key, value):
            self._data[key] = value
        def get(self, key, default=None):
            return self._data.get(key, default)

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
            nres = NamingResolver(doc)
            dest = DestinationStore()
            _, sheet_rows = nstore.load('sheet')
            _, set_rows = nstore.load('set')
        except Exception:
            sheet_rows = []
            set_rows = []
            nres = None
            dest = None

        def _name_for_sheet(viewsheet):
            """Retourne le nom projeté d'une feuille selon les règles de nommage"""
            try:
                base = nres.resolve_for_element(viewsheet, sheet_rows, empty_fallback=False) if nres is not None else ''
                base = dest.sanitize(base) if (dest is not None and base) else base
                if not base:
                    base = getattr(viewsheet, 'Name', 'Sheet')
                return base
            except Exception:
                return getattr(viewsheet, 'Name', 'Sheet')
        
        def _name_for_collection(collection):
            """Retourne le nom projeté d'une collection (carnet) selon les règles de nommage"""
            try:
                base = nres.resolve_for_element(collection, set_rows, empty_fallback=False) if nres is not None else ''
                base = dest.sanitize(base) if (dest is not None and base) else base
                if not base:
                    base = getattr(collection, 'Name', 'Collection')
                return base
            except Exception:
                return getattr(collection, 'Name', 'Collection')
        
        def _sheet_info(viewsheet):
            """Retourne l'info de la feuille (numéro + nom)"""
            try:
                num = getattr(viewsheet, 'SheetNumber', '')
                name = getattr(viewsheet, 'Name', '')
                if num and name:
                    return u"{} - {}".format(num, name)
                return name or num or 'Sheet'
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
                # Inverser la logique : si le param Carnet est True = compiler (per_sheet=False), si False = par feuille (per_sheet=True)
                carnet_flag = _read_flag(coll, pname_carnet, False)
                per_sheet = not carnet_flag  # Inversion
                do_dwg = _read_flag(coll, pname_dwg, False)
                do_pdf = bool(do_export)
                sheets = _sheets_in(doc, coll)

                details = []
                if do_pdf:
                    if per_sheet:
                        # Export PDF par feuille
                        for sh in sheets:
                            try:
                                preview = _name_for_sheet(sh)
                                sheet_info = _sheet_info(sh)
                                details.append({
                                    'SheetInfo': sheet_info,
                                    'PreviewNom': preview,
                                    'Format': 'PDF', 
                                    'StatutText': u'', 
                                    'StatutColor': getattr(Brushes, 'Green', None) if Brushes is not None else None
                                })
                            except Exception:
                                continue
                    else:
                        # Export PDF combiné (carnet)
                        preview = _name_for_collection(coll)
                        details.append({
                            'SheetInfo': u'{} feuilles'.format(len(sheets)),
                            'PreviewNom': preview,
                            'Format': 'PDF (combiné)', 
                            'StatutText': u'', 
                            'StatutColor': getattr(Brushes, 'Green', None) if Brushes is not None else None
                        })
                if do_dwg:
                    # Export DWG toujours par feuille
                    for sh in sheets:
                        try:
                            preview = _name_for_sheet(sh)
                            sheet_info = _sheet_info(sh)
                            details.append({
                                'SheetInfo': sheet_info,
                                'PreviewNom': preview,
                                'Format': 'DWG', 
                                'StatutText': u'', 
                                'StatutColor': getattr(Brushes, 'Green', None) if Brushes is not None else None
                            })
                        except Exception:
                            continue

                try:
                    details.sort(key=lambda d: (d.get('SheetInfo','') or '').lower())
                except Exception:
                    pass

                # Preview nom pour la collection
                collection_preview = _name_for_collection(coll)

                items.append(ObservableItem({
                    'Nom': coll.Name,
                    'PreviewNom': collection_preview,
                    'Feuilles': len(sheets),
                    'ExportText': u"\u2713" if do_pdf else u"\u2717",
                    'ExportColor': getattr(Brushes, 'Green', None) if (Brushes is not None and do_pdf) else (getattr(Brushes, 'Gray', None) if Brushes is not None else None),
                    'CarnetText': u"\u2713" if carnet_flag else u"\u2717",
                    'CarnetColor': getattr(Brushes, 'Green', None) if (Brushes is not None and carnet_flag) else (getattr(Brushes, 'Gray', None) if Brushes is not None else None),
                    'DWGText': u"\u2713" if do_dwg else u"\u2717",
                    'DWGColor': getattr(Brushes, 'Green', None) if (Brushes is not None and do_dwg) else (getattr(Brushes, 'Gray', None) if Brushes is not None else None),
                    'StatutText': u"",
                    'StatutColor': None,
                    'Details': details,
                    'IsExpanded': True,
                }))
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
            row_bg = getattr(Brushes, 'Transparent', None)
            txt = u""
            
            if state == 'progress':
                txt = u"En cours…"
                # row_bg reste transparent ou gris clair
            elif state == 'ok':
                txt = u""
                row_bg = getattr(Brushes, 'LightGreen', None)
            elif state == 'error':
                txt = u"Erreur"
                row_bg = getattr(Brushes, 'LightYellow', None)
            
            for it in items:
                try:
                    if it.get('Nom') != collection_name:
                        continue
                    for d in it.get('Details', []) or []:
                        try:
                            if (d.get('PreviewNom') == detail_name) and (d.get('Format') == detail_format):
                                d['StatutText'] = txt
                                d['RowBackground'] = row_bg
                                return
                        except Exception:
                            continue
                except Exception:
                    continue
        except Exception:
            pass
