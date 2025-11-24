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
        try:
            from System.Windows.Data import ListCollectionView, PropertyGroupDescription  # type: ignore
        except Exception:
            ListCollectionView = None
            PropertyGroupDescription = None

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

        def _get_sheet_size_orientation(sheet):
            try:
                # Try to find titleblock
                tblock = DB.FilteredElementCollector(doc, sheet.Id)\
                           .OfCategory(DB.BuiltInCategory.OST_TitleBlocks)\
                           .FirstElement()
                if tblock:
                    size = tblock.Name
                    # Try to guess orientation from width/height params if available
                    # or just assume based on size name if it contains "Landscape" or "Portrait"
                    # But usually size name is just "A1".
                    # Let's try to get Width/Height from sheet parameters
                    w_param = sheet.get_Parameter(DB.BuiltInParameter.SHEET_WIDTH)
                    h_param = sheet.get_Parameter(DB.BuiltInParameter.SHEET_HEIGHT)
                    
                    width = w_param.AsDouble() if w_param else 0
                    height = h_param.AsDouble() if h_param else 0
                    
                    orientation = "Landscape" if width > height else "Portrait"
                    if width == 0 and height == 0:
                         orientation = ""
                    
                    return size, orientation
            except Exception:
                pass
            return "", ""

        pname_export = selected_names.get('ExportationCombo')
        pname_carnet = selected_names.get('CarnetCombo')
        pname_dwg = selected_names.get('DWGCombo')

        items = []
        cols = _collections(doc)
        cols_sorted = sorted(cols, key=lambda c: (getattr(c, 'Name', '') or '').lower())
        
        for coll in cols_sorted:
            try:
                do_export = _read_flag(coll, pname_export, False)
                carnet_flag = _read_flag(coll, pname_carnet, False)
                per_sheet = not carnet_flag
                do_dwg = _read_flag(coll, pname_dwg, False)
                do_pdf = bool(do_export)
                
                if not do_pdf and not do_dwg:
                    continue

                sheets = _sheets_in(doc, coll)
                # Sort sheets by number
                try:
                    sheets.sort(key=lambda s: (getattr(s, 'SheetNumber', '') or ''))
                except Exception:
                    pass

                # Construct group info
                export_info = []
                if do_pdf:
                    if per_sheet:
                        export_info.append("PDF (Feuilles)")
                    else:
                        export_info.append("PDF (Combiné)")
                if do_dwg:
                    export_info.append("DWG")
                
                group_header = "{} [{}]".format(coll.Name, ", ".join(export_info))

                for sh in sheets:
                    size, orientation = _get_sheet_size_orientation(sh)
                    sheet_num = getattr(sh, 'SheetNumber', '')
                    sheet_name = getattr(sh, 'Name', '')
                    
                    # Helper to add item
                    def add_item(fmt, is_combined=False):
                        # Calculate preview name
                        preview_name = ""
                        try:
                            if is_combined:
                                preview_name = _name_for_collection(coll)
                            else:
                                preview_name = _name_for_sheet(sh)
                        except Exception:
                            preview_name = sheet_name

                        items.append(ObservableItem({
                            'IsChecked': True,
                            'SheetNumber': sheet_num,
                            'SheetName': sheet_name,
                            'PreviewNom': preview_name,
                            'Format': fmt,
                            'Size': size,
                            'Orientation': orientation,
                            'Progress': '',
                            'ProgressColor': getattr(Brushes, 'Black', None),
                            # Internal data
                            'CollectionName': coll.Name,
                            'GroupHeader': group_header,
                            'SheetIdStr': sheet_num + '_' + sheet_name, # Matches _safe_sheet_name
                            'IsCombined': is_combined
                        }))

                    if do_pdf:
                        add_item('PDF', is_combined=not per_sheet)
                    
                    if do_dwg:
                        add_item('DWG', is_combined=False)

            except Exception:
                continue

        try:
            win._preview_items = items
            if hasattr(win, 'PreviewCounterText') and win.PreviewCounterText is not None:
                ncoll = len(cols) # Total collections found
                nelems = len(items)
                win.PreviewCounterText.Text = u"Collections: {} • Éléments: {}".format(ncoll, nelems)
            grid = getattr(win, 'CollectionGrid', None)
            if grid is not None:
                if ListCollectionView is not None and PropertyGroupDescription is not None:
                    view = ListCollectionView(items)
                    # Use indexer syntax for dictionary access if needed, or just property name if ObservableItem supports it.
                    # Since ObservableItem is a wrapper around dict, we might need to ensure it works.
                    # PropertyGroupDescription("GroupHeader") expects a property named GroupHeader.
                    # ObservableItem does not have a property named GroupHeader.
                    # However, we can try to use the indexer syntax "[GroupHeader]" which WPF supports for indexers.
                    view.GroupDescriptions.Add(PropertyGroupDescription("[GroupHeader]"))
                    grid.ItemsSource = view
                else:
                    grid.ItemsSource = items
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
        # In flat list, we might not show collection status directly, 
        # or we could update all items of that collection?
        # For now, ignore collection-level status updates as they are redundant with detail updates usually.
        pass

    def set_detail_status(self, win, collection_name, detail_name, detail_format, state):
        try:
            from System.Windows.Media import Brushes  # type: ignore
        except Exception:
            Brushes = None  # type: ignore
        try:
            items = getattr(win, '_preview_items', []) or []
            color = getattr(Brushes, 'Black', None)
            txt = u""
            
            if state == 'progress':
                txt = u"En cours…"
                color = getattr(Brushes, 'Orange', None)
            elif state == 'ok':
                txt = u"Terminé"
                color = getattr(Brushes, 'Green', None)
            elif state == 'error':
                txt = u"Erreur"
                color = getattr(Brushes, 'Red', None)
            
            # Handle "PDF (combiné)"
            is_combined_update = (detail_format == 'PDF (combiné)')
            
            for it in items:
                try:
                    if it.get('CollectionName') != collection_name:
                        continue
                    
                    # Check format
                    # If update is combined PDF, we update all PDF items for this collection
                    if is_combined_update:
                        if it.get('Format') == 'PDF':
                            it['Progress'] = txt
                            it['ProgressColor'] = color
                    else:
                        # Per sheet update
                        # Check format match (PDF vs DWG)
                        # detail_format is 'PDF' or 'DWG'
                        if it.get('Format') != detail_format:
                            continue
                            
                        # Check sheet match
                        # detail_name passed from orchestrator is _safe_sheet_name (SheetNumber_SheetName)
                        if it.get('SheetIdStr') == detail_name:
                            it['Progress'] = txt
                            it['ProgressColor'] = color
                            
                except Exception:
                    continue
        except Exception:
            pass
