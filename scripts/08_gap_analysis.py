# =============================================================================
# 08_gap_analysis.py
# Baltimore City Transit Equity Analysis
# Stage 08 — Spatial Gap Analysis & Title VI Spatial Overlay
#
# Purpose:
#   1. Dissolves service area rings into a single coverage polygon
#   2. Erases coverage from city boundary to produce transit desert (gap) zones
#   3. Clips gap zones to land only (removes water bodies)
#   4. Identifies gap-affected census tracts (spatial join)
#   5. Runs FTA Title VI demographic overlay on gap zones
#
# Inputs:
#   - Analysis\ServiceArea_Rings_Clean_Pg_5min_10min
#   - Base\Baltimore_City_Land_Only
#   - Base\Baltimore_City_Boundary
#   - Base\CensusTracts_Demographics_Pg
#
# Outputs:
#   - Analysis\SA_Dissolved_Pg
#   - Analysis\Gap_Zones_Pg
#   - Analysis\Combined_Gap_Zones_Pg
#
# Key Results:
#   - 10.04 sq mi (12.4%) transit desert
#   - Hispanic residents: 1.54x overrepresentation in gap zones → TITLE VI FINDING
#
# Author : Nathaniel K.A. Stephens
# Date   : March 2026
# CRS    : EPSG 2248 (NAD 1983 StatePlane Maryland FIPS 1900, US Feet)
# =============================================================================

import arcpy
import os

# ── Environment setup ─────────────────────────────────────────────────────────
arcpy.env.overwriteOutput = True
arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(2248)

PROJECT_DIR  = r"C:\Users\kojoa\Documents\ArcGIS\Projects\MyProject"
GDB          = os.path.join(PROJECT_DIR, "MyProject.gdb")
ANALYSIS_DS  = os.path.join(GDB, "Analysis")
BASE_DS      = os.path.join(GDB, "Base")

# ── Input paths ───────────────────────────────────────────────────────────────
SERVICE_AREA_RINGS = os.path.join(ANALYSIS_DS, "ServiceArea_Rings_Clean_Pg_5min_10min")
CITY_LAND_ONLY     = os.path.join(BASE_DS,     "Baltimore_City_Land_Only")
CITY_BOUNDARY      = os.path.join(BASE_DS,     "Baltimore_City_Boundary")
CENSUS_TRACTS      = os.path.join(BASE_DS,     "CensusTracts_Demographics_Pg")

# ── Output paths ──────────────────────────────────────────────────────────────
SA_DISSOLVED       = os.path.join(ANALYSIS_DS, "SA_Dissolved_Pg")
GAP_ZONES          = os.path.join(ANALYSIS_DS, "Gap_Zones_Pg")
COMBINED_GAP_ZONES = os.path.join(ANALYSIS_DS, "Combined_Gap_Zones_Pg")

SCRATCH = arcpy.env.scratchGDB

print("=" * 65)
print("Stage 08 — Spatial Gap Analysis")
print("=" * 65)

# ── Step 1: Dissolve service area rings into single coverage polygon ──────────
print("\n[1/5] Dissolving service area rings...")
arcpy.management.Dissolve(
    in_features      = SERVICE_AREA_RINGS,
    out_feature_class= SA_DISSOLVED,
    dissolve_field   = None,
    statistics_fields= None,
    multi_part       = "MULTI_PART"
)
sa_area = sum(r[0] for r in arcpy.da.SearchCursor(SA_DISSOLVED, ["SHAPE@AREA"]))
sa_sqmi = sa_area / 27878400  # sq ft -> sq mi
print(f"   Service area dissolved: {sa_sqmi:.2f} sq mi")

# ── Step 2: Erase coverage from land-only boundary → gap zones ───────────────
print("\n[2/5] Erasing coverage to produce gap zones...")
gap_raw = os.path.join(SCRATCH, "gap_raw")
arcpy.analysis.Erase(
    in_features      = CITY_LAND_ONLY,
    erase_features   = SA_DISSOLVED,
    out_feature_class= gap_raw
)

# ── Step 3: Eliminate slivers (minimum area 43560 sq ft = 1 acre) ─────────────
print("\n[3/5] Eliminating slivers < 1 acre...")
arcpy.management.CopyFeatures(gap_raw, GAP_ZONES)
with arcpy.da.UpdateCursor(GAP_ZONES, ["SHAPE@AREA"]) as cur:
    removed = 0
    for row in cur:
        if row[0] < 43560:
            cur.deleteRow()
            removed += 1
print(f"   Removed {removed} sliver polygons")

# Calculate gap area
gap_area = sum(r[0] for r in arcpy.da.SearchCursor(GAP_ZONES, ["SHAPE@AREA"]))
gap_sqmi = gap_area / 27878400

# City total land area
city_area = sum(r[0] for r in arcpy.da.SearchCursor(CITY_LAND_ONLY, ["SHAPE@AREA"]))
city_sqmi = city_area / 27878400

