# ============================================================
# 06_equity_index_build.py
# Baltimore Transit Equity Analysis
# Build 19-Indicator Composite Equity Need Index
#
# Author:  Nathaniel K.A. Stephens
# Date:    March 2026
#
# Method:  Min-max normalize each indicator to 0-1
#          Invert Med_HH_Income (lower = more need)
#          Apply weights (sum = 100%)
#          Scale to 0-100
#          Assign quintiles via 20/40/60/80th percentile breaks
#
# Inputs:  CensusTracts_Demographics_Pg (with all Pct_ fields)
# Outputs: Three new fields on CensusTracts_Demographics_Pg:
#          Equity_Score    (0-100 continuous)
#          Equity_Quintile (1-5 integer)
#          Equity_Level    (Very Low/Low/Moderate/High/Very High)
# ============================================================

import arcpy
import numpy as np

# ── PATHS ────────────────────────────────────────────────────
gdb   = r"C:\Users\kojoa\Documents\ArcGIS\Projects\MyProject\MyProject.gdb"
layer = f"{gdb}\\Base\\CensusTracts_Demographics_Pg"

arcpy.env.overwriteOutput = True

print("=" * 60)
print("COMPOSITE EQUITY NEED INDEX — 19 INDICATORS")
print("=" * 60)

# ── 19 INDICATORS WITH WEIGHTS ──────────────────────────────
# Weights must sum to exactly 1.0 (100%)
indicators = {
    "Pct_Minority"        : 0.12,   # Title VI core requirement
    "Pct_Poverty"         : 0.09,   # Economic vulnerability
    "Med_HH_Income"       : 0.07,   # Income (INVERTED — lower = more need)
    "Pct_ZeroVehicle"     : 0.06,   # Transit dependency
    "Pct_ZeroVeh_Combined": 0.06,   # Owner + renter zero vehicle
    "Pct_Disability"      : 0.05,   # ADA vulnerability
    "Pct_Elderly"         : 0.05,   # Age vulnerability (65+)
    "Pct_LimitedEnglish"  : 0.05,   # Language barrier
    "Pct_TransitCommute"  : 0.05,   # Actual transit users
    "Pct_NotCitizen"      : 0.04,   # Legal vulnerability
    "Pct_Youth"           : 0.04,   # Youth dependency (<18)
    "Pct_Under18Poverty"  : 0.04,   # Child poverty
    "Pct_Over65Poverty"   : 0.03,   # Elderly poverty
    "Pct_Renters"         : 0.03,   # Housing instability
    "Avg_Travel_Time"     : 0.05,   # Long commutes = system failure
    "Pct_BusDependent"    : 0.05,   # Bus-specific dependency
    "Pct_Elderly75Dis"    : 0.04,   # Disabled 75+ most vulnerable
    "Pct_FemaleTravelTime": 0.04,   # Female commute time
    "Pct_MaleTravelTime"  : 0.04,   # Male commute time
}

# ── VERIFY WEIGHTS SUM TO 100% ───────────────────────────────
total_weight = sum(indicators.values())
print(f"\nTotal weight: {total_weight*100:.0f}%")
assert abs(total_weight - 1.0) < 0.001, \
    f"Weights must sum to 100% — currently {total_weight*100:.1f}%"
print(f"✅ Weights verified")

# ── STEP 1 — READ ALL INDICATOR VALUES ───────────────────────
print(f"\nStep 1 — Reading indicator values from {len(indicators)} fields...")

fields   = ["OBJECTID"] + list(indicators.keys())
data     = {field: [] for field in indicators.keys()}
oid_list = []
tractce  = []

with arcpy.da.SearchCursor(layer, fields + ["TRACTCE"]) as cursor:
    for row in cursor:
        oid_list.append(row[0])
        tractce.append(row[-1])
        for i, field in enumerate(indicators.keys()):
            val = row[i + 1]
            data[field].append(float(val) if val is not None else 0.0)

print(f"  ✅ {len(oid_list)} tracts read")
print(f"  ✅ {len(indicators)} indicators loaded")

# ── STEP 2 — NORMALIZE TO 0-1 ────────────────────────────────
print(f"\nStep 2 — Normalizing all indicators to 0-1...")
print("-" * 52)

normalized = {}
for field, values in data.items():
    arr     = np.array(values, dtype=float)
    arr     = np.nan_to_num(arr, nan=0.0)
    min_val = arr.min()
    max_val = arr.max()

    if max_val > min_val:
        norm = (arr - min_val) / (max_val - min_val)
    else:
        norm = np.zeros_like(arr)

    # Invert income — lower income = higher need score
    if field == "Med_HH_Income":
        norm = 1 - norm
        tag  = "INVERTED"
        print(f"  🔄 {field:25} min={min_val:8.0f}  max={max_val:8.0f}  {tag}")
    else:
        print(f"  ✅ {field:25} min={min_val:6.1f}  max={max_val:6.1f}")

    normalized[field] = norm

# ── STEP 3 — CALCULATE WEIGHTED INDEX ────────────────────────
print(f"\nStep 3 — Calculating weighted index scores...")

index_scores = np.zeros(len(oid_list))
for field, weight in indicators.items():
    index_scores += normalized[field] * weight

