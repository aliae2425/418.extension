# -*- coding: utf-8 -*-
# Fenêtre modale SetupEditor migrée sous ui/windows et branchée sur core.UserConfig

from __future__ import unicode_literals

import os
import json
from pyrevit import forms


def _get_xaml_path():
    try:
        from ...core.AppPaths import AppPaths
        paths = AppPaths()
        return os.path.join(paths.gui_root(), 'Modals', 'SetupEditor.xaml')
    except Exception:
        here = os.path.dirname(__file__)
        return os.path.normpath(os.path.join(here, '..', '..', 'GUI', 'Modals', 'SetupEditor.xaml'))


def _config():
    from ...core.UserConfig import UserConfig
    return UserConfig('batch_export')


def _load_custom_list(kind):
    key = 'custom_{}_setups'.format(kind)
    cfg = _config()
    try:
        raw = cfg.get(key, '')
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
    cfg = _config()
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
        cfg.set(key, json.dumps(safe))
        return True
    except Exception:
        return False


class SetupEditorWindow(forms.WPFWindow):
    def __init__(self, kind=None):
        forms.WPFWindow.__init__(self, _get_xaml_path())
        try:
            from System import Uri, UriKind
            from System.Windows import ResourceDictionary
            from Autodesk.Revit.UI import UIThemeManager, UITheme
            from ...core.AppPaths import AppPaths
            paths = AppPaths()
            theme = UIThemeManager.CurrentTheme
            if theme == UITheme.Dark:
                files = ['ColorsDark.xaml', 'StylesDark.xaml']
            else:
                files = ['Colors.xaml', 'Styles.xaml']
            for filename in files:
                path = paths.resource_path(filename)
                if os.path.exists(path):
                    rd = ResourceDictionary()
                    rd.Source = Uri(path, UriKind.Absolute)
                    self.Resources.MergedDictionaries.Add(rd)
        except Exception as e:
            print('SetupEditorWindow [001]: Error loading resources: {}'.format(e))
        self._kind = (kind or 'pdf').lower()
        self._saved = False
        try:
            if hasattr(self, 'CancelButton'):
                self.CancelButton.Click += self._on_cancel
            if hasattr(self, 'SaveButton'):
                self.SaveButton.Click += self._on_save
            if hasattr(self, 'KindCombo'):
                self.KindCombo.SelectionChanged += self._on_kind_changed
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
        try:
            d['name'] = (self.SetupNameText.Text or '').strip()
        except Exception:
            d['name'] = ''
        try:
            d['page_size'] = str(getattr(self.PageSizeCombo, 'SelectedItem', ''))
        except Exception:
            d['page_size'] = ''
        d['zoom_mode'] = 'fit' if getattr(self, 'ZoomFitRadio', None) and getattr(self.ZoomFitRadio, 'IsChecked', False) else 'percent'
        try:
            d['zoom_percent'] = int(getattr(self, 'ZoomPercentText', None) and getattr(self.ZoomPercentText, 'Text', '100') or '100')
        except Exception:
            d['zoom_percent'] = 100
        if getattr(self, 'OrientationPortrait', None) and getattr(self.OrientationPortrait, 'IsChecked', False):
            d['orientation'] = 'portrait'
        elif getattr(self, 'OrientationLandscape', None) and getattr(self.OrientationLandscape, 'IsChecked', False):
            d['orientation'] = 'landscape'
        else:
            d['orientation'] = 'auto'
        if getattr(self, 'PlacementOffset', None) and getattr(self.PlacementOffset, 'IsChecked', False):
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
        try:
            d['raster_quality'] = str(getattr(self.RasterQualityCombo, 'SelectedItem', 'High'))
        except Exception:
            d['raster_quality'] = 'High'
        try:
            d['colors'] = str(getattr(self.ColorsCombo, 'SelectedItem', 'Color'))
        except Exception:
            d['colors'] = 'Color'
        d['processing'] = 'vector' if getattr(self, 'ProcessingVector', None) and getattr(self.ProcessingVector, 'IsChecked', False) else 'raster'
        flags = {
            'hide_ref_work_planes': getattr(self, 'OptHideRefWorkPlanes', None) and getattr(self.OptHideRefWorkPlanes, 'IsChecked', False),
            'hide_unref_tags': getattr(self, 'OptHideUnrefTags', None) and getattr(self.OptHideUnrefTags, 'IsChecked', False),
            'hide_crop_boundaries': getattr(self, 'OptHideCropBoundaries', None) and getattr(self.OptHideCropBoundaries, 'IsChecked', False),
            'hide_scope_boxes': getattr(self, 'OptHideScopeBoxes', None) and getattr(self.OptHideScopeBoxes, 'IsChecked', False),
            'export_in_background': getattr(self, 'OptExportInBackground', None) and getattr(self.OptExportInBackground, 'IsChecked', False),
            'separate_views_files': getattr(self, 'SeparateViewsCheck', None) and getattr(self.SeparateViewsCheck, 'IsChecked', False),
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
        print('SetupEditorWindow [002]: Error: {}'.format(e))
        return False


__all__ = ['open_setup_editor', 'SetupEditorWindow']
