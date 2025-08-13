"""Family Purge"""

from Autodesk.Revit import DB, UI
from Autodesk.Revit.DB import Document, BuiltInCategory, Transaction, BuiltInParameterGroup, FamilyParameter, FamilyType, FilteredElementCollector
from Autodesk.Revit.UI.Selection import Selection, ObjectType
from pyrevit import forms, revit, coreutils, script
from pyrevit.forms import WPFWindow
import config
import System
from System.Collections.Generic import List


doc = __revit__.ActiveUIDocument.Document
ui = __revit__.ActiveUIDocument
logger = coreutils.logger.get_logger(__name__)


def purge_perf_adv(family_doc):
    purgeGuid = config.PURGE_GUID
    purgableElementIds = []
    performanceAdviser = DB.PerformanceAdviser.GetPerformanceAdviser()
    guid = System.Guid(purgeGuid)
    ruleId = None
    allRuleIds = performanceAdviser.GetAllRuleIds()
    for rule in allRuleIds:
    # Finds the PerformanceAdviserRuleId for the purge command
        if str(rule.Guid) == purgeGuid:
            ruleId = rule
    ruleIds = List[DB.PerformanceAdviserRuleId]([ruleId])
    for i in range(4):
    # Executes the purge
        failureMessages = performanceAdviser.ExecuteRules(family_doc, ruleIds)
        if failureMessages.Count > 0:
        # Retreives the elements
            purgableElementIds = failureMessages[0].GetFailingElements()
# Deletes the elements
    print("it's purgin' time...")
    with Transaction(family_doc, 'Its purgin time') as s:
        s.Start()
        try:
            family_doc.Delete(purgableElementIds)
            #print("purge attempt 1")
        except:
            for e in purgableElementIds:
                try:
                    family_doc.Delete(e)
                        #print("purge attempt 2")
                except:
                        #print("no purge")
                    pass
        s.Commit()   