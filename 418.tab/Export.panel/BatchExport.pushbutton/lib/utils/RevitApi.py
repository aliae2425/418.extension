# -*- coding: utf-8 -*-
# Façade API Revit pour isoler les imports .NET

class RevitApi(object):
    def __init__(self):
        try:
            from Autodesk.Revit import DB  # type: ignore
        except Exception:
            DB = None  # type: ignore
        self.DB = DB

    # Retourne le document actif si accessible via __revit__
    def active_doc(self):
        try:
            return __revit__.ActiveUIDocument.Document  # type: ignore
        except Exception:
            return None
