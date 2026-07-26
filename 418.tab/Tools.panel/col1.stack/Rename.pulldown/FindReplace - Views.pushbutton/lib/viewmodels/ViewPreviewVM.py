# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class ViewPreviewVM(object):
    """Aperçu d'une vue renommée : nom original → nom généré."""

    def __init__(self, nom_original, type_label, nom_genere):
        self.NomOriginal = nom_original
        self.TypeLabel = type_label
        self.NomGenere = nom_genere
        self.OriginalLabel = u'{} [{}]'.format(nom_original, type_label) if type_label else nom_original
        self.IsRenamed = (nom_genere != nom_original)
