# -*- coding: utf-8 -*-

import os
import re
import tempfile


try:
    from pyrevit.framework import System
except Exception:
    System = None


class AppPaths(object):
    def __init__(self, base_dir=None):
        # base_dir = dossier lib/core/
        self._base = base_dir or os.path.dirname(__file__)

    def gui_root(self):
        return os.path.normpath(os.path.join(self._base, '..', '..', 'GUI'))

    def windows_xaml(self):
        return os.path.join(self.gui_root(), 'windows.xaml')

    def controls_dir(self):
        return os.path.join(self.gui_root(), 'Controls')

    def main_xaml(self):
        return os.path.normpath(os.path.join(self.gui_root(), 'Views', 'index.xaml'))

    def edit_record_xaml(self):
        return os.path.normpath(os.path.join(self.gui_root(), 'Modals', 'EditRecord.xaml'))

    def resource_path(self, filename):
        return os.path.join(self.gui_root(), 'resources', filename)

    def _to_file_uri(self, path):
        if System is not None:
            try:
                return System.Uri(path).AbsoluteUri
            except Exception:
                pass
        # Fallback: best-effort file URI (Windows)
        norm = os.path.normpath(path).replace('\\', '/')
        if not norm.startswith('/'):
            norm = '/' + norm
        return 'file://{}'.format(norm)

    def materialize_xaml_with_absolute_sources(self, xaml_path):
        """Return a temp XAML path where relative ResourceDictionary Source URIs are absolute.

        pyRevit's XAML loader does not reliably set a BaseUri for resolving relative
        ResourceDictionary.Source values. This makes MergedDictionaries with relative
        Source paths fail at load time. We keep resources external but rewrite the
        Source values into absolute file:/// URIs in a generated copy.
        """
        xaml_path = os.path.normpath(xaml_path)
        xaml_dir = os.path.dirname(xaml_path)

        with open(xaml_path, 'r') as fp:
            xaml_text = fp.read()

        def _replace_source(match):
            raw = match.group(1)
            if '://' in raw:
                return match.group(0)
            # only rewrite relative paths (., ..) that look like file refs
            if not (raw.startswith('.') or raw.startswith('..')):
                return match.group(0)
            if not raw.lower().endswith('.xaml'):
                return match.group(0)

            abs_path = os.path.normpath(os.path.join(xaml_dir, raw))
            return 'Source="{}"'.format(self._to_file_uri(abs_path))

        patched = re.sub(r'Source\s*=\s*"([^"]+)"', _replace_source, xaml_text)

        tmp_dir = os.path.join(tempfile.gettempdir(), 'pyrevit_keynotes')
        if not os.path.isdir(tmp_dir):
            os.makedirs(tmp_dir)

        base = os.path.basename(xaml_path)
        out_path = os.path.join(tmp_dir, base.replace('.xaml', '.abs.xaml'))

        with open(out_path, 'w') as fp:
            fp.write(patched)

        return out_path
