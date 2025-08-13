# -*- coding: utf-8 -*-
# Family Purge (biggest-first) for pyRevit — API-only + SILENT (suppressed warnings)
# - Scans editable, non in-place families
# - Ranks by temp SaveAs size (safe+unique temp filenames)
# - Purges via API (no Performance Adviser dependency)
# - Suppresses warnings/popups during purge & reload
# - Reloads into project (overwrite), reports size savings

from Autodesk.Revit import DB, UI
from Autodesk.Revit.DB import (
    Transaction, FilteredElementCollector, Family, SaveAsOptions, ElementId,
    ImportInstance, ImageType, ElementType, Material, FamilyType
)
from pyrevit import forms, revit, script, coreutils
import System
from System.IO import Path, File, FileInfo, Directory
from System import Guid
import uuid, re, traceback

uidoc = __revit__.ActiveUIDocument
doc   = uidoc.Document
logger = coreutils.logger.get_logger(__name__)
output = script.get_output()

# ----------------------------
# Failure suppression (silent tx)
# ----------------------------
class _SwallowFailures(DB.IFailuresPreprocessor):
    def PreprocessFailures(self, failuresAccessor):
        # Delete all warnings; continue processing
        try:
            for f in failuresAccessor.GetFailureMessages():
                try:
                    failuresAccessor.DeleteWarning(f)
                except:
                    pass
        except:
            pass
        return DB.FailureProcessingResult.Continue

def _silent_tx(rdoc, name):
    """Create a Transaction with warning dialogs suppressed."""
    t = Transaction(rdoc, name)
    opts = t.GetFailureHandlingOptions()
    opts.SetClearAfterRollback(True)
    opts.SetForcedModalHandling(False)
    opts.SetFailuresPreprocessor(_SwallowFailures())
    t.SetFailureHandlingOptions(opts)
    return t

# ----------------------------
# Helpers (hardened temp files)
# ----------------------------
_illegal = re.compile(r'[\\/:\*\?"<>\|\x00-\x1F]')

def _sanitize(s):
    if not s:
        return "untitled"
    return _illegal.sub('_', s)

def tmp_rfa_path(fam_name, suffix="pre"):
    tmpdir = Path.GetTempPath()
    if not Directory.Exists(tmpdir):
        Directory.CreateDirectory(tmpdir)
    safe_fam  = _sanitize(fam_name)
    safe_proj = _sanitize(doc.Title)
    u = str(uuid.uuid4())[:8]  # uniqueness to avoid collisions
    return Path.Combine(tmpdir, "{}_{}_{}_{}.rfa".format(safe_fam, safe_proj, suffix, u))

def file_size_kb(path):
    try:
        if not File.Exists(path):
            return None
        return int(round(FileInfo(path).Length / 1024.0))
    except:
        return None

def save_as_temp(family_doc, path):
    sao = SaveAsOptions()
    sao.OverwriteExistingFile = True
    try:
        sao.Compact = True
    except:
        pass
    d = Path.GetDirectoryName(path)
    if d and not Directory.Exists(d):
        Directory.CreateDirectory(d)
    family_doc.SaveAs(path, sao)
    if not File.Exists(path) or FileInfo(path).Length == 0:
        raise Exception("Temp SaveAs failed or produced empty file: {}".format(path))

def cleanup_temp(*paths):
    for p in paths:
        try:
            if p and File.Exists(p):
                File.Delete(p)
        except:
            pass

class OverwriteLoadOptions(DB.IFamilyLoadOptions):
    def OnFamilyFound(self, familyInUse, overwriteParameterValues):
        return True
    def OnSharedFamilyFound(self, familyInUse, newFamily, source, overwriteParameterValues):
        return True

# Utility to build a .NET List[ElementId]
def ListElementIds(seq):
    lst = System.Collections.Generic.List[ElementId]()
    for x in seq:
        lst.Add(x if isinstance(x, ElementId) else ElementId(int(x)))
    return lst

