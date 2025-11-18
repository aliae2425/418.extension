# -*- coding: utf-8 -*-
# Aides système de fichiers minimales

import os

class FileSystem(object):
    def exists(self, path):
        try:
            return os.path.exists(path)
        except Exception:
            return False

    def ensure_dir(self, path):
        try:
            if not os.path.exists(path):
                os.makedirs(path)
            return True
        except Exception:
            return False
