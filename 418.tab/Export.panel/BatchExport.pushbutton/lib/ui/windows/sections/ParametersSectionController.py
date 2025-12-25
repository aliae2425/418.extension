# -*- coding: utf-8 -*-


class ParametersSectionController(object):
    def __init__(
        self,
        win,
        cfg,
        sheet_params_repo,
        param_component,
        on_export_state_update=None,
        on_preview_update=None,
    ):
        self._win = win
        self._cfg = cfg
        self._sheet_params = sheet_params_repo
        self._param_comp = param_component
        self._on_export_state_update = on_export_state_update
        self._on_preview_update = on_preview_update

    def initialize(self):
        self._load_param_combos()

    def wire_events(self):
        for cname in ("ExportationCombo", "CarnetCombo", "DWGCombo"):
            ctrl = getattr(self._win, cname, None)
            if ctrl is None:
                continue
            try:
                ctrl.SelectionChanged += self._on_param_changed
            except Exception:
                pass

    def apply_saved_selection(self):
        saved_map = {}
        for cname in ("ExportationCombo", "CarnetCombo", "DWGCombo"):
            try:
                saved_map[cname] = self._cfg.get('sheet_param_' + cname)
            except Exception:
                saved_map[cname] = None

        for cname in ("ExportationCombo", "CarnetCombo", "DWGCombo"):
            ctrl = getattr(self._win, cname, None)
            if ctrl is None:
                continue
            saved = saved_map.get(cname)
            if not saved:
                continue
            try:
                idx = -1
                for i in range(ctrl.Items.Count):
                    if str(ctrl.Items[i]) == str(saved):
                        idx = i
                        break
                if idx >= 0:
                    ctrl.SelectedIndex = idx
            except Exception:
                pass

    def check_warnings(self):
        try:
            from System.Windows import Visibility
        except Exception:
            class _V(object):
                Visible = 0
                Collapsed = 2

            Visibility = _V()

        warn = getattr(self._win, 'ParamWarningText', None)
        unique_err = getattr(self._win, 'UniqueErrorText', None)
        expander = getattr(self._win, 'CollectionExpander', None)

        avail = getattr(self._win, '_available_param_names', None)
        count = len(avail) if isinstance(avail, list) else 0

        if warn is not None:
            try:
                warn.Visibility = Visibility.Visible if count < 3 else Visibility.Collapsed
            except Exception:
                pass

        if unique_err is not None:
            try:
                if count >= 3 and not self._are_three_unique():
                    unique_err.Visibility = Visibility.Visible
                else:
                    unique_err.Visibility = Visibility.Collapsed
            except Exception:
                pass

        if expander is not None:
            try:
                expander.Visibility = Visibility.Collapsed if count == 0 else Visibility.Visible
            except Exception:
                pass

    def _load_param_combos(self):
        try:
            doc = __revit__.ActiveUIDocument.Document  # type: ignore
        except Exception:
            doc = None

        try:
            self._win._available_param_names = self._sheet_params.collect_for_collections(doc) if doc else []
        except Exception:
            self._win._available_param_names = []

        self._param_comp.populate(self._win)
        self.apply_saved_selection()
        self.check_warnings()

        if self._on_export_state_update is not None:
            try:
                self._on_export_state_update()
            except Exception:
                pass

    def _get_selected_values(self):
        out = {}
        for cname in ("ExportationCombo", "CarnetCombo", "DWGCombo"):
            ctrl = getattr(self._win, cname, None)
            if ctrl is None:
                continue
            try:
                val = getattr(ctrl, 'SelectedItem', None)
                out[cname] = None if val is None else str(val)
            except Exception:
                out[cname] = None
        return out

    def _are_three_unique(self):
        selected = self._get_selected_values()
        vals = [v for v in selected.values() if v]
        if len(vals) != 3:
            return False
        return len(set(vals)) == 3

    def _on_param_changed(self, sender, args):
        name = getattr(sender, 'Name', None) or ''
        val = getattr(sender, 'SelectedItem', None)
        if val:
            try:
                self._cfg.set('sheet_param_' + name, str(val))
            except Exception:
                pass

        self.check_warnings()

        if self._on_export_state_update is not None:
            try:
                self._on_export_state_update()
            except Exception:
                pass

        if self._on_preview_update is not None:
            try:
                self._on_preview_update()
            except Exception:
                pass
