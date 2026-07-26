# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class PreviewCopyVM(object):
    """Une copie générée : son index dans la série et son nom calculé."""

    def __init__(self, index, nom):
        self.IndexLabel = u'{}.'.format(index)
        self.Nom = nom


class PreviewGroupVM(object):
    """Un groupe de l'aperçu : vue d'origine + liste des copies générées."""

    def __init__(self, nom_original, copies):
        """
        Args:
            nom_original : str — nom de la vue source
            copies       : list[PreviewCopyVM]
        """
        self.NomOriginal = nom_original
        self.Copies = copies
        self.CountLabel = u'× {}'.format(len(copies))
        self.NomGenere = copies[0].Nom if copies else nom_original
        self.IsRenamed = any(c.Nom != nom_original for c in copies)
