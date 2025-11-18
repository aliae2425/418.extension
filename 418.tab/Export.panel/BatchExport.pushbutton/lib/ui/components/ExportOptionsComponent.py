# -*- coding: utf-8 -*-
# Composant UI: population des options PDF/DWG

class ExportOptionsComponent(object):
    def __init__(self, pdf_service, dwg_service):
        self._pdf = pdf_service
        self._dwg = dwg_service

    def populate_pdf(self, win):
        try:
            doc = __revit__.ActiveUIDocument.Document  # type: ignore
        except Exception:
            doc = None
        names = []
        try:
            names = self._pdf.list_all_setups(doc)
        except Exception:
            names = []
        combo = getattr(win, 'PDFSetupCombo', None)
        if combo is not None:
            try:
                combo.Items.Clear()
                for n in names:
                    combo.Items.Add(n)
                saved = self._pdf.get_saved_setup()
                if saved and saved in names:
                    combo.SelectedIndex = names.index(saved)
                elif names:
                    combo.SelectedIndex = 0
                combo.SelectionChanged += lambda s,a: self._pdf.set_saved_setup(str(getattr(combo,'SelectedItem','')))
            except Exception:
                pass
        chk = getattr(win, 'PDFSeparateCheck', None)
        if chk is not None:
            try:
                chk.IsChecked = self._pdf.get_separate(False)
                chk.Checked += lambda s,a: self._pdf.set_separate(True)
                chk.Unchecked += lambda s,a: self._pdf.set_separate(False)
            except Exception:
                pass

    def populate_dwg(self, win):
        try:
            doc = __revit__.ActiveUIDocument.Document  # type: ignore
        except Exception:
            doc = None
        names = []
        try:
            names = self._dwg.list_all_setups(doc)
        except Exception:
            names = []
        combo = getattr(win, 'DWGSetupCombo', None)
        if combo is not None:
            try:
                combo.Items.Clear()
                for n in names:
                    combo.Items.Add(n)
                saved = self._dwg.get_saved_setup()
                if saved and saved in names:
                    combo.SelectedIndex = names.index(saved)
                elif names:
                    combo.SelectedIndex = 0
                combo.SelectionChanged += lambda s,a: self._dwg.set_saved_setup(str(getattr(combo,'SelectedItem','')))
            except Exception:
                pass
        chk = getattr(win, 'DWGSeparateCheck', None)
        if chk is not None:
            try:
                chk.IsChecked = self._dwg.get_separate(False)
                chk.Checked += lambda s,a: self._dwg.set_separate(True)
                chk.Unchecked += lambda s,a: self._dwg.set_separate(False)
            except Exception:
                pass
