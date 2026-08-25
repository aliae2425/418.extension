# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class SheetPreviewGroupVM(object):
    """Aperçu d'une feuille renommée : numéro + nom original → numéros/noms générés."""

    def __init__(self, numero_original, nom_original, numero_genere, nom_genere):
        self.NumeroOriginal = numero_original
        self.NomOriginal = nom_original
        self.NumeroGenere = numero_genere
        self.NomGenere = nom_genere
        self.OriginalLabel = u'{} — {}'.format(numero_original, nom_original)
        self.IsRenamed = (numero_genere != numero_original or nom_genere != nom_original)
