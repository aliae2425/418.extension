# -*- coding: utf-8 -*-

__title__ = "Keynotes Editor"
__doc__ = """
    Editeur de fichier Keynotes
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from lib.ui.windows.MainWindowController import MainWindowController

if __name__ == "__main__":
    ctrl = MainWindowController()
    ctrl.show()
