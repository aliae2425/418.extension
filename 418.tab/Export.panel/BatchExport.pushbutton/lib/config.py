# -*- coding: utf-8 -*-
"""Adapter simple pour le stockage utilisateur via un module user_Config externe.

Expose une petite classe UserConfigStore avec un espace de noms, fournissant:
- get(key, default=None)
- set(key, value)
- get_list(key, default=None)  # accepte CSV ou liste

Cette implémentation tente différentes signatures usuelles de user_Config
pour rester compatible avec plusieurs implémentations.
"""



from pyrevit.userconfig import user_config as UC
from pyrevit import DB, forms

# Compat: alias de type pour chaînes (Py2 basestring / Py3 str)
try:
    BASESTRING_T = basestring  # type: ignore
except NameError:
    BASESTRING_T = str  # type: ignore



class UserConfigStore:
    """Adaptateur simple pour le stockage utilisateur via un module user_Config externe.

    Méthodes:
    - get(key, default=None)
    - set(key, value)
    """

    def __init__(self, namespace='batch_export'):
        self.namespace = namespace

    def set(self, key, value):
        try:
            UC.add_section("batch_export")
        except Exception:
            pass
        try:
            sval = str(value)
        except Exception:
            try:
                sval = u"{}".format(value)
            except Exception:
                sval = value

        try:
            if key == "Export":
                UC.batch_export.Export = sval
            elif key == "ExportParFeuilles":
                UC.batch_export.ExportParFeuilles = sval
            elif key == "ExportDWG":
                UC.batch_export.ExportDWG = sval
            elif key == "PathDossier":
                UC.batch_export.PathDossier = sval
            else:
                # Fallback générique: créer/mettre à jour un attribut dynamique
                try:
                    setattr(UC.batch_export, key, sval)
                except Exception:
                    return False
            UC.save_changes()
            return True
        except Exception:
            return False

    def get(self, key, default=""):
        """Récupère une valeur, avec fallback sur getattr si get_option indisponible."""
        try:
            return UC.batch_export.get_option(key, default)
        except Exception:
            try:
                return getattr(UC.batch_export, key)
            except Exception:
                return default


