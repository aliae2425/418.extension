# -*- coding: utf-8 -*-
# Accès aux jeux de feuilles (collections) et dénombrements

try:
    from Autodesk.Revit import DB  # type: ignore
except Exception:
    DB = None  # type: ignore

class SheetSetRepository(object):
    # Retourne une liste de dicts {'Titre': str, 'Feuilles': int}
    def list_sets(self, doc):
        result_sets = []
        if DB is None or doc is None:
            return result_sets
        try:
            collections = DB.FilteredElementCollector(doc).OfClass(DB.SheetCollection).ToElements()
            all_sheets = DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet).ToElements()
        except Exception:
            return result_sets
        for coll in collections:
            coll_title = None
            try:
                coll_title = coll.Name
            except Exception:
                coll_title = 'Collection'
            count_in_coll = 0
            for vs in all_sheets:
                try:
                    if vs.SheetCollectionId == coll.Id:
                        count_in_coll += 1
                except Exception:
                    continue
            result_sets.append({'Titre': coll_title, 'Feuilles': count_in_coll})
        return result_sets
