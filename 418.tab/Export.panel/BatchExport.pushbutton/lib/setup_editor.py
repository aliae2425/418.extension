# -*- coding: utf-8 -*-
"""Fenêtre modale pour créer et enregistrer des réglages d'export PDF / DWG.

Persistance:
    - custom_pdf_setups : JSON list[{name: str, data: dict}]
    - custom_dwg_setups : JSON list[{name: str, data: dict}]

Chaque `data` contient une structure agnostique (sans objets Revit) facile à recharger.
Conversion vers options Revit laissée en TODO future (build_*_export_options pourra accepter ce dict).
"""

import os
import json
from pyrevit import forms

from .config import UserConfigStore

CONFIG = UserConfigStore('batch_export')

GUI_FILE = os.path.join('GUI', 'SetupEditor.xaml')


def _get_xaml_path():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(base_dir, GUI_FILE)


def _load_custom_list(kind):
    key = 'custom_{}_setups'.format(kind)
    try:
        raw = CONFIG.get(key, '')
        if not raw:
            return []
        data = json.loads(raw)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _save_custom_list(kind, lst):
    key = 'custom_{}_setups'.format(kind)
    try:
        safe = []
        for item in lst:
            if not isinstance(item, dict):
                continue
            name = item.get('name')
            data = item.get('data')
            if not name or not isinstance(data, dict):
                continue
            safe.append({'name': name, 'data': data})
        CONFIG.set(key, json.dumps(safe))
        return True
    except Exception:
        return False


class SetupEditorWindow(forms.WPFWindow):
    def __init__(self, kind=None):
        forms.WPFWindow.__init__(self, _get_xaml_path())
        self._kind = (kind or 'pdf').lower()  # défaut
        self._saved = False
        # Brancher boutons
        try:
            if hasattr(self, 'CancelButton'):
                self.CancelButton.Click += self._on_cancel
            if hasattr(self, 'SaveButton'):
                self.SaveButton.Click += self._on_save
            if hasattr(self, 'KindCombo'):
                self.KindCombo.SelectionChanged += self._on_kind_changed
                # Appliquer sélection initiale
                for i in range(getattr(self.KindCombo, 'Items', None).Count):
                    try:
                        it = self.KindCombo.Items[i]
                        if str(getattr(it, 'Content', '')).lower() == self._kind:
                            self.KindCombo.SelectedIndex = i
                            break
                    except Exception:
                        continue
        except Exception:
            pass

    def _on_kind_changed(self, sender, args):
        try:
            sel = getattr(self.KindCombo, 'SelectedItem', None)
            if sel is not None:
                self._kind = getattr(sel, 'Content', 'PDF').lower()
        except Exception:
            self._kind = 'pdf'

    def _on_cancel(self, sender, args):
        try:
            self.Close()
        except Exception:
            pass

    def _collect_data(self):
        d = {}
        # Nom
        try:
            d['name'] = (self.SetupNameText.Text or '').strip()
        except Exception:
            d['name'] = ''
        # Page
        try:
            d['page_size'] = str(getattr(self.PageSizeCombo, 'SelectedItem', ''))
        except Exception:
            d['page_size'] = ''
        d['zoom_mode'] = 'fit' if getattr(self.ZoomFitRadio, 'IsChecked', False) else 'percent'
        try:
            d['zoom_percent'] = int(getattr(self.ZoomPercentText, 'Text', '100'))
        except Exception:
            d['zoom_percent'] = 100
        # Orientation
        if getattr(self.OrientationPortrait, 'IsChecked', False):
            d['orientation'] = 'portrait'
        elif getattr(self.OrientationLandscape, 'IsChecked', False):
            d['orientation'] = 'landscape'
        else:
            d['orientation'] = 'auto'
        # Placement
        if getattr(self.PlacementOffset, 'IsChecked', False):
            d['placement'] = 'offset'
            try:
                d['offset_x'] = float(getattr(self.OffsetXText, 'Text', '0') or 0)
                d['offset_y'] = float(getattr(self.OffsetYText, 'Text', '0') or 0)
            except Exception:
                d['offset_x'] = 0.0
                d['offset_y'] = 0.0
        else:
            d['placement'] = 'center'
            d['offset_x'] = 0.0
            d['offset_y'] = 0.0
        # Apparence
        try:
            d['raster_quality'] = str(getattr(self.RasterQualityCombo, 'SelectedItem', 'High'))
        except Exception:
            d['raster_quality'] = 'High'
        try:
            d['colors'] = str(getattr(self.ColorsCombo, 'SelectedItem', 'Color'))
        except Exception:
            d['colors'] = 'Color'
        d['processing'] = 'vector' if getattr(self.ProcessingVector, 'IsChecked', False) else 'raster'
        # Options booléennes
        flags = {
            'hide_ref_work_planes': getattr(self.OptHideRefWorkPlanes, 'IsChecked', False),
            'hide_unref_tags': getattr(self.OptHideUnrefTags, 'IsChecked', False),
            'hide_crop_boundaries': getattr(self.OptHideCropBoundaries, 'IsChecked', False),
            'hide_scope_boxes': getattr(self.OptHideScopeBoxes, 'IsChecked', False),
            'export_in_background': getattr(self.OptExportInBackground, 'IsChecked', False),
            'separate_views_files': getattr(self.SeparateViewsCheck, 'IsChecked', False),
        }
        d.update(flags)
        return d

    def _on_save(self, sender, args):
        data = self._collect_data()
        name = data.get('name')
        if not name:
            forms.alert('Nom du réglage requis.', title='Réglage export')
            return
        lst = _load_custom_list(self._kind)
        # Écraser si même nom
        replaced = False
        for i, item in enumerate(lst):
            if item.get('name') == name:
                lst[i] = {'name': name, 'data': data}
                replaced = True
                break
        if not replaced:
            lst.append({'name': name, 'data': data})
        _save_custom_list(self._kind, lst)
        self._saved = True
        try:
            self.Close()
        except Exception:
            pass


def open_setup_editor(kind=None):
    try:
        win = SetupEditorWindow(kind=kind)
        try:
            win.ShowDialog()
        except Exception:
            win.show()
        return win._saved
    except Exception as e:
        print('[info] Erreur setup_editor:', e)
        return False


__all__ = ['open_setup_editor', 'SetupEditorWindow']
