# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime as _datetime

try:
    _str = unicode
except NameError:
    _str = str

_AVAILABLE_TOKENS = (
    u'{date}',   u'{annee}', u'{mois}', u'{jour}',
    u'{n}',      u'{type}',
)


class TokenExpander(object):
    """Résout les tokens de génération de texte dans un template."""

    def __init__(self, today=None):
        self._today = today or _datetime.date.today()

    def expand(self, template, index=1, context=None):
        if not template:
            return template
        ctx = context or {}
        d = self._today
        result = template
        result = result.replace(u'{date}',  d.strftime('%Y-%m-%d'))
        result = result.replace(u'{annee}', d.strftime('%Y'))
        result = result.replace(u'{mois}',  d.strftime('%m'))
        result = result.replace(u'{jour}',  d.strftime('%d'))
        result = result.replace(u'{n}',     _str(index))
        for key, value in ctx.items():
            result = result.replace(u'{' + key + u'}', _str(value))
        return result

    @staticmethod
    def available_tokens():
        return list(_AVAILABLE_TOKENS)