# ----------------------------
# Purge primitives (inside family doc, SILENT)
# ----------------------------
def delete_elements(fdoc, ids, label):
    if not ids:
        return 0
    deleted = 0
    # Bulk attempt
    with _silent_tx(fdoc, "Purge: {}".format(label)) as t:
        t.Start()
        try:
            fdoc.Delete(ListElementIds(ids))
            deleted = len(ids)
            t.Commit()
            return deleted
        except:
            t.RollBack()
    # Fallback one-by-one (also silent)
    with _silent_tx(fdoc, "Purge (fallback): {}".format(label)) as t:
        t.Start()
        for eid in ids:
            try:
                fdoc.Delete(eid)
                deleted += 1
            except:
                pass
        t.Commit()
    return deleted

def purge_imports_and_images(fdoc):
    to_del = []
    # Imported CAD instances
    to_del.extend([e.Id for e in FilteredElementCollector(fdoc).OfClass(ImportInstance)])
    # Embedded images (types)
    to_del.extend([e.Id for e in FilteredElementCollector(fdoc).OfClass(ImageType)])
    return delete_elements(fdoc, to_del, "Imports & Images")

def purge_unused_family_types(fdoc):
    fm = fdoc.FamilyManager
    try:
        current_type = fm.CurrentType
        keep_id = current_type.Id if isinstance(current_type, FamilyType) else None
        all_types = list(fm.Types)
    except:
        return 0
    if len(all_types) <= 1:
        return 0
    to_del = []
    for ft in all_types:
        try:
            if keep_id and ft.Id == keep_id:
                continue
            to_del.append(ft.Id)
        except:
            pass
    return delete_elements(fdoc, to_del, "Unused Family Types")

def _collect_used_material_ids(fdoc):
    used = set()
    elems = FilteredElementCollector(fdoc).WhereElementIsNotElementType().ToElements()
    for e in elems:
        try:
            ids = e.GetMaterialIds(False)  # exclude paints
            if ids:
                for mid in ids:
                    used.add(mid.IntegerValue)
        except:
            pass
    return used

def purge_unused_materials(fdoc):
    used_ids = _collect_used_material_ids(fdoc)
    mats = list(FilteredElementCollector(fdoc).OfClass(Material))
    to_del = []
    for m in mats:
        try:
            nm = (m.Name or "").strip().lower()
            if nm in ("default", "global"):
                continue
            if m.Id.IntegerValue not in used_ids:
                to_del.append(m.Id)
        except:
            pass
    return delete_elements(fdoc, to_del, "Unused Materials")

def purge_unused_element_types_best_effort(fdoc):
    # Delete any element types Revit permits (skip FamilyTypes handled above)
    types = FilteredElementCollector(fdoc).WhereElementIsElementType().ToElements()
    famtype_ids = set()
    try:
        famtype_ids = set([ft.Id.IntegerValue for ft in fdoc.FamilyManager.Types])
    except:
        pass
    to_del = []
    for t in types:
        try:
            if t.Id.IntegerValue in famtype_ids:
                continue
            to_del.append(t.Id)
        except:
            pass
    return delete_elements(fdoc, to_del, "Unused Element Types (best-effort)")

def purge_family_api_only(fdoc):
    total = 0
    total += purge_imports_and_images(fdoc)
    total += purge_unused_family_types(fdoc)
    total += purge_unused_materials(fdoc)
    total += purge_unused_element_types_best_effort(fdoc)
    return total

# ----------------------------
# Gather candidates & rank by size
# ----------------------------
families = list(FilteredElementCollector(doc).OfClass(Family))
candidates = [f for f in families if f.IsEditable and not f.IsInPlace]
if not candidates:
    forms.alert("No loadable (non in-place) families found that are editable.", exitscript=True)

