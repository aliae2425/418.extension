# -*- coding: utf-8 -*-
# Service de progression: encapsule les callbacks vers la barre de progression et logs UI

class ProgressReporter(object):
    def __init__(self, progress_cb=None, log_cb=None):
        self._progress_cb = progress_cb
        self._log_cb = log_cb

    # Met à jour la progression
    def update(self, i, n, text=None):
        try:
            if callable(self._progress_cb):
                self._progress_cb(i, n, text)
        except Exception:
            pass

    # Ajoute un message de log
    def log(self, text):
        try:
            if callable(self._log_cb):
                self._log_cb(text)
        except Exception:
            pass
