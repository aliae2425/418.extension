# -*- coding: utf-8 -*-
try:
    from Autodesk.Revit import DB
except Exception:
    DB = None

class BipTranslator(object):
    def __init__(self):
        pass

    @staticmethod
    def get_bip_from_element_param(param):
        """Tente de récupérer le BuiltInParameter d'un paramètre d'élément."""
        if DB is None or param is None:
            return None
        try:
            defi = param.Definition
            if isinstance(defi, DB.InternalDefinition):
                bip = defi.BuiltInParameter
                if bip != DB.BuiltInParameter.INVALID:
                    return str(bip)
        except Exception:
            pass
        return None

    @staticmethod
    def get_localized_name(bip_name):
        """Retourne le nom localisé d'un BuiltInParameter (str)."""
        if DB is None or not bip_name:
            return bip_name
        try:
            bip = getattr(DB.BuiltInParameter, bip_name, None)
            if bip:
                return DB.LabelUtils.GetLabelFor(bip)
        except Exception:
            pass
        return bip_name

    @staticmethod
    def get_bip_enum(bip_name):
        if DB is None:
            return None
        return getattr(DB.BuiltInParameter, bip_name, None)
