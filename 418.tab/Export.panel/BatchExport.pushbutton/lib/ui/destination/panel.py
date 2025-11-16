# -*- coding: utf-8 -*-

# Destination: gestion du chemin et des options

from ..state import CONFIG, Brushes

# TODO: ces helpers sont appelés depuis ExportMainWindow (garder la signature win/self)


def validate_destination(win, create=False):
    # Valide/Crée le dossier, donne un feedback visuel et persiste la valeur
    try:
        from ...destination import ensure_directory, set_saved_destination
    except Exception:
        return False
    path = ''
    try:
        path = win.PathTextBox.Text or ''
    except Exception:
        path = ''
    ok = False
    err = None
    if path:
        if create:
            ok, err = ensure_directory(path)
        else:
            try:
                import os as _os
                ok = _os.path.isdir(path)
            except Exception:
                ok = False
    try:
        if ok:
            if Brushes is not None:
                win.PathTextBox.BorderBrush = Brushes.Gray
                win.PathTextBox.Background = Brushes.White
            win.PathTextBox.ToolTip = path
            set_saved_destination(path)
        else:
            if Brushes is not None:
                win.PathTextBox.BorderBrush = Brushes.Red
                win.PathTextBox.Background = Brushes.MistyRose if hasattr(Brushes, 'MistyRose') else win.PathTextBox.Background
            win.PathTextBox.ToolTip = err or u"Chemin invalide"
    except Exception:
        pass
    win._dest_valid = bool(ok)
    return win._dest_valid


def init_destination_toggles(win):
    # Lecture/sauvegarde des options destination (1/0) depuis CONFIG
    try:
        getv = lambda k, d=False: (CONFIG.get(k, '') == '1') if CONFIG else d
        setv = lambda k, v: CONFIG.set(k, '1' if v else '0') if CONFIG else None
        if hasattr(win, 'CreateSubfoldersCheck'):
            win.CreateSubfoldersCheck.IsChecked = getv('create_subfolders', False)
            win.CreateSubfoldersCheck.Checked += lambda s,a: setv('create_subfolders', True)
            win.CreateSubfoldersCheck.Unchecked += lambda s,a: setv('create_subfolders', False)
        if hasattr(win, 'SeparateByFormatCheck'):
            win.SeparateByFormatCheck.IsChecked = getv('separate_format_folders', False)
            win.SeparateByFormatCheck.Checked += lambda s,a: setv('separate_format_folders', True)
            win.SeparateByFormatCheck.Unchecked += lambda s,a: setv('separate_format_folders', False)
    except Exception:
        pass
