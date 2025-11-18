# -*- coding: utf-8 -*-
# FACADE: redirige vers les classes de data/sheets.

from __future__ import unicode_literals

def _repo(cfg=None):
    try:
        from .data.sheets.SheetParameterRepository import SheetParameterRepository
        return SheetParameterRepository(config_store=cfg)
    except Exception:
        return None

def _sets():
    try:
        from .data.sheets.SheetSetRepository import SheetSetRepository
        return SheetSetRepository()
    except Exception:
        return None

def is_boolean_param_definition(param_def):
    repo = _repo()
    return repo.is_boolean_param_definition(param_def) if repo is not None else False

def filter_param_names(param_names, config_store):
    repo = _repo(config_store)
    return repo.filter_param_names(param_names) if repo is not None else param_names

def collect_sheet_parameter_names(doc, config_store):
    repo = _repo(config_store)
    return repo.collect_for_collections(doc) if repo is not None else []

def get_sheet_sets(doc):
    sets = _sets()
    return sets.list_sets(doc) if sets is not None else []

def picker_collect_project_parameter_names(doc, config_store):
    repo = _repo(config_store)
    return repo.collect_project_params(doc) if repo is not None else []

def picker_collect_sheet_instance_parameter_names(doc, config_store):
    repo = _repo(config_store)
    return repo.collect_sheet_instance_params(doc) if repo is not None else []

def picker_collect_sheet_parameter_names(doc, config_store):
    # alias vers collect_for_collections pour compat
    repo = _repo(config_store)
    return repo.collect_for_collections(doc) if repo is not None else []
