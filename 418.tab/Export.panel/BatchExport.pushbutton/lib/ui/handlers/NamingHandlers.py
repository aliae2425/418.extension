# -*- coding: utf-8 -*-
# Gestionnaires liés au nommage (ouverture modale)

class NamingHandlers(object):
    def __init__(self):
        pass

    def open_sheet_naming(self, win):
        try:
            from ... import piker
            piker.open_modal(kind='sheet', title=u"Nommage des feuilles")
        except Exception:
            pass

    def open_set_naming(self, win):
        try:
            from ... import piker
            piker.open_modal(kind='set', title=u"Nommage des carnets")
        except Exception:
            pass
