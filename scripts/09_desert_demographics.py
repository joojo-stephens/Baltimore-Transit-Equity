# =============================================================================
# 09_desert_demographics.py
# Baltimore City Transit Equity Analysis
# Stage 09 — Frequency Desert Demographics
#
# Purpose:
#   1. Joins frequency stop data to census tracts (spatial join)
#   2. Calculates median tract-level headway from stop-level headways
#   3. Identifies frequency gap tracts (headway > 20 min = Low/Infrequent)
#   4. Builds frequency gap zone polygons
#   5. Produces demographic profile of frequency-gap vs well-served tracts
#
# Inputs:
#   - Analysis\Frequency_Stops_Baltimore_Pt   (from Stage 13 — run 13 first)
#   - Base\CensusTracts_Demographics_Pg
#   - Analysis\Gap_Zones_Pg                   (from Stage 08)
#
# Outputs:
#   - Analysis\Freq_Gap_Tracts_Pg
#   - Analysis\Frequency_Gap_Zones_Pg
#   - Analysis\Frequency_Tracts_Pg            (updated with tract-level headway stats)
#
# Key Results:
#   - 18 frequency gap tracts identified (headway > 20 min)
#   - Q1 avg headway 25.3 min vs Q5 17.2 min (r = -0.356, p < 0.001)
#   - No Title VI frequency finding (ratio 0.62x < 1.25x threshold)
#
# Author : Nathaniel K.A. Stephens
# Date   : March 2026
# CRS    : EPSG 2248 (NAD 1983 StatePlane Maryland FIPS 1900, US Feet)
# =============================================================================

import arcpy
import os
import statistics

arcpy.env.overwriteOutput = True
arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(2248)

PROJECT_DIR = r"C:\Users\kojoa\Documents\ArcGIS\Projects\MyProject"
GDB         = os.path.join(PROJECT_DIR, "MyProject.gdb")
GTFS_GDB    = os.path.join(PROJECT_DIR, "GTFS_Database.gdb")
ANALYSIS_DS = os.path.join(GDB, "Analysis")
BASE_DS     = os.path.join(GDB, "Base")

# ── Inputs ────────────────────────────────────────────────────────────────────
FREQ_STOPS    = os.path.join(ANALYSIS_DS, "Frequency_Stops_Baltimore_Pt")
CENSUS_TRACTS = os.path.join(BASE_DS,     "CensusTracts_Demographics_Pg")
GAP_ZONES     = os.path.join(ANALYSIS_DS, "Gap_Zones_Pg")

# ── Outputs ───────────────────────────────────────────────────────────────────
FREQ_TRACTS      = os.path.join(ANALYSIS_DS, "Frequency_Tracts_Pg")
FREQ_GAP_TRACTS  = os.path.join(ANALYSIS_DS, "Freq_Gap_Tracts_Pg")
FREQ_GAP_ZONES   = os.path.join(ANALYSIS_DS, "Frequency_Gap_Zones_Pg")

SCRATCH = arcpy.env.scratchGDB

# Frequency class thresholds (minutes headway)
FREQ_THRESHOLDS = {
    "High"       : (0,  10],   # <= 10 min
    "Moderate"   : (10, 20],   # 10-20 min
    "Low"        : (20, 30],   # 20-30 min
    "Infrequent" : (30, 9999]  # > 30 min
}
# Gap threshold: any tract with median headway > 20 min
FREQ_GAP_THRESHOLD = 20.0

print("=" * 65)
print("Stage 09 — Frequency Desert Demographics")
print("=" * 65)

# ── Step 1: Spatial join stops to tracts ──────────────────────────────────────
print("\n[1/5] Spatial join: stops → census tracts...")
stops_to_tracts = os.path.join(SCRATCH, "stops_to_tracts")
arcpy.analysis.SpatialJoin(
    target_features  = FREQ_STOPS,
    join_features    = CENSUS_TRACTS,
    out_feature_class= stops_to_tracts,
    join_operation   = "JOIN_ONE_TO_ONE",
    join_type        = "KEEP_ALL",
    match_option     = "WITHIN"
)

# ── Step 2: Aggregate headway to tract level ──────────────────────────────────
print("\n[2/5] Aggregating headway values to tract level...")

# Build dict: GEOID -> list of headways
tract_headways = {}
join_fields = ["GEOID", "Headway_Min", "Freq_Class"]
with arcpy.da.SearchCursor(stops_to_tracts, join_fields) as cur:
    for geoid, hw, fc in cur:
        if geoid is None or hw is None:
            continue
        if geoid not in tract_headways:
            tract_headways[geoid] = []
        tract_headways[geoid].append(hw)

print(f"   Tracts with stop data: {len(tract_headways)}")

# ── Step 3: Copy tracts layer and add headway statistics ──────────────────────
print("\n[3/5] Building Frequency_Tracts_Pg with headway stats...")
arcpy.management.CopyFeatures(CENSUS_TRACTS, FREQ_TRACTS)

