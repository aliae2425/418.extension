# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class BaseCheck(object):
    cle = u'?'
    libelle = u'?'

    def run(self, doc):
        raise NotImplementedError