n_default = min(25, max(5, int(len(candidates) * 0.2)))
choice = forms.CommandSwitchWindow.show(
    ["Top {}".format(n_default), "All"],
    message="How many families to process (ranked by pre-purge size)?"
)
process_all = (choice == "All")

# Pre-pass: temp-save to measure size
rank_info = []  # (family, pre_kb, pre_path_for_debug)
for fam in candidates:
    famdoc = None
    pre_path = None
    pre_kb = -1
    try:
        famdoc = doc.EditFamily(fam)
        pre_path = tmp_rfa_path(fam.Name, "pre")
        save_as_temp(famdoc, pre_path)
        size = file_size_kb(pre_path)
        pre_kb = size if size is not None else -1
    except Exception:
        pre_kb = -1
        logger.debug("Pre-size failed for '{}'\n{}".format(fam.Name, traceback.format_exc()))
    finally:
        if famdoc:
            try: famdoc.Close(False)
            except: pass
    rank_info.append((fam, pre_kb, pre_path))

rank_info.sort(key=lambda x: x[1], reverse=True)
worklist = rank_info if process_all else rank_info[:n_default]

# ----------------------------
# Purge + reload (SILENT)
# ----------------------------
results = []
with forms.ProgressBar(title='Purging families (silent, API-only)...', step=1, cancellable=True) as pb:
    for i, (fam, pre_kb, _) in enumerate(worklist):
        if pb.cancelled:
            break
        pb.update_progress(i+1, len(worklist))

        row = {
            "Family": fam.Name,
            "Pre Size (KB)": pre_kb if pre_kb >= 0 else None,
            "Post Size (KB)": None,
            "Saved (KB)": None,
            "Deleted Items": 0,
            "Status": ""
        }

        famdoc = None
        post_path = None
        try:
            famdoc = doc.EditFamily(fam)

            # Purge (silent)
            deleted = purge_family_api_only(famdoc)
            row["Deleted Items"] = deleted

            # Measure post size
            post_path = tmp_rfa_path(fam.Name, "post")
            try:
                save_as_temp(famdoc, post_path)
                post_kb = file_size_kb(post_path)
            except Exception:
                post_kb = None
                row["Status"] = (row.get("Status") or "") + " (post-size unknown)"
            row["Post Size (KB)"] = post_kb
            if row["Pre Size (KB)"] is not None and post_kb is not None:
                row["Saved (KB)"] = max(0, row["Pre Size (KB)"] - post_kb)

            # Reload purged family into project (overwrite) — NO transaction allowed here
            opts = OverwriteLoadOptions()
            try:
                if doc.IsModifiable:
                    # Paranoia: we should never be inside a TX on the project doc here
                    # (Our code doesn't open one; this catches anything external)
                    raise Exception("Project document is modifiable (open transaction). Close it before LoadFamily.")
                famdoc.LoadFamily(doc, opts)
                row["Status"] = (row["Status"] + " | " if row["Status"] else "") + "Purged & Reloaded"
            except Exception as ex:
                row["Status"] = (row.get("Status") or "") + " RELOAD FAILED: {}".format(ex)


            row["Status"] = (row["Status"] + " | " if row["Status"] else "") + "Purged & Reloaded"

        except Exception as ex:
            row["Status"] = (row.get("Status") or "") + " ERROR: {}".format(ex)
            logger.error(traceback.format_exc())
        finally:
            if famdoc:
                try: famdoc.Close(False)
                except: pass
            cleanup_temp(post_path)

        results.append(row)

# ----------------------------
# Report
# ----------------------------
headers = ["Family", "Pre Size (KB)", "Post Size (KB)", "Saved (KB)", "Deleted Items", "Status"]
output.print_md("### Family Purge Results (silent, API-only, largest-first)")
output.print_table(results, columns=headers)
total_saved = sum([r["Saved (KB)"] or 0 for r in results if r.get("Saved (KB)") is not None])
output.print_md("**Total saved ~ {} KB (~{:.2f} MB)**".format(total_saved, total_saved/1024.0))