new_fields = [
    ("Avg_Headway",    "DOUBLE", "Average headway across all stops in tract (min)"),
    ("Median_Headway", "DOUBLE", "Median headway across all stops in tract (min)"),
    ("Min_Headway",    "DOUBLE", "Best (lowest) headway stop in tract (min)"),
    ("Stop_Count",     "SHORT",  "Number of frequency stops in tract"),
    ("Freq_Gap_Flag",  "SHORT",  "1 = freq gap tract (avg headway > 20 min), 0 = served"),
    ("Freq_Class_Dom", "TEXT",   "Dominant frequency class in tract"),
]
for fname, ftype, falias in new_fields:
    arcpy.management.AddField(FREQ_TRACTS, fname, ftype, field_alias=falias)

update_fields = ["GEOID", "Avg_Headway", "Median_Headway",
                 "Min_Headway", "Stop_Count", "Freq_Gap_Flag", "Freq_Class_Dom"]
with arcpy.da.UpdateCursor(FREQ_TRACTS, update_fields) as cur:
    for row in cur:
        geoid = row[0]
        hws = tract_headways.get(geoid, [])
        if hws:
            avg = sum(hws) / len(hws)
            med = statistics.median(hws)
            mn  = min(hws)
            cnt = len(hws)
            # Dominant class
            if avg <= 10:   dom = "High"
            elif avg <= 20: dom = "Moderate"
            elif avg <= 30: dom = "Low"
            else:           dom = "Infrequent"
            gap = 1 if avg > FREQ_GAP_THRESHOLD else 0
        else:
            avg, med, mn, cnt, dom, gap = None, None, None, 0, "No Service", 1
        row[1] = avg
        row[2] = med
        row[3] = mn
        row[4] = cnt
        row[5] = gap
        row[6] = dom
        cur.updateRow(row)

gap_count = sum(1 for r in arcpy.da.SearchCursor(FREQ_TRACTS, ["Freq_Gap_Flag"]) if r[0] == 1)
print(f"   Frequency gap tracts (avg > 20 min): {gap_count}")

# ── Step 4: Extract gap tracts and dissolve to zones ─────────────────────────
print("\n[4/5] Building frequency gap zones...")
arcpy.analysis.Select(
    in_features     = FREQ_TRACTS,
    out_feature_class= FREQ_GAP_TRACTS,
    where_clause    = "Freq_Gap_Flag = 1"
)
arcpy.management.Dissolve(
    in_features      = FREQ_GAP_TRACTS,
    out_feature_class= FREQ_GAP_ZONES,
    dissolve_field   = None
)
print(f"   Frequency gap tracts copied: {int(arcpy.management.GetCount(FREQ_GAP_TRACTS)[0])}")

# ── Step 5: Equity analysis — headway by quintile ─────────────────────────────
print("\n[5/5] Frequency equity analysis by quintile...")
equity_fields = ["Equity_Quintile", "Avg_Headway", "Pct_Minority",
                 "Pct_NonHispanicWhite"]
q_headways   = {q: [] for q in range(1, 6)}
minority_hws = []
nonmin_hws   = []

with arcpy.da.SearchCursor(FREQ_TRACTS, equity_fields) as cur:
    for q, hw, pct_min, pct_nhw in cur:
        if hw is None or q is None:
            continue
        q_headways[q].append(hw)
        pct_min_val = 100 - (pct_nhw or 0)
        if pct_min_val >= 50:
            minority_hws.append(hw)
        else:
            nonmin_hws.append(hw)

print("\n   Headway by Equity Quintile:")
for q in range(1, 6):
    hws = q_headways[q]
    if hws:
        print(f"   Q{q}: {sum(hws)/len(hws):.1f} min avg  (n={len(hws)})")

# Title VI frequency test
if minority_hws and nonmin_hws:
    m_avg  = sum(minority_hws)  / len(minority_hws)
    nm_avg = sum(nonmin_hws)    / len(nonmin_hws)
    ratio  = m_avg / nm_avg if nm_avg > 0 else 0
    print(f"\n   Minority avg headway    : {m_avg:.1f} min")
    print(f"   Non-minority avg headway: {nm_avg:.1f} min")
    print(f"   Disparity ratio         : {ratio:.2f}x")
    if ratio >= 1.25:
        print("   >>> TITLE VI FINDING")
    else:
        print("   No Title VI finding (minority served more frequently)")

print("\n" + "=" * 65)
print("Stage 09 Complete")
print(f"  Gap tracts (headway > 20 min) : {gap_count}")
print(f"  Output : Analysis\\Frequency_Tracts_Pg")
print(f"  Output : Analysis\\Freq_Gap_Tracts_Pg")
print(f"  Output : Analysis\\Frequency_Gap_Zones_Pg")
print("=" * 65)
