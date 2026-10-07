# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime as _datetime
import re as _re

try:
    _str = unicode
except NameError:
    _str = str

_RESTES = _re.compile(r'\{[^{}]*\}')


def sans_jetons_restants(texte):
    """Retire les ``{jetons}`` qu'aucune valeur n'a résolus, et resserre.

    ``expand()`` les laisse tels quels — c'est voulu pour les gabarits de
    renommage, où voir le jeton aide à corriger sa faute de frappe. Mais un
    NOM DE FICHIER ou de dossier ne doit jamais porter de « {…} » brut : un
    jeton vide disparaît, et les séparateurs devenus orphelins avec lui.
    """
    if not texte:
        return texte
    sortie = _RESTES.sub(u'', texte)
    # « 2431 -  - PC » après disparition du nom : recoller les séparateurs
    # plutôt que laisser la trace de ce qui manquait.
    sortie = _re.sub(r'\s*[-_·]\s*([-_·]\s*)+', u' - ', sortie)
    sortie = _re.sub(r'\s{2,}', u' ', sortie)
    return sortie.strip(u' -_·')


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
