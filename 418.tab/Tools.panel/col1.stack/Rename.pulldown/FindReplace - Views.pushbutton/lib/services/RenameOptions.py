# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class RenameViewOptions(object):
    """Options de renommage de vues. Contrat entre NamingPageVM et
    RenameViewsService."""

    def __init__(self,
                 view_find=u'', view_replace=u'', view_prefix=u'', view_suffix=u''):
        self.view_find = view_find
        self.view_replace = view_replace
        self.view_prefix = view_prefix
        self.view_suffix = view_suffix
