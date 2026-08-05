# -*- coding: utf-8 -*-
from __future__ import unicode_literals

OK = 0
A_REVOIR = 1
CRITIQUE = 2

_LIBELLES = {OK: u'Conforme', A_REVOIR: u'À revoir', CRITIQUE: u'Critique'}


def libelle(niveau):
    return _LIBELLES.get(niveau, u'Inconnu')


def pire(niveaux):
    p = OK
    for n in niveaux:
        if n > p:
            p = n
    return p
