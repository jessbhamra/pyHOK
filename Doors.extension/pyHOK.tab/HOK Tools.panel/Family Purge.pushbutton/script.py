# -*- coding: utf-8 -*-
# Family Purge (biggest-first) for pyRevit — API-only, SILENT, no renaming, CSV export
# - Scans editable, non in-place families
# - Ranks by temp SaveAs to %TEMP%/<FamilyName>.rfa (no rename risk)
# - Purges via API (imports, images, unused family types, unused materials, deletable element types)
# - Reloads into project (overwrite) with NO project transaction
# - Suppresses warnings in purge transactions
# - Emits CSV to %TEMP%\pyrevit_family_purge\ and prints a clickable link

from Autodesk.Revit import DB, UI
from Autodesk.Revit.DB import (
    Transaction, FilteredElementCollector, Family, SaveAsOptions, ElementId,
    ImportInstance, ImageType, ElementType, Material, FamilyType
)
from pyrevit import forms, revit, script, coreutils
import System
from System.IO import Path, File, FileInfo, Directory
from System.Text import UTF8Encoding
import re, uuid, traceback, datetime

uidoc = __revit__.ActiveUIDocument
doc   = uidoc.Document
logger = coreutils.logger.get_logger(__name__)
output = script.get_output()

# ----------------------------
# Failure suppression (silent transactions)
# ----------------------------
class _SwallowFailures(DB.IFailuresPreprocessor):
    def PreprocessFailures(self, failuresAccessor):
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
    t = Transaction(rdoc, name)
    opts = t.GetFailureHandlingOptions()
    opts.SetClearAfterRollback(True)
    opts.SetForcedModalHandling(False)
    opts.SetFailuresPreprocessor(_SwallowFailures())
    t.SetFailureHandlingOptions(opts)
    return t

# ----------------------------
# Temp file helpers (NO RENAME)
# ----------------------------
_illegal = re.compile(r'[\\/:\*\?"<>\|\x00-\x1F]')

def _has_illegal_filename_chars(name):
    return bool(_illegal.search(name or ""))

def _sanitize_for_file(name):
    return _illegal.sub('_', name or "Project")

def temp_dir():
    d = Path.Combine(Path.GetTempPath(), "pyrevit_family_purge")
    if not Directory.Exists(d):
        Directory.CreateDirectory(d)
    return d

def build_preserving_name_path(fdoc):
    """Return %TEMP%/<FamilyName>.rfa if legal; else None (skip sizing to avoid rename)."""
    famname = (fdoc.Title or "").strip()
    if not famname or _has_illegal_filename_chars(famname):
        return None
    return Path.Combine(temp_dir(), famname + ".rfa")

def file_size_kb(path):
    try:
        if not File.Exists(path):
            return None
        return int(round(FileInfo(path).Length / 1024.0))
    except:
        return None

def save_as_exact_name(family_doc, exact_path):
    """SaveAs to exact_path (which must be <FamilyName>.rfa). This does not rename in-project."""
    sao = SaveAsOptions()
    sao.OverwriteExistingFile = True
    try:
        sao.Compact = True
    except:
        pass
    d = Path.GetDirectoryName(exact_path)
    if d and not Directory.Exists(d):
        Directory.CreateDirectory(d)
    family_doc.SaveAs(exact_path, sao)
    if not File.Exists(exact_path) or FileInfo(exact_path).Length == 0:
        raise Exception("Temp SaveAs failed or produced empty file: {}".format(exact_path))

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

def ListElementIds(seq):
    lst = System.Collections.Generic.List[ElementId]()
    for x in seq:
        lst.Add(x if isinstance(x, ElementId) else ElementId(int(x)))
    return lst

# ----------------------------
# Purge primitives (inside family doc, silent)
# ----------------------------
def delete_elements(fdoc, ids, label):
    if not ids:
        return 0
    deleted = 0
    with _silent_tx(fdoc, "Purge: {}".format(label)) as t:
        t.Start()
        try:
            fdoc.Delete(ListElementIds(ids))
            deleted = len(ids)
            t.Commit()
            return deleted
        except:
            t.RollBack()
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
    to_del.extend([e.Id for e in FilteredElementCollector(fdoc).OfClass(ImportInstance)])
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
            ids = e.GetMaterialIds(False)
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
# Gather candidates & pre-rank by size (no rename)
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

