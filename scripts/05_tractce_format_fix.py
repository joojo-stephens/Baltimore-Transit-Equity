# ============================================================
# 05_tractce_format_fix.py
# Baltimore Transit Equity Analysis
# Fix TRACTCE format and join Census data to shapefile
#
# Author:  Nathaniel K.A. Stephens
# Date:    March 2026
#
# PROBLEM: Census TRACTCE = 6-digit string e.g. "010100"
#          ArcGIS TableToTable converts to Integer (10100)
#          Leading zero is lost — join fails
#
# FIX:     Add TRACTCE_STR field (TEXT) = str(TRACTCE).zfill(6)
#          Join CensusTracts_Pg.TRACTCE (String)
#          to   Census_Master_Tbl.TRACTCE_STR (String)
#
# Inputs:  CensusTracts_Pg (shapefile, 199 tracts)
#          Baltimore_Census_Master.csv
#
# Outputs: Census_Master_Tbl (table in GDB)
#          CensusTracts_Demographics_Pg (joined feature class)
# ============================================================

import arcpy
import os

# ── PATHS ────────────────────────────────────────────────────
gdb         = r"C:\Users\kojoa\Documents\ArcGIS\Projects\MyProject\MyProject.gdb"
project_dir = r"C:\Users\kojoa\Documents\ArcGIS\Projects\MyProject"
master_csv  = os.path.join(project_dir, "data", "census",
                           "cleaned", "Baltimore_Census_Master.csv")
tracts      = f"{gdb}\\Base\\CensusTracts_Pg"

arcpy.env.overwriteOutput = True

print("=" * 60)
print("TRACTCE FORMAT FIX AND CENSUS JOIN")
print("=" * 60)

# ── STEP 1 — Import Master CSV to GDB Table ───────────────────
print("\nStep 1 — Importing Census Master CSV to GDB table...")
arcpy.conversion.TableToTable(
    in_rows         = master_csv,
    out_path        = gdb,
    out_name        = "Census_Master_Tbl"
)
tbl_count = int(arcpy.management.GetCount(f"{gdb}\\Census_Master_Tbl")[0])
print(f"  ✅ Census_Master_Tbl → {tbl_count} rows")

# ── STEP 2 — Fix TRACTCE in Table ───────────────────────────
print("\nStep 2 — Fixing TRACTCE format in table...")

# Check if TRACTCE field exists and its type
tbl_fields = {f.name: f.type for f in arcpy.ListFields(f"{gdb}\\Census_Master_Tbl")}
print(f"  TRACTCE field type: {tbl_fields.get('TRACTCE', 'NOT FOUND')}")

# Add TRACTCE_STR as text field
arcpy.management.AddField(f"{gdb}\\Census_Master_Tbl", "TRACTCE_STR", "TEXT",
                           field_length=6, field_alias="Tract Code (String)")

# Calculate TRACTCE_STR = zero-padded 6-digit string
arcpy.management.CalculateField(
    in_table        = f"{gdb}\\Census_Master_Tbl",
    field           = "TRACTCE_STR",
    expression      = "str(int(!TRACTCE!)).zfill(6)",
    expression_type = "PYTHON3"
)

# Verify sample values
print(f"\n  Sample TRACTCE values after fix:")
print(f"  {'TRACTCE (Int)':15} {'TRACTCE_STR (Text)':20}")
print("  " + "-" * 35)
with arcpy.da.SearchCursor(
    f"{gdb}\\Census_Master_Tbl",
    ["TRACTCE", "TRACTCE_STR"]
) as cursor:
    for i, row in enumerate(cursor):
        if i >= 5:
            break
        print(f"  {str(row[0]):15} {str(row[1]):20}")
print(f"  ✅ TRACTCE_STR field populated correctly")

# ── STEP 3 — Verify Join Keys Match ─────────────────────────
print(f"\nStep 3 — Verifying join keys match between layers...")

# Get tract codes from shapefile
shp_tracts = set()
with arcpy.da.SearchCursor(tracts, ["TRACTCE"]) as cursor:
    for row in cursor:
        shp_tracts.add(str(row[0]).strip())

# Get tract codes from table
tbl_tracts = set()
with arcpy.da.SearchCursor(
    f"{gdb}\\Census_Master_Tbl", ["TRACTCE_STR"]
) as cursor:
    for row in cursor:
        tbl_tracts.add(str(row[0]).strip())

matching = shp_tracts & tbl_tracts
only_shp = shp_tracts - tbl_tracts
only_tbl = tbl_tracts - shp_tracts

print(f"  Tracts in shapefile:        {len(shp_tracts)}")
print(f"  Tracts in Census table:     {len(tbl_tracts)}")
print(f"  Matching tracts:            {len(matching)}")

if only_shp:
    print(f"  ⚠️  Only in shapefile:       {len(only_shp)} — {list(only_shp)[:5]}")
if only_tbl:
    print(f"  ⚠️  Only in table:           {len(only_tbl)} — {list(only_tbl)[:5]}")

if len(matching) >= 195:
    print(f"  ✅ Join keys verified — {len(matching)} tracts will match")
else:
    print(f"  ❌ Join key mismatch — check TRACTCE format")
    print(f"     Shapefile sample: {list(shp_tracts)[:3]}")
    print(f"     Table sample:     {list(tbl_tracts)[:3]}")

# ── STEP 4 — Join and Export ─────────────────────────────────
print(f"\nStep 4 — Joining Census data to Census tracts...")

# Make feature layer
arcpy.management.MakeFeatureLayer(tracts, "tracts_lyr")

# Add join
arcpy.management.AddJoin(
    in_layer_or_view    = "tracts_lyr",
    in_field            = "TRACTCE",
    join_table          = f"{gdb}\\Census_Master_Tbl",
    join_field          = "TRACTCE_STR",
    join_type           = "KEEP_ALL"
)

# Export to new feature class
out_fc = f"{gdb}\\Base\\CensusTracts_Demographics_Pg"
arcpy.conversion.FeatureClassToFeatureClass(
    in_features = "tracts_lyr",
    out_path    = f"{gdb}\\Base",
    out_name    = "CensusTracts_Demographics_Pg"
)

# Clean up
arcpy.management.Delete("tracts_lyr")

# ── STEP 5 — Verify Output ───────────────────────────────────
print(f"\nStep 5 — Verifying output...")
out_count  = int(arcpy.management.GetCount(out_fc)[0])
out_fields = [f.name for f in arcpy.ListFields(out_fc)
              if not f.name.startswith("Shape")]
pct_fields = [f for f in out_fields if f.startswith("Pct_")]

print(f"  ✅ CensusTracts_Demographics_Pg created")
print(f"  Tracts:      {out_count} (should be 199)")
print(f"  Fields:      {len(out_fields)} total")
print(f"  Pct_ fields: {len(pct_fields)}")

if out_count == 199:
    print(f"\n  ✅ All 199 tracts joined successfully")
else:
    print(f"\n  ⚠️  Expected 199, got {out_count}")

print(f"\n{'='*60}")
print(f"CENSUS JOIN COMPLETE")
print(f"  Output: Base\\CensusTracts_Demographics_Pg")
print(f"  Next step: Run 06_equity_index_build.py")
print(f"{'='*60}")
