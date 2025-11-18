# -*- coding: utf-8 -*-
# Gestionnaires d'événements liés à l'export

class ExportHandlers(object):
    def __init__(self, orchestrator):
        self._orch = orchestrator

    # Clic sur le bouton Export
    def on_export_click(self, win):
        try:
            doc = __revit__.ActiveUIDocument.Document  # type: ignore
        except Exception:
            doc = None
        if doc is None:
            return False
        def _get_ctrl(name):
            return getattr(win, name, None)
        def _progress(i, n, text):
            try:
                if hasattr(win, 'ExportProgressBar'):
                    win.ExportProgressBar.Maximum = max(n, 1)
                    win.ExportProgressBar.Value = i
            except Exception:
                pass
        def _log(msg):
            print('[info]', msg)
        return self._orch.run(doc, _get_ctrl, progress_cb=_progress, log_cb=_log, ui_win=win)
