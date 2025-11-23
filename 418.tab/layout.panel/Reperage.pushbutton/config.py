from pyrevit.userconfig import user_config
from pyrevit import DB, forms


activ_document   = __revit__.ActiveUIDocument.Document

def get_floorPlan(doc):
    return DB.FilteredElementCollector(doc).OfClass(DB.ViewPlan).ToElements()

def selectFloorType(doc):
    ops = []
    floorPlantype = {}

    for section in get_floorPlan(doc):
        if section.GetTypeId() not in floorPlantype:
            if section.GetTypeId().ToString() != '-1':
                # floorPlantype[section.GetTypeId().ToString()] = DB.Element.Name.__get__(activ_document.GetElement(section.GetTypeId()))
                floorPlantype[DB.Element.Name.__get__(doc.GetElement(section.GetTypeId()))] = section.GetTypeId()

    for key, value in floorPlantype.items():
        ops.append(key)

    return( floorPlantype[forms.CommandSwitchWindow.show(ops, message='Selectionner le type plan de niveau')])

def userConfig_ID(doc):
    try:
        # check if the section exist
        user_config.add_section('localplan')
        user_config.localplan.id = int(selectFloorType(doc).ToString())
        user_config.save_changes()
    except:
        user_config.localplan.id = int(selectFloorType(doc).ToString())
        user_config.save_changes()

if __name__ == "__main__":
    userConfig_ID(activ_document)