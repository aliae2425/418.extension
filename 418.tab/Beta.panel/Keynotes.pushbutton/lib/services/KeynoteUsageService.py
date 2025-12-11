# -*- coding: utf-8 -*-
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInParameter, ElementId

class KeynoteUsageService(object):
    def __init__(self, doc):
        self._doc = doc

    def get_usage_counts(self):
        """Returns a dictionary {keynote_value: count}"""
        counts = {}
        
        # 1. Collect all elements that might have a keynote
        # We'll check both Instances and Types because Keynotes can be assigned to both.
        # However, iterating EVERYTHING is slow.
        # Let's try to filter for elements that have the parameter.
        
        # It's hard to filter "Has Parameter" efficiently for all categories.
        # We will iterate over all elements that are not view-specific and not internal.
        
        # Strategy: Get all elements. Check parameter.
        # To optimize, maybe we only care about categories that can have keynotes?
        # That's almost everything.
        
        # Let's try a broad collector but exclude some things if possible.
        # For now, simple iteration.
        
        collector = FilteredElementCollector(self._doc).WhereElementIsNotElementType()
        
        for element in collector:
            self._check_element(element, counts)
            
        # Also check types?
        # If a Type has a Keynote, does it count as 1 usage? 
        # Or should we count how many instances of that type exist?
        # The user request "nombre de fois que la keynotes est utiliser" usually implies instances in the model.
        # If a Keynote is on a Type, and there are 10 instances, it's effectively used 10 times.
        # But the parameter value is on the Type.
        
        # Let's stick to counting where the parameter is explicitly set for now.
        # If the user sets Keynote on a Wall Type, we count it as 1 usage (the type).
        # If they want instance counts for type-based keynotes, that's much more complex logic (resolving inheritance).
        
        type_collector = FilteredElementCollector(self._doc).WhereElementIsElementType()
        for element in type_collector:
            self._check_element(element, counts)
            
        return counts

    def _check_element(self, element, counts):
        try:
            param = element.get_Parameter(BuiltInParameter.KEYNOTE_PARAM)
            if param and param.HasValue:
                val = param.AsString()
                if val:
                    counts[val] = counts.get(val, 0) + 1
        except Exception:
            pass
