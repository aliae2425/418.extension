# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import os
import csv
import io
import sys

class Profile(object):

    def __init__(self, name, data=None):
        self.name = name
        self.data = data if data else {}

class ConfigManagerService(object):

    KEYS = [
        'separate_format_folders',
        'create_subfolders',
        'sheet_param_carnetcombo',
        'sheet_param_dwgcombo',
        'pattern_sheet',
        'pattern_set',
        'pattern_set_rows',
        'pathdossier',
        'pattern_sheet_rows',
        'pdf_setup_name',
        'dwg_setup_name'
    ]

    def __init__(self):
        print("ConfigManagerService initialized")