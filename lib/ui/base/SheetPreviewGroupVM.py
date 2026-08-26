# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Ligne d'aperçu « avant → après » d'une feuille, commune aux outils qui
# régénèrent numéro et nom : duplication (duplicate_sheets) et renommage
# (FindReplace_Sheets). Les deux exemplaires précédents ne différaient que
# par un mot de docstring.


class SheetPreviewGroupVM(object):
    """Aperçu d'une feuille : numéro + nom d'origine → numéro + nom générés."""

    def __init__(self, numero_original, nom_original, numero_genere, nom_genere):
        self.NumeroOriginal = numero_original
        self.NomOriginal = nom_original
        self.NumeroGenere = numero_genere
        self.NomGenere = nom_genere
        self.OriginalLabel = u'{} — {}'.format(numero_original, nom_original)
        self.IsRenamed = (numero_genere != numero_original
                          or nom_genere != nom_original)
