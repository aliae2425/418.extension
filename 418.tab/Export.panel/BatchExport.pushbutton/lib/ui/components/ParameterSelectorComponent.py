# -*- coding: utf-8 -*-
# Composant UI: chargement et gestion des combos de paramètres

try:
    from pyrevit import EXEC_PARAMS
    _verbose = EXEC_PARAMS.debug_mode
except Exception:
    _verbose = False

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
            if _verbose:
                print('[debug] Found {} boolean parameters for collections'.format(len(names)))
                if names:
                    print('[debug] Parameters:', ', '.join(names[:5]) + ('...' if len(names) > 5 else ''))
        except Exception as e:
            print('[error] Failed to collect parameters:', e)
            names = []
        for cname in ("ExportationCombo", "CarnetCombo", "DWGCombo"):
            ctrl = getattr(win, cname, None)
            if ctrl is None:
                if _verbose:
                    print('[warning] Control {} not found in window'.format(cname))
                continue
            try:
                ctrl.Items.Clear()
                for n in names:
                    ctrl.Items.Add(n)
                if ctrl.Items.Count > 0:
                    ctrl.SelectedIndex = 0
                if _verbose:
                    print('[debug] Populated {} with {} items'.format(cname, ctrl.Items.Count))
            except Exception as e:
                print('[error] Failed to populate {}: {}'.format(cname, e))
                pass
