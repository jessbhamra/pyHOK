import clr
import os
import tempfile

from pyrevit import revit, DB
from Autodesk.Revit.DB import Transaction, Family, FamilySymbol, XYZ, Transform, Structure

uidoc = revit.uidoc

if not detail_components:
    print("No detail components selected.")
    # Exit or return here as needed

loaded_comp_families = {}

# Start a transaction in family_doc to load families and place instances
t = Transaction(family_doc, "Load and Place Detail Components")
t.Start()

try:
    # Try to get a reference from the active view in the family_doc
    active_view = family_doc.ActiveView
    if active_view and hasattr(active_view, 'SketchPlane') and active_view.SketchPlane:
        placement_ref = active_view.SketchPlane.GetPlane().Reference
    else:
        # If we can't get a reference from the active view's SketchPlane, try reference planes:
        reference_planes = DB.FilteredElementCollector(family_doc) \
                             .OfClass(DB.ReferencePlane) \
                             .ToElements()
        if reference_planes:
            # Use the first reference plane found
            placement_ref = reference_planes[0].GetPlane().Reference
        else:
            # If no reference planes exist, create one:
            # Create a simple reference plane
            rp_trans = Transaction(family_doc, "Create Reference Plane")
            rp_trans.Start()
            # Create a reference plane along the origin
            ref_plane = family_doc.FamilyCreate.NewReferencePlane(
                XYZ(0,0,0),
                XYZ(1,0,0),
                XYZ(0,1,0),
                family_doc.ActiveView
            )
            rp_trans.Commit()
            placement_ref = ref_plane.GetPlane().Reference

    for comp in detail_components:
        if not isinstance(comp, DB.FamilyInstance):
            continue

        symbol = comp.Symbol
        if symbol is None:
            continue

        symbol_name = symbol.Name
        comp_family = symbol.Family
        fam_name = comp_family.Name

        # If this family hasn't been loaded into family_doc yet, do so
        if fam_name not in loaded_comp_families:
            # Extract the family from the project to a temp RFA file
            try:
                fam_doc = doc.EditFamily(comp_family)
                temp_dir = tempfile.gettempdir()
                temp_family_path = os.path.join(temp_dir, fam_name + ".rfa")

                if os.path.exists(temp_family_path):
                    os.remove(temp_family_path)

                fam_doc.SaveAs(temp_family_path)
                fam_doc.Close(False)

                # Load the family into family_doc
                new_fam_ref = clr.Reference[Family]()
                if family_doc.LoadFamily(temp_family_path, new_fam_ref):
                    new_fam = new_fam_ref.Value
                    loaded_comp_families[fam_name] = new_fam
                else:
                    print("Failed to load family '{}' into the family_doc.".format(fam_name))
                    continue
            except Exception as ex:
                print("Error editing/loading family '{}': {}".format(fam_name, ex))
                continue
        else:
            new_fam = loaded_comp_families[fam_name]

        # Find the matching symbol by name in the loaded family
        new_comp_symbol = None
        for fsid in new_fam.GetFamilySymbolIds():
            fs = family_doc.GetElement(fsid)
            if fs and fs.Name == symbol_name:
                new_comp_symbol = fs
                break

        if not new_comp_symbol:
            print("Could not find symbol '{}' in family '{}'. Skipping.".format(symbol_name, fam_name))
            continue

        # Activate the symbol if not active
        if not new_comp_symbol.IsActive:
            new_comp_symbol.Activate()
            family_doc.Regenerate()

        # Determine the placement point (using bounding box center from the project doc)
        bbox = comp.get_BoundingBox(current_view)
        if bbox:
            comp_center = (bbox.Min + bbox.Max) * 0.5
        else:
            print("No bounding box for component {}. Skipping.".format(comp.Id))
            continue

        # Transform the point if necessary. For now, assume no transform needed:
        transformed_point = Transform.Identity.OfPoint(comp_center)

        try:
            # Place the instance in the family doc
            # Using the reference from the active view or a created reference plane
            new_instance = family_doc.FamilyCreate.NewFamilyInstance(
                transformed_point,
                new_comp_symbol,
                placement_ref,
                Structure.StructuralType.NonStructural
            )
        except Exception as e:
            print("Failed to place detail component in family: {}".format(e))
            continue

    # After processing all components
    t.Commit()
except Exception as e:
    print("An error occurred during transaction: {}".format(e))
    t.RollBack()