rank_info = []  # (family, pre_kb, can_size)
for fam in candidates:
    famdoc = None
    pre_kb = -1
    can_size = True
    try:
        famdoc = doc.EditFamily(fam)
        pre_path = build_preserving_name_path(famdoc)
        if pre_path:
            save_as_exact_name(famdoc, pre_path)   # %TEMP%/<FamilyName>.rfa
            size = file_size_kb(pre_path)
            pre_kb = size if size is not None else -1
            cleanup_temp(pre_path)
        else:
            pre_kb = -1
            can_size = False
    except Exception:
        pre_kb = -1
        logger.debug("Pre-size failed for '{}'\n{}".format(fam.Name, traceback.format_exc()))
    finally:
        if famdoc:
            try: famdoc.Close(False)
            except: pass
    rank_info.append((fam, pre_kb, can_size))

rank_info.sort(key=lambda x: x[1], reverse=True)
worklist = rank_info if process_all else rank_info[:n_default]

# ----------------------------
# Purge + reload (silent) — no renaming
# ----------------------------
results = []
with forms.ProgressBar(title='Purging families (silent, no-rename)...', step=1, cancellable=True) as pb:
    for i, (fam, pre_kb, can_size) in enumerate(worklist):
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

            deleted = purge_family_api_only(famdoc)
            row["Deleted Items"] = deleted

            # Post size (only if we can SaveAs using the exact family name)
            if can_size:
                post_path = build_preserving_name_path(famdoc)
                if post_path:
                    try:
                        save_as_exact_name(famdoc, post_path)
                        post_kb = file_size_kb(post_path)
                    except Exception:
                        post_kb = None
                        row["Status"] = (row["Status"] + " | " if row["Status"] else "") + "post-size unknown"
                else:
                    post_kb = None
                    row["Status"] = (row["Status"] + " | " if row["Status"] else "") + "size-scan skipped (illegal chars)"
            else:
                post_kb = None
                row["Status"] = (row["Status"] + " | " if row["Status"] else "") + "size-scan skipped (illegal chars)"

            row["Post Size (KB)"] = post_kb
            if row["Pre Size (KB)"] is not None and post_kb is not None:
                row["Saved (KB)"] = max(0, row["Pre Size (KB)"] - post_kb)

            # Reload into project (NO transaction allowed here)
            opts = OverwriteLoadOptions()
            if doc.IsModifiable:
                raise Exception("Project doc has an open transaction. Close it before LoadFamily.")
            famdoc.LoadFamily(doc, opts)
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
# Report (list-of-lists) + CSV export
# ----------------------------
headers = ["Family", "Pre Size (KB)", "Post Size (KB)", "Saved (KB)", "Deleted Items", "Status"]

def _fmt(v): return "-" if v is None else v

results_sorted = sorted(results, key=lambda r: (r.get("Saved (KB)") or 0, r.get("Pre Size (KB)") or 0), reverse=True)

table_rows = []
for r in results_sorted:
    table_rows.append([
        r.get("Family", ""),
        _fmt(r.get("Pre Size (KB)")),
        _fmt(r.get("Post Size (KB)")),
        _fmt(r.get("Saved (KB)")),
        _fmt(r.get("Deleted Items")),
        r.get("Status") or "",
    ])

output.print_md("### Family Purge Results (silent, API-only, no-rename, largest-first)")
output.print_table(table_rows, columns=headers)

total_saved = sum([(r.get("Saved (KB)") or 0) for r in results_sorted])
output.print_md("**Total saved ~ {} KB (~{:.2f} MB)**".format(total_saved, total_saved/1024.0))

# ---- CSV: write to %TEMP%\pyrevit_family_purge and linkify
def _csv_escape(s):
    if s is None:
        s = ""
    s = unicode(s) if not isinstance(s, unicode) else s
    s = s.replace(u'"', u'""')
    if u',' in s or u'\n' in s or u'"' in s:
        return u'"' + s + u'"'
    return s

def write_csv_and_link(rows, headers, total_saved_kb):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    proj = _sanitize_for_file(doc.Title)
    csv_path = Path.Combine(temp_dir(), u"FamilyPurgeResults_{}_{}.csv".format(proj, ts))

    # Use .NET StreamWriter to avoid IronPython csv+unicode quirks; add UTF-8 BOM for Excel
    sw = System.IO.StreamWriter(csv_path, False, UTF8Encoding(True))
    try:
        sw.WriteLine(u",".join([_csv_escape(h) for h in headers]))
        for row in rows:
            sw.WriteLine(u",".join([_csv_escape(x) for x in row]))
        sw.WriteLine(u"")
        sw.WriteLine(u"{},{}".format(_csv_escape(u"Total saved (KB)"), _csv_escape(total_saved_kb)))
    finally:
        sw.Close()

    output.print_md("**CSV saved:** {}".format(csv_path))
    output.linkify(csv_path, title="Open CSV")

write_csv_and_link(table_rows, headers, total_saved)
