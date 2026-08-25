# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class ViewsDuplicationOptions(object):
    """Options de duplication de vues : mode de duplication + nombre de copies."""

    def __init__(self, view_duplicate_option=u'duplicate', count=1,
                 prefixe=u'', rechercher=u'', remplacer=u'', suffixe=u'',
                 use_regex=False):
        self.view_duplicate_option = view_duplicate_option
        try:
            c = int(count)
        except (ValueError, TypeError):
            c = 1
        self.count = c if c >= 1 else 1
        self.prefixe = prefixe
        self.rechercher = rechercher
        self.remplacer = remplacer
        self.suffixe = suffixe
        self.use_regex = use_regex
