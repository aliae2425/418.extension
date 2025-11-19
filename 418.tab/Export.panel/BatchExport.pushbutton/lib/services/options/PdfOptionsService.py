# -*- coding: utf-8 -*-
# Service d'options PDF (facade minimaliste)

class PdfOptionsService(object):
    def __init__(self, pdf_service=None):
        if pdf_service is None:
            try:
                from ..formats.PdfExporterService import PdfExporterService
                pdf_service = PdfExporterService()
            except Exception:
                pdf_service = None
        self._pdf = pdf_service

    # Récupère la liste de réglages + sélectionne le courant
    def populate_combo(self, doc):
        if self._pdf is None:
            return []
        try:
            return self._pdf.list_all_setups(doc)
        except Exception:
            return []

    def get_saved(self, default=None):
        if self._pdf is None:
            return default
        return self._pdf.get_saved_setup(default)

    def set_saved(self, name):
        if self._pdf is None:
            return False
        return self._pdf.set_saved_setup(name)

    def get_separate(self, default=False):
        if self._pdf is None:
            return default
        return self._pdf.get_separate(default)

    def set_separate(self, flag):
        if self._pdf is None:
            return False
        return self._pdf.set_separate(flag)
