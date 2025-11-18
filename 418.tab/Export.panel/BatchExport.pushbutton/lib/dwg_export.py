# -*- coding: utf-8 -*-
# FACADE: délègue au service DwgExporterService.

from __future__ import unicode_literals

def _svc():
    try:
        from .services.formats.DwgExporterService import DwgExporterService
        return DwgExporterService()
    except Exception:
        return None

def list_dwg_setups(doc):
    svc = _svc()
    return svc.list_all_setups(doc) if svc is not None else []

def list_custom_dwg_setups():
    svc = _svc()
    return svc.list_custom_setups() if svc is not None else []

def list_all_dwg_setups(doc):
    svc = _svc()
    return svc.list_all_setups(doc) if svc is not None else []

def get_custom_dwg_setup_data(name):
    svc = _svc()
    return svc.get_custom_setup_data(name) if svc is not None else None

def get_saved_dwg_setup(default=None):
    svc = _svc()
    return svc.get_saved_setup(default) if svc is not None else default

def set_saved_dwg_setup(name):
    svc = _svc()
    return svc.set_saved_setup(name) if svc is not None else False

def get_saved_dwg_separate(default=False):
    svc = _svc()
    return svc.get_separate(default) if svc is not None else default

def set_saved_dwg_separate(flag):
    svc = _svc()
    return svc.set_separate(flag) if svc is not None else False

def build_dwg_export_options(doc, setup_name=None):
    svc = _svc()
    return svc.build_options(doc, setup_name) if svc is not None else None

__all__ = [
    'list_dwg_setups',
    'list_custom_dwg_setups',
    'list_all_dwg_setups',
    'get_custom_dwg_setup_data',
    'get_saved_dwg_setup',
    'set_saved_dwg_setup',
    'get_saved_dwg_separate',
    'set_saved_dwg_separate',
    'build_dwg_export_options',
]
