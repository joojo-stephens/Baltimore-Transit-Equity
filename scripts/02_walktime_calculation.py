# ============================================================
# 02_walktime_calculation.py
# Baltimore Transit Equity Analysis
# Calculate WalkTime field on road network for service area
#
# Author:  Nathaniel K.A. Stephens
# Date:    March 2026
#
# Inputs:  Roads_Baltimore_Ln_Project
# Outputs: WalkTime field added to Roads_Baltimore_Ln_Project
#
# Formula: WalkTime = Shape_Length / 264
#          264 feet per minute = 3 mph walking speed
#          Result = walking time in minutes per segment
# ============================================================

import arcpy

# ── PATHS ────────────────────────────────────────────────────
gdb   = r"C:\Users\kojoa\Documents\ArcGIS\Projects\MyProject\MyProject.gdb"
roads = f"{gdb}\\OSM_Network\\Roads_Baltimore_Ln_Project"

arcpy.env.overwriteOutput = True

print("=" * 60)
print("WALKTIME FIELD CALCULATION")
print("=" * 60)

# ── VERIFY LAYER EXISTS ──────────────────────────────────────
if not arcpy.Exists(roads):
    print(f"❌ Roads layer not found at:")
    print(f"   {roads}")
    print(f"   Verify path and re-run")
    exit()

count = int(arcpy.management.GetCount(roads)[0])
desc  = arcpy.Describe(roads)
print(f"\n  Layer:       Roads_Baltimore_Ln_Project")
print(f"  Features:    {count:,} road segments")
print(f"  SR:          {desc.spatialReference.name}")
print(f"  Units:       {desc.spatialReference.linearUnitName}")

# ── CHECK FOR EXISTING WALKTIME FIELD ───────────────────────
fields = [f.name for f in arcpy.ListFields(roads)]
if "WalkTime" in fields:
    print(f"\n  ⚠️  WalkTime field already exists — will recalculate")
else:
    print(f"\n  Adding WalkTime field...")
    arcpy.management.AddField(roads, "WalkTime", "DOUBLE",
                               field_alias="Walking Time (Minutes)")
    print(f"  ✅ WalkTime field added")

# ── CALCULATE WALKTIME ───────────────────────────────────────
print(f"\n  Calculating WalkTime = Shape_Length / 264...")
print(f"  (264 feet/min = 3 mph walking speed)")

arcpy.management.CalculateField(
    in_table        = roads,
    field           = "WalkTime",
    expression      = "!Shape_Length! / 264",
    expression_type = "PYTHON3"
)
print(f"  ✅ WalkTime calculated for all {count:,} segments")

# ── VERIFY RESULTS ───────────────────────────────────────────
print(f"\n  Verifying results (first 10 segments):")
print(f"  {'OID':6} {'Shape_Length':14} {'WalkTime':10}")
print("  " + "-" * 35)

with arcpy.da.SearchCursor(
    roads, ["OID@", "Shape_Length", "WalkTime"]
) as cursor:
    for i, row in enumerate(cursor):
        if i >= 10:
            break
        print(f"  {row[0]:6} {row[1]:14.1f} {row[2]:10.3f} min")

# ── SUMMARY STATISTICS ───────────────────────────────────────
times = [row[0] for row in arcpy.da.SearchCursor(roads, ["WalkTime"])
         if row[0] is not None]

import statistics
print(f"\n  WalkTime Statistics:")
print(f"  Min:    {min(times):.3f} min")
print(f"  Max:    {max(times):.3f} min")
print(f"  Mean:   {statistics.mean(times):.3f} min")
print(f"  Median: {statistics.median(times):.3f} min")

print(f"\n{'='*60}")
print(f"WALKTIME CALCULATION COMPLETE")
print(f"  Field: WalkTime (Double)")
print(f"  Use as Impedance in Network Dataset travel mode")
print(f"{'='*60}")
