# -*- coding: utf-8 -*-
# FACADE: délègue à services/core/ExportOrchestrator

from __future__ import unicode_literals

def _svc():
    try:
        from .services.core.ExportOrchestrator import ExportOrchestrator
        return ExportOrchestrator()
    except Exception:
        return None

def plan_exports_for_collections(doc, get_ctrl):
    svc = _svc()
    return svc.plan_exports_for_collections(doc, get_ctrl) if svc is not None else []

def execute_exports(doc, get_ctrl, progress_cb=None, log_cb=None, ui_win=None):
    svc = _svc()
    return bool(svc.run(doc, get_ctrl, progress_cb=progress_cb, log_cb=log_cb, ui_win=ui_win)) if svc is not None else False

__all__ = ['plan_exports_for_collections', 'execute_exports']
