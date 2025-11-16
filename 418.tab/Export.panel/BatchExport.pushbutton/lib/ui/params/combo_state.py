# -*- coding: utf-8 -*-

# Paramètres: ComboBox et validations

from ..state import CONFIG, Visibility, Brushes
from ...sheets import collect_sheet_parameter_names  # type: ignore

# TODO: limiter la logique d'UI ici et extraire les validations pures si nécessaire


def _fill_combos_with_placeholder(win, text):
    for cname in ["ExportationCombo", "CarnetCombo", "DWGCombo"]:
        ctrl = getattr(win, cname, None)
        if ctrl is None:
            continue
        try:
            try:
                ctrl.Items.Clear()
            except Exception:
                pass
            ctrl.Items.Add(text)
            ctrl.SelectedIndex = 0
        except Exception:
            pass
    try:
        win._available_param_names = []
    except Exception:
        pass


def _populate_sheet_param_combos(win):
    # Remplit ExportationCombo, CarnetCombo, DWGCombo avec les noms de paramètres
    try:
        if getattr(win, 'REVIT_API_AVAILABLE', None) is False:
            _fill_combos_with_placeholder(win, "(API Revit indisponible)")
            return
    except Exception:
        pass
    try:
        doc = __revit__.ActiveUIDocument.Document  # type: ignore
    except Exception:
        _fill_combos_with_placeholder(win, "(Document introuvable)")
        return

    param_names = collect_sheet_parameter_names(doc, CONFIG)
    if not param_names:
        _fill_combos_with_placeholder(win, "(Aucun paramètre booléen de feuille)")
        return

    target_combo_names = ["ExportationCombo", "CarnetCombo", "DWGCombo"]
    for cname in target_combo_names:
        ctrl = getattr(win, cname, None)
        if ctrl is None:
            continue
        try:
            try:
                ctrl.Items.Clear()
            except Exception:
                pass
            for n in param_names:
                try:
                    ctrl.Items.Add(n)
                except Exception:
                    continue
            if ctrl.Items.Count > 0:
                try:
                    ctrl.SelectedIndex = 0
                except Exception:
                    pass
        except Exception:
            print('[info] Impossible de remplir {}.'.format(cname))
    try:
        win._available_param_names = param_names
    except Exception:
        pass


def _get_selected_values(win):
    out = {}
    for cname in ["ExportationCombo", "CarnetCombo", "DWGCombo"]:
        ctrl = getattr(win, cname, None)
        if ctrl is None:
            continue
        try:
            val = getattr(ctrl, 'SelectedItem', None)
            out[cname] = None if val is None else str(val)
        except Exception:
            out[cname] = None
    return out


def _are_three_unique(win):
    selected = _get_selected_values(win)
    vals = [v for v in selected.values() if v]
    if len(vals) != 3:
        return False, selected
    if len(set(vals)) != 3:
        return False, selected
    return True, selected


def _check_and_warn_insufficient(win):
    # Affiche/masque un avertissement si < 3 paramètres uniques disponibles
    try:
        warn = getattr(win, 'ParamWarningText', None)
        unique_err = getattr(win, 'UniqueErrorText', None)
        expander = getattr(win, 'CollectionExpander', None)
        if warn is None:
            return
        avail = getattr(win, '_available_param_names', None)
        count = len(avail) if isinstance(avail, list) else 0
        if count < 3:
            warn.Visibility = Visibility.Visible
            warn.Text = u"Paramètres insuffisants pour assurer des sélections uniques ({} trouvés).".format(count)
        else:
            warn.Visibility = Visibility.Collapsed
        if unique_err is not None:
            try:
                are_unique, _ = _are_three_unique(win)
                if count >= 3 and not are_unique:
                    unique_err.Visibility = Visibility.Visible
                else:
                    unique_err.Visibility = Visibility.Collapsed
            except Exception:
                pass
        if expander is not None:
            if count == 0:
                expander.Visibility = Visibility.Collapsed
            else:
                expander.Visibility = Visibility.Visible
    except Exception:
        pass


def _update_export_button_state(win):
    # Active le bouton Export si la destination est valide et qu'au moins un paramètre est disponible
    try:
        btn = getattr(win, 'ExportButton', None)
        status = getattr(win, 'ExportStatusText', None)
        unique_err = getattr(win, 'UniqueErrorText', None)
        if btn is None:
            return
        avail = getattr(win, '_available_param_names', None)
        count = len(avail) if isinstance(avail, list) else 0
        dest_ok = bool(getattr(win, '_dest_valid', False))

        messages = []
        if not dest_ok:
            messages.append(u"Sélectionnez un dossier de destination valide.")
        if count < 1:
            messages.append(u"Aucun paramètre de feuille disponible.")

        enabled = (len(messages) == 0)
        btn.IsEnabled = enabled

        if status is not None:
            try:
                if enabled:
                    status.Text = u"Prêt à exporter."
                    if Brushes is not None and hasattr(Brushes, 'Green'):
                        status.Foreground = Brushes.Green
                else:
                    status.Text = u" • ".join(messages)
                    if Brushes is not None and hasattr(Brushes, 'Red'):
                        status.Foreground = Brushes.Red
            except Exception:
                pass
        if unique_err is not None:
            try:
                unique_err.Visibility = Visibility.Collapsed
            except Exception:
                pass
    except Exception:
        pass


def _apply_saved_selection(win):
    # Charge les sélections mémorisées pour chaque combo si l'item existe
    try:
        from ..state import _PARAM_COMBOS, CONFIG
    except Exception:
        _PARAM_COMBOS = ["ExportationCombo", "CarnetCombo", "DWGCombo"]
        CONFIG = None

    def _config_key_for(cname):
        return 'sheet_param_{}'.format(cname)

    saved_map = {}
    for cname in _PARAM_COMBOS:
        try:
            saved_map[cname] = CONFIG.get(_config_key_for(cname)) if CONFIG else None
        except Exception:
            saved_map[cname] = None

    for cname in _PARAM_COMBOS:
        ctrl = getattr(win, cname, None)
        if ctrl is None:
            continue
        saved = saved_map.get(cname)
        if not saved:
            continue
        try:
            idx = -1
            try:
                for i in range(ctrl.Items.Count):
                    try:
                        if str(ctrl.Items[i]) == str(saved):
                            idx = i
                            break
                    except Exception:
                        continue
            except Exception:
                pass
            if idx >= 0:
                try:
                    ctrl.SelectedIndex = idx
                except Exception:
                    pass
        except Exception:
            pass
