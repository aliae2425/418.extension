# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime as _datetime

try:
    _str = unicode
except NameError:
    _str = str


class TokenExpander(object):
    """Résout les tokens de génération de texte dans un template.

    Tokens intégrés
    ───────────────
        {date}   date du jour  AAAA-MM-JJ
        {annee}  année 4 chiffres
        {mois}   mois 2 chiffres
        {jour}   jour 2 chiffres
        {n}      numéro de la copie courante (1-based)
        {type}   type de vue (injecté via context)

    Tokens personnalisés
    ────────────────────
        Passer un dict ``context={'cle': 'valeur'}`` pour résoudre ``{cle}``.

    Usage
    ─────
        expander = TokenExpander()
        expander.expand(u'{annee}_{n}', index=2)   # '2026_2'
    """

    def __init__(self, today=None):
        self._today = today or _datetime.date.today()

    def expand(self, template, index=1, context=None):
        """Retourne ``template`` avec tous les tokens résolus.

        Les tokens inconnus sont laissés tels quels.
        """
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