pct_gap     = (gap_sqmi / city_sqmi) * 100
pct_covered = 100 - pct_gap
print(f"   City land area : {city_sqmi:.2f} sq mi")
print(f"   Gap area       : {gap_sqmi:.2f} sq mi ({pct_gap:.1f}%)")
print(f"   Coverage       : {city_sqmi - gap_sqmi:.2f} sq mi ({pct_covered:.1f}%)")

# Add area fields to Gap_Zones_Pg
arcpy.management.AddField(GAP_ZONES, "Area_SqMi", "DOUBLE")
arcpy.management.AddField(GAP_ZONES, "Area_Acres", "DOUBLE")
with arcpy.da.UpdateCursor(GAP_ZONES, ["SHAPE@AREA", "Area_SqMi", "Area_Acres"]) as cur:
    for row in cur:
        row[1] = row[0] / 27878400
        row[2] = row[0] / 43560
        cur.updateRow(row)

# ── Step 4: Spatial join gap zones to census tracts ───────────────────────────
print("\n[4/5] Joining gap zones to census tracts...")
gap_tracts_join = os.path.join(SCRATCH, "gap_tracts_join")
arcpy.analysis.SpatialJoin(
    target_features     = CENSUS_TRACTS,
    join_features       = GAP_ZONES,
    out_feature_class   = gap_tracts_join,
    join_operation      = "JOIN_ONE_TO_ONE",
    join_type           = "KEEP_ALL",
    match_option        = "INTERSECT",
    search_radius       = None,
    distance_field_name = ""
)

# Copy to Combined_Gap_Zones_Pg with gap flag
arcpy.management.CopyFeatures(gap_tracts_join, COMBINED_GAP_ZONES)
arcpy.management.AddField(COMBINED_GAP_ZONES, "In_Gap_Zone", "SHORT")
with arcpy.da.UpdateCursor(COMBINED_GAP_ZONES, ["Join_Count", "In_Gap_Zone"]) as cur:
    for row in cur:
        row[1] = 1 if (row[0] is not None and row[0] > 0) else 0
        cur.updateRow(row)

gap_tract_count = sum(1 for r in arcpy.da.SearchCursor(COMBINED_GAP_ZONES, ["In_Gap_Zone"]) if r[0] == 1)
print(f"   Gap-affected tracts: {gap_tract_count} of 199")

# ── Step 5: Title VI spatial demographic overlay ──────────────────────────────
print("\n[5/5] Running Title VI demographic overlay...")

# Fields needed: Pct_Hispanic, Pct_NonHispanicWhite, total population
demo_fields = ["In_Gap_Zone", "Pct_Hispanic", "Pct_NonHispanicWhite",
               "Total_Population", "Hispanic_Pop"]

total_pop       = 0
gap_total_pop   = 0
total_hisp      = 0
gap_hisp        = 0
total_nhwhite   = 0
gap_nhwhite     = 0

with arcpy.da.SearchCursor(COMBINED_GAP_ZONES, demo_fields) as cur:
    for in_gap, pct_hisp, pct_nhw, tot_pop, hisp_pop in cur:
        if tot_pop is None:
            continue
        total_pop     += tot_pop
        total_hisp    += (tot_pop * (pct_hisp or 0) / 100)
        total_nhwhite += (tot_pop * (pct_nhw or 0) / 100)
        if in_gap == 1:
            gap_total_pop += tot_pop
            gap_hisp      += (tot_pop * (pct_hisp or 0) / 100)
            gap_nhwhite   += (tot_pop * (pct_nhw or 0) / 100)

if total_pop > 0 and total_hisp > 0:
    city_hisp_pct  = (total_hisp / total_pop) * 100
    gap_hisp_pct   = (gap_hisp / gap_total_pop) * 100 if gap_total_pop > 0 else 0
    hisp_ratio     = gap_hisp_pct / city_hisp_pct if city_hisp_pct > 0 else 0

    city_nhw_pct   = (total_nhwhite / total_pop) * 100
    gap_nhw_pct    = (gap_nhwhite / gap_total_pop) * 100 if gap_total_pop > 0 else 0

    print(f"\n   Hispanic citywide : {city_hisp_pct:.1f}%")
    print(f"   Hispanic in gaps  : {gap_hisp_pct:.1f}%")
    print(f"   Disparity ratio   : {hisp_ratio:.2f}x")

    if hisp_ratio >= 1.25:
        print(f"   >>> TITLE VI FINDING: {hisp_ratio:.2f}x exceeds 1.25x threshold")
    else:
        print(f"   No Title VI finding ({hisp_ratio:.2f}x < 1.25x threshold)")

print("\n" + "=" * 65)
print("Stage 08 Complete")
print(f"  Gap zones    : {gap_sqmi:.2f} sq mi ({pct_gap:.1f}% of city land)")
print(f"  Coverage     : {pct_covered:.1f}%")
print(f"  Gap tracts   : {gap_tract_count}")
print(f"  Output       : Analysis\\Gap_Zones_Pg")
print(f"  Output       : Analysis\\Combined_Gap_Zones_Pg")
print(f"  Output       : Analysis\\SA_Dissolved_Pg")
print("=" * 65)
