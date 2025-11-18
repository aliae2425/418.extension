# -*- coding: utf-8 -*-
# FACADE: délègue au service PdfExporterService.

from __future__ import unicode_literals

def _svc():
    try:
        from .services.formats.PdfExporterService import PdfExporterService
        return PdfExporterService()
    except Exception:
        return None

def list_pdf_setups(doc):
    svc = _svc()
    # Pour compat: n'expose que les setups Revit (historiquement) -> utiliser list_all_pdf_setups sinon
    return svc.list_all_setups(doc) if svc is not None else []

def list_custom_pdf_setups():
    svc = _svc()
    return svc.list_custom_setups() if svc is not None else []

def list_all_pdf_setups(doc):
    svc = _svc()
    return svc.list_all_setups(doc) if svc is not None else []

def get_custom_pdf_setup_data(name):
    svc = _svc()
    return svc.get_custom_setup_data(name) if svc is not None else None

def get_saved_pdf_setup(default=None):
    svc = _svc()
    return svc.get_saved_setup(default) if svc is not None else default

def set_saved_pdf_setup(name):
    svc = _svc()
    return svc.set_saved_setup(name) if svc is not None else False

def get_saved_pdf_separate(default=False):
    svc = _svc()
    return svc.get_separate(default) if svc is not None else default

def set_saved_pdf_separate(flag):
    svc = _svc()
    return svc.set_separate(flag) if svc is not None else False

def build_pdf_export_options(doc, setup_name=None):
    svc = _svc()
    return svc.build_options(doc, setup_name) if svc is not None else None

__all__ = [
    'list_pdf_setups',
    'list_custom_pdf_setups',
    'list_all_pdf_setups',
    'get_custom_pdf_setup_data',
    'get_saved_pdf_setup',
    'set_saved_pdf_setup',
    'get_saved_pdf_separate',
    'set_saved_pdf_separate',
    'build_pdf_export_options',
]
