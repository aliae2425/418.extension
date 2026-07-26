# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class DuplicationOptions(object):
    """Options de duplication de feuilles. Contrat entre OptionsPageVM et
    DuplicationSheetsService. Tous les champs ont une valeur par défaut."""

    def __init__(self,
                 view_find=u'', view_replace=u'', view_prefix=u'', view_suffix=u'',
                 number_find=u'', number_replace=u'', number_prefix=u'', number_suffix=u'',
                 name_find=u'', name_replace=u'', name_prefix=u'', name_suffix=u'',
                 include_views=True, include_legends=True, include_schedules=True,
                 include_images=True, include_lines=True, include_text=True,
                 include_clouds=False, include_dwgs=False, include_symbols=False,
                 include_dimensions=False, include_additional_revisions=False,
                 use_existing_legends=True, use_existing_schedules=True,
                 view_duplicate_option=u'duplicate'):
        self.view_find = view_find
        self.view_replace = view_replace
        self.view_prefix = view_prefix
        self.view_suffix = view_suffix
        self.number_find = number_find
        self.number_replace = number_replace
        self.number_prefix = number_prefix
        self.number_suffix = number_suffix
        self.name_find = name_find
        self.name_replace = name_replace
        self.name_prefix = name_prefix
        self.name_suffix = name_suffix
        self.include_views = include_views
        self.include_legends = include_legends
        self.include_schedules = include_schedules
        self.include_images = include_images
        self.include_lines = include_lines
        self.include_text = include_text
        self.include_clouds = include_clouds
        self.include_dwgs = include_dwgs
        self.include_symbols = include_symbols
        self.include_dimensions = include_dimensions
        self.include_additional_revisions = include_additional_revisions
        self.use_existing_legends = use_existing_legends
        self.use_existing_schedules = use_existing_schedules
        self.view_duplicate_option = view_duplicate_option
