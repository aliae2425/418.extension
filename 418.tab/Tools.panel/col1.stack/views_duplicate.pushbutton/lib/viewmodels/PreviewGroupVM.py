# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class PreviewGroupVM(object):
    """Une ligne de l'aperçu : vue d'origine → nom(s) généré(s)."""

    def __init__(self, nom_original, nom_genere, count):
        self.NomOriginal = nom_original
        self.NomGenere = nom_genere
        self.CountLabel = u'× {}'.format(count)
        self.IsRenamed = nom_genere != nom_original
