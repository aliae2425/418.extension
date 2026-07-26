# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class RenameSheetOptions(object):
    """Options de renommage de feuilles. Contrat entre NamingPageVM et
    RenameSheetsService. Tous les champs ont une valeur par défaut."""

    def __init__(self,
                 number_find=u'', number_replace=u'', number_prefix=u'', number_suffix=u'',
                 name_find=u'', name_replace=u'', name_prefix=u'', name_suffix=u''):
        self.number_find = number_find
        self.number_replace = number_replace
        self.number_prefix = number_prefix
        self.number_suffix = number_suffix
        self.name_find = name_find
        self.name_replace = name_replace
        self.name_prefix = name_prefix
        self.name_suffix = name_suffix
