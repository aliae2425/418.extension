# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from config.AuditRules import charger as _charger


class BaseCheck(object):
    cle = u'?'
    libelle = u'?'

    def __init__(self, rules=None):
        # Règles injectées (tests) ou singleton chargé depuis audit_rules.json.
        if rules is not None:
            self._rules = rules
        else:
            self._rules = _charger()

    def run(self, doc):
        raise NotImplementedError
