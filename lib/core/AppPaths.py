# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

# _lib_dir = 418.extension/lib/
_lib_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class AppPaths(object):
    def resources_dir(self):
        return os.path.join(_lib_dir, 'ui', 'GUI', 'resources')

    def resource_path(self, filename):
        return os.path.join(self.resources_dir(), filename)
