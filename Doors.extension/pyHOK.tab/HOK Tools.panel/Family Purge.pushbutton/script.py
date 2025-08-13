# -*- coding: utf-8 -*-
# Family Purge (biggest-first) for pyRevit
# - Scans loadable (non in-place) families
# - Ranks by temp SaveAs size (safe + unique temp filenames)
# - Purges via Performance Adviser until stable
# - Reloads into project (overwrite)
# - Reports pre/post sizes and savings

from Autodesk.Revit import DB, UI
from Autodesk.Revit.DB import (
    Transaction, FilteredElementCollector, Family, SaveAsOptions,
    PerformanceAdviser, PerformanceAdviserRuleId
)
from pyrevit import forms, revit, script, coreutils
import System
from System import Guid
from System.IO import Path, File, FileInfo, Directory
import uuid
import re
import os
import traceback

# Optional config override for purge rule GUID (string)
PURGE_GUID = None
try:
    import config
    PURGE_GUID = getattr(config, 'PURGE_GUID', None)
except Exception:
    pass

uidoc = __revit__.ActiveUIDocument
doc   = uidoc.Document
logger = coreutils.logger.get_logger(__name__)
output = script.get_output()

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
        # Harmless on RFAs; supported on RVTs. Keep for completeness.
        sao.Compact = True
    except:
        pass
    # Ensure directory exists
    dirpath = Path.GetDirectoryName(path)
    if dirpath and not Directory.Exists(dirpath):
        Directory.CreateDirectory(dirpath)
    family_doc.SaveAs(path, sao)
    # Verify the write actually happened
    if not File.Exists(path) or FileInfo(path).Length == 0:
        raise Exception("Temp SaveAs failed or produced empty file: {}".format(path))

def cleanup_temp(*paths):
    for p in paths:
        try:
            if p and File.Exists(p):
                File.Delete(p)
        except:
            pass

# ----------------------------
# Performance Adviser (purge)
# ----------------------------
def find_purge_rule_id():
    pa = PerformanceAdviser.GetPerformanceAdviser()
    # Prefer name match (handles most locales with "purge" in string)
    for rid in pa.GetAllRuleIds():
        try:
            name = pa.GetRuleName(rid)
            if name and "purge" in name.lower():
                return rid
        except Exception:
            pass
    # Fallback to configured GUID
    if PURGE_GUID:
        g = Guid(PURGE_GUID)
        for rid in pa.GetAllRuleIds():
            try:
                if rid.Guid == g:
                    return rid
            except Exception:
                pass
    return None

def purge_family_doc(family_doc, rule_id, max_passes=6):
    pa = PerformanceAdviser.GetPerformanceAdviser()
    rule_ids = System.Collections.Generic.List[PerformanceAdviserRuleId]([rule_id])
    total_deleted = 0

    for _ in range(max_passes):
        failures = pa.ExecuteRules(family_doc, rule_ids)
        if not failures or failures.Count == 0:
            break

        purgable = set()
        for fmsg in failures:
            try:
                for eid in fmsg.GetFailingElements():
                    purgable.add(eid)
            except Exception:
                pass
        if not purgable:
            break

        with Transaction(family_doc, "Purge Unused (PA)") as t:
            t.Start()
            deleted_now = 0
            # Try bulk delete first
            try:
                family_doc.Delete(System.Collections.Generic.List[DB.ElementId](list(purgable)))
                deleted_now = len(purgable)
            except Exception:
                # Fallback one-by-one
                for eid in list(purgable):
                    try:
                        family_doc.Delete(eid)
                        deleted_now += 1
                    except Exception:
                        pass
            t.Commit()
            total_deleted += deleted_now

        if deleted_now == 0:
            break

    return total_deleted

class OverwriteLoadOptions(DB.IFamilyLoadOptions):
    def OnFamilyFound(self, familyInUse, overwriteParameterValues):
        return True
    def OnSharedFamilyFound(self, familyInUse, newFamily, source, overwriteParameterValues):
        return True

# ----------------------------
# Gather candidates & ranking
# ----------------------------
families = list(FilteredElementCollector(doc).OfClass(Family))
candidates = [f for f in families if f.IsEditable and not f.IsInPlace]

if not candidates:
    forms.alert("No loadable (non in-place) families found that are editable.", exitscript=True)

# Let user choose scope
n_default = min(25, max(5, int(len(candidates) * 0.2)))
choice = forms.CommandSwitchWindow.show(
    ["Top {}".format(n_default), "All"],
    message="How many families to process (ranked by pre-purge size)?"
)
process_all = (choice == "All")

# Pre-pass to measure sizes (safe temp files; tolerate failures)
rank_info = []  # (family, pre_size_kb, pre_path_for_cleanup)
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
        # Close without saving anything from the pre-pass
        if famdoc:
            try:
                famdoc.Close(False)
            except Exception:
                pass
        # We don't delete pre_path yet (keep for debugging if you want).
        # If you prefer auto-clean, uncomment:
        # cleanup_temp(pre_path)
    rank_info.append((fam, pre_kb, pre_path))

# Sort by size DESC
rank_info.sort(key=lambda x: x[1], reverse=True)
worklist = rank_info if process_all else rank_info[:n_default]

# ----------------------------
# Purge + reload
# ----------------------------
purge_rule = find_purge_rule_id()
if purge_rule is None:
    forms.alert("Could not find Performance Adviser 'Purge' rule.\n"
                "Tip: set config.PURGE_GUID = 'xxxxxxxx-xxxx-....' for your environment.",
                exitscript=True)

results = []  # rows for table

with forms.ProgressBar(title='Purging families...', step=1, cancellable=True) as pb:
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

            # Purge until stable
            deleted = purge_family_doc(famdoc, purge_rule, max_passes=6)
            row["Deleted Items"] = deleted

            # Measure post size (safe temp)
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

            # Reload into project (overwrite)
            opts = OverwriteLoadOptions()
            with Transaction(doc, "Reload Purged Family: {}".format(fam.Name)) as t:
                t.Start()
                famdoc.LoadFamily(doc, opts)
                t.Commit()

            row["Status"] = (row["Status"] + " | " if row["Status"] else "") + "Purged & Reloaded"

        except Exception as ex:
            row["Status"] = (row.get("Status") or "") + " ERROR: {}".format(ex)
            logger.error(traceback.format_exc())
        finally:
            if famdoc:
                try:
                    famdoc.Close(False)
                except Exception:
                    pass
            # Clean post temp (safe)
            cleanup_temp(post_path)

        results.append(row)

# ----------------------------
# Report
# ----------------------------
headers = ["Family", "Pre Size (KB)", "Post Size (KB)", "Saved (KB)", "Deleted Items", "Status"]
output.print_md("### Family Purge Results (largest-first)")
output.print_table(results, columns=headers)

total_saved = sum([r["Saved (KB)"] or 0 for r in results if r.get("Saved (KB)") is not None])
output.print_md("**Total saved ~ {} KB (~{:.2f} MB)**".format(total_saved, total_saved/1024.0))

