# -*- coding: utf-8 -*-


class ExportSectionController(object):
    def __init__(self, win, options_component):
        self._win = win
        self._opts_comp = options_component

    def initialize(self):
        self._opts_comp.populate_pdf(self._win)
        self._opts_comp.populate_dwg(self._win)
        self._wire_setup_buttons()

    def wire_export_button(self, on_export):
        try:
            if hasattr(self._win, 'ExportButton'):
                self._win.ExportButton.Click += on_export
        except Exception:
            pass

    def _wire_setup_buttons(self):
        try:
            if hasattr(self._win, 'PDFCreateButton'):
                self._win.PDFCreateButton.Click += self._on_create_pdf
        except Exception:
            pass
        try:
            if hasattr(self._win, 'DWGCreateButton'):
                self._win.DWGCreateButton.Click += self._on_create_dwg
        except Exception:
            pass

    def _on_create_pdf(self, sender, args):
        try:
            from ..SetupEditorWindow import open_setup_editor
            if open_setup_editor(kind='pdf'):
                self._opts_comp.populate_pdf(self._win)
        except Exception:
            pass

    def _on_create_dwg(self, sender, args):
        try:
            from ..SetupEditorWindow import open_setup_editor
            if open_setup_editor(kind='dwg'):
                self._opts_comp.populate_dwg(self._win)
        except Exception:
            pass

    @staticmethod
    def run_export(win):
        try:
            doc = __revit__.ActiveUIDocument.Document  # type: ignore
        except Exception:
            doc = None
        if doc is None:
            return

        try:
            from ....services.core.ExportOrchestrator import ExportOrchestrator
            orch = ExportOrchestrator()

            def _progress(i, n, text):
                try:
                    if hasattr(win, 'ExportProgressBar'):
                        win.ExportProgressBar.Maximum = max(n, 1)
                        win.ExportProgressBar.Value = i
                except Exception:
                    pass

            def _log(msg):
                pass

            def _get_ctrl(name):
                return getattr(win, name, None)

            orch.run(doc, _get_ctrl, progress_cb=_progress, log_cb=_log, ui_win=win)
        except Exception as e:
            print('MainWindowController [003]: Export error: {}'.format(e))
