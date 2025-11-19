# -*- coding: utf-8 -*-
# Composant UI: chargement et gestion des combos de paramètres

class ParameterSelectorComponent(object):
    def __init__(self, sheet_params_repo):
        self._repo = sheet_params_repo

    # Remplit ExportationCombo, CarnetCombo, DWGCombo
    def populate(self, win):
        try:
            doc = __revit__.ActiveUIDocument.Document  # type: ignore
        except Exception:
            doc = None
        names = []
        try:
            names = self._repo.collect_for_collections(doc)
        except Exception:
            names = []
        for cname in ("ExportationCombo", "CarnetCombo", "DWGCombo"):
            ctrl = getattr(win, cname, None)
            if ctrl is None:
                continue
            try:
                ctrl.Items.Clear()
                for n in names:
                    ctrl.Items.Add(n)
                if ctrl.Items.Count > 0:
                    ctrl.SelectedIndex = 0
            except Exception:
                pass
