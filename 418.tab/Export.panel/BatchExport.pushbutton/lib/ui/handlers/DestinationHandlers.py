# -*- coding: utf-8 -*-
# Gestionnaires liés à la sélection de destination

class DestinationHandlers(object):
    def __init__(self, component):
        self._comp = component

    def on_browse(self, win):
        return self._comp.browse(win)

    def on_path_changed(self, win):
        ok, _ = self._comp.validate(win, create=False)
        return ok
