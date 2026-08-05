# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class AuditResult(object):
    def __init__(self, themes=None, score=100, top_critiques=None, meta=None):
        self.themes = list(themes) if themes else []
        self.score = score
        self.top_critiques = list(top_critiques) if top_critiques else []
        self.meta = dict(meta) if meta else {}
