# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class AuditIssue(object):
    def __init__(self, nom, gravite, element_id=None,
                 emplacement=u'', type_=u'', message=u''):
        self.nom = nom
        self.gravite = gravite
        self.element_id = element_id
        self.emplacement = emplacement
        self.type = type_
        self.message = message
