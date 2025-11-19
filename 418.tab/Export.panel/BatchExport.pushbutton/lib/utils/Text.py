# -*- coding: utf-8 -*-
# Utilitaires texte simples

class Text(object):
    def safe(self, s, default=''):
        try:
            return s if s is not None else default
        except Exception:
            return default

    def lower(self, s):
        try:
            return (s or '').lower()
        except Exception:
            return ''
