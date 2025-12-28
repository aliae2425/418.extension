# -*- coding: utf-8 -*-
"""This button is not required.

Auto-renaming views when they are placed on a sheet is handled by the global
hook located at the root of the extension: startup.py
"""


if __name__ == "__main__":
    print("Auto-rename hook is loaded via root startup.py")


def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    """pyRevit smartbutton initializer.

    Returning True keeps the button enabled and prevents
    'module has no attribute __selfinit__' errors.
    """
    return True
