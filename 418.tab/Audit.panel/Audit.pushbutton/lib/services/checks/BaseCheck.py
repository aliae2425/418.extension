# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from config.AuditRules import charger as _charger
except Exception:
    try:
        from lib.config.AuditRules import charger as _charger
    except Exception:
        _charger = None


class BaseCheck(object):
    cle = u'?'
    libelle = u'?'

    def __init__(self, rules=None):
        # Règles injectées (tests) ou singleton chargé depuis audit_rules.json.
        if rules is not None:
            self._rules = rules
        elif _charger is not None:
            self._rules = _charger()
        else:
            self._rules = None

    def run(self, doc):
        raise NotImplementedError