# Scale to 0-100
index_scores = (index_scores * 100).round(1)

print(f"  ✅ Scores calculated")
print(f"  Min:    {index_scores.min():.1f}")
print(f"  Max:    {index_scores.max():.1f}")
print(f"  Mean:   {index_scores.mean():.1f}")
print(f"  Median: {np.median(index_scores):.1f}")

# ── STEP 4 — ASSIGN QUINTILES ────────────────────────────────
print(f"\nStep 4 — Assigning equity need quintiles...")

quintile_labels = {
    1: "Very Low",
    2: "Low",
    3: "Moderate",
    4: "High",
    5: "Very High"
}

# Percentile-based breaks — federal standard for equity analysis
breakpoints = np.percentile(index_scores, [20, 40, 60, 80])
print(f"  Breakpoints (20/40/60/80th percentile):")
print(f"  {breakpoints[0]:.1f} / {breakpoints[1]:.1f} / "
      f"{breakpoints[2]:.1f} / {breakpoints[3]:.1f}")
print(f"  Use these exact values for ArcGIS manual interval symbology")

quintiles = np.ones(len(index_scores), dtype=int)
quintiles[index_scores > breakpoints[0]] = 2
quintiles[index_scores > breakpoints[1]] = 3
quintiles[index_scores > breakpoints[2]] = 4
quintiles[index_scores > breakpoints[3]] = 5

score_by_oid    = dict(zip(oid_list, index_scores))
quintile_by_oid = dict(zip(oid_list, quintiles))
label_by_oid    = {oid: quintile_labels[q]
                   for oid, q in zip(oid_list, quintiles)}

# ── STEP 5 — ADD OUTPUT FIELDS ───────────────────────────────
print(f"\nStep 5 — Adding output fields to layer...")

new_fields = [
    ("Equity_Score",    "DOUBLE", "Composite Equity Need Score 0-100"),
    ("Equity_Quintile", "SHORT",  "Equity Need Quintile 1-5"),
    ("Equity_Level",    "TEXT",   "Equity Need Level"),
]

for fname, ftype, falias in new_fields:
    try:
        arcpy.management.AddField(
            layer, fname, ftype,
            field_alias  = falias,
            field_length = 20 if ftype == "TEXT" else None
        )
        print(f"  ✅ {fname} added")
    except Exception as e:
        print(f"  ⚠️  {fname} may already exist: {e}")

# ── STEP 6 — WRITE SCORES TO LAYER ───────────────────────────
print(f"\nStep 6 — Writing scores to all tracts...")

write_fields = ["OBJECTID", "Equity_Score",
                "Equity_Quintile", "Equity_Level"]

updated = 0
with arcpy.da.UpdateCursor(layer, write_fields) as cursor:
    for row in cursor:
        oid = row[0]
        if oid in score_by_oid:
            row[1] = float(score_by_oid[oid])
            row[2] = int(quintile_by_oid[oid])
            row[3] = label_by_oid[oid]
            cursor.updateRow(row)
            updated += 1

print(f"  ✅ {updated} tracts updated")

# ── STEP 7 — SUMMARY REPORT ──────────────────────────────────
print(f"\n{'='*60}")
print("EQUITY INDEX SUMMARY")
print(f"{'='*60}")
print(f"\n  {'Q':3} {'Level':12} {'Tracts':7} "
      f"{'Min':7} {'Max':7} {'Avg':7}")
print("  " + "-" * 50)

for q in range(1, 6):
    label = quintile_labels[q]
    mask  = quintiles == q
    n     = mask.sum()
    lo    = index_scores[mask].min()
    hi    = index_scores[mask].max()
    avg   = index_scores[mask].mean()
    print(f"  Q{q}  {label:12} {n:7} "
          f"{lo:7.1f} {hi:7.1f} {avg:7.1f}")

print(f"\n  TOP 10 HIGHEST NEED TRACTS:")
print("  " + "-" * 40)
sorted_idx = np.argsort(index_scores)[::-1]
for i in range(10):
    idx = sorted_idx[i]
    print(f"  {i+1:2}. Tract {tractce[idx]:8}  "
          f"Score: {index_scores[idx]:5.1f}  "
          f"{quintile_labels[quintiles[idx]]}")

print(f"\n  ArcGIS Symbology Settings:")
print(f"  Layer:  CensusTracts_Demographics_Pg")
print(f"  Field:  Equity_Score")
print(f"  Method: Manual Interval")
print(f"  Breaks: {breakpoints[0]:.1f} / {breakpoints[1]:.1f} / "
      f"{breakpoints[2]:.1f} / {breakpoints[3]:.1f}")
print(f"  Colors: Yellow → Dark Red (5 classes)")

print(f"\n{'='*60}")
print(f"EQUITY INDEX COMPLETE — 19 Indicators")
print(f"  Fields added to CensusTracts_Demographics_Pg:")
print(f"  → Equity_Score    (0-100 continuous)")
print(f"  → Equity_Quintile (1=Very Low to 5=Very High)")
print(f"  → Equity_Level    (readable text label)")
print(f"  Next step: Run 07_new_fields_calculation.py")
print(f"{'='*60}")
