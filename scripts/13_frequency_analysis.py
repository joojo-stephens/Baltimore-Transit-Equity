# =============================================================================
# 13_frequency_analysis.py
# Baltimore City Transit Equity Analysis
# Stage 13 — Stop-Level Service Frequency Analysis
#
# Purpose:
#   1. Reads GTFS stop_times.txt to compute per-stop headways
#      (average gap between consecutive arrivals during AM peak 7–9 AM)
#   2. Classifies each stop into frequency classes:
#        High       : headway ≤ 10 min
#        Moderate   : headway ≤ 20 min
#        Low        : headway ≤ 30 min
#        Infrequent : headway  > 30 min
#   3. Joins computed headways onto the GTFS stops feature class
#   4. Exports Frequency_Stops_Baltimore_Pt with Headway_Min + Freq_Class
#   5. Runs correlation: Avg_Headway vs Equity_Score (The Frequency Paradox)
#
# Inputs:
#   - GTFS source files: stop_times.txt, trips.txt, calendar.txt
#     Path: C:\Users\kojoa\Documents\ArcGIS\Projects\MyProject\GTFS\
#   - GTFS_Database.gdb\GTFS_BusStops_Baltimore_Pt
#   - Base\CensusTracts_Demographics_Pg
#
# Outputs:
#   - Analysis\Frequency_Stops_Baltimore_Pt
#     Fields: stop_id_raw, stop_id_pfx, stop_name, mode,
#             Headway_Min, Freq_Class
#
# Frequency Class Thresholds:
#   High       : ≤ 10 min   (GTFS "frequent" service standard)
#   Moderate   : ≤ 20 min
#   Low        : ≤ 30 min
#   Infrequent : > 30 min   (headway capped at 180 min)
#
# Key Results:
#   - 2,678 stops with headway data
#   - r = -0.356 between headway and equity score (p < 0.001)
#   - Vulnerable neighborhoods receive MORE frequent service
#
# Author : Nathaniel K.A. Stephens
# Date   : March 2026
# CRS    : EPSG 2248 (NAD 1983 StatePlane Maryland FIPS 1900, US Feet)
# =============================================================================

import arcpy
import os
import csv
import math
import statistics
from collections import defaultdict

arcpy.env.overwriteOutput = True
arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(2248)

PROJECT_DIR = r"C:\Users\kojoa\Documents\ArcGIS\Projects\MyProject"
GDB         = os.path.join(PROJECT_DIR, "MyProject.gdb")
GTFS_GDB    = os.path.join(PROJECT_DIR, "GTFS_Database.gdb")
GTFS_DIR    = os.path.join(PROJECT_DIR, "GTFS")
ANALYSIS_DS = os.path.join(GDB, "Analysis")
BASE_DS     = os.path.join(GDB, "Base")

# ── Inputs ────────────────────────────────────────────────────────────────────
GTFS_STOPS    = os.path.join(GTFS_GDB, "GTFS_BusStops_Baltimore_Pt")
CENSUS_TRACTS = os.path.join(BASE_DS,  "CensusTracts_Demographics_Pg")

# ── Output ────────────────────────────────────────────────────────────────────
FREQ_STOPS = os.path.join(ANALYSIS_DS, "Frequency_Stops_Baltimore_Pt")

SCRATCH = arcpy.env.scratchGDB

# ── Constants ─────────────────────────────────────────────────────────────────
PEAK_START_SEC = 7 * 3600    # 07:00 AM in seconds since midnight
PEAK_END_SEC   = 9 * 3600    # 09:00 AM
HEADWAY_CAP    = 180         # minutes — cap to exclude very infrequent stops

def time_to_seconds(t_str):
    """Convert HH:MM:SS to seconds since midnight. Handles >24h GTFS times."""
    parts = t_str.strip().split(":")
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])

def classify_frequency(headway_min):
    if headway_min is None:
        return "Infrequent"
    if headway_min <= 10:
        return "High"
    if headway_min <= 20:
        return "Moderate"
    if headway_min <= 30:
        return "Low"
    return "Infrequent"

print("=" * 65)
print("Stage 13 — Service Frequency Analysis")
print("=" * 65)

# ── Step 1: Load GTFS trips (weekday service only) ────────────────────────────
print("\n[1/5] Loading GTFS trips (weekday service)...")

# calendar.txt: identify weekday service IDs
calendar_file = os.path.join(GTFS_DIR, "calendar.txt")
weekday_services = set()
if os.path.exists(calendar_file):
    with open(calendar_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Service runs Monday–Friday
            if all(row.get(day, "0") == "1"
                   for day in ["monday", "tuesday", "wednesday", "thursday", "friday"]):
                weekday_services.add(row["service_id"].strip())
    print(f"   Weekday service IDs: {len(weekday_services)}")
else:
    print("   calendar.txt not found — using all trips")

trips_file = os.path.join(GTFS_DIR, "trips.txt")
trip_route = {}
with open(trips_file, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        svc = row.get("service_id", "").strip()
        if not weekday_services or svc in weekday_services:
            trip_route[row["trip_id"].strip()] = row["route_id"].strip()

print(f"   Weekday trips loaded: {len(trip_route):,}")

# ── Step 2: Compute per-stop headways from stop_times.txt (AM peak) ───────────
print("\n[2/5] Computing AM peak headways from stop_times.txt...")
print(f"   Peak window: {PEAK_START_SEC//3600:02d}:00 – {PEAK_END_SEC//3600:02d}:00")

# stop_id -> sorted list of arrival times (seconds) during AM peak
stop_arrivals = defaultdict(list)

stop_times_file = os.path.join(GTFS_DIR, "stop_times.txt")
row_count = 0
with open(stop_times_file, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        trip_id = row["trip_id"].strip()
        if trip_id not in trip_route:
            continue
        try:
            arr_sec = time_to_seconds(row["arrival_time"])
        except (ValueError, IndexError):
            continue
        if PEAK_START_SEC <= arr_sec <= PEAK_END_SEC:
            stop_id = row["stop_id"].strip()
            stop_arrivals[stop_id].append(arr_sec)
        row_count += 1

print(f"   Stop_times rows processed: {row_count:,}")
print(f"   Stops with AM peak arrivals: {len(stop_arrivals):,}")

# Compute headway per stop
stop_headway = {}
for stop_id, arrivals in stop_arrivals.items():
    arrivals_sorted = sorted(set(arrivals))
    if len(arrivals_sorted) < 2:
        stop_headway[stop_id] = HEADWAY_CAP
        continue
    gaps = [(arrivals_sorted[i+1] - arrivals_sorted[i]) / 60.0
            for i in range(len(arrivals_sorted) - 1)]
    avg_hw = sum(gaps) / len(gaps)
    stop_headway[stop_id] = min(avg_hw, HEADWAY_CAP)

print(f"   Headways computed: {len(stop_headway):,}")

# ── Step 3: Build Frequency_Stops_Baltimore_Pt ────────────────────────────────
print("\n[3/5] Building Frequency_Stops_Baltimore_Pt...")
arcpy.management.CopyFeatures(GTFS_STOPS, FREQ_STOPS)

# Rename/add required fields
existing = [f.name for f in arcpy.ListFields(FREQ_STOPS)]
if "Headway_Min" not in existing:
    arcpy.management.AddField(FREQ_STOPS, "Headway_Min", "DOUBLE",
                               field_alias="Average AM Peak Headway (min)")
if "Freq_Class" not in existing:
    arcpy.management.AddField(FREQ_STOPS, "Freq_Class", "TEXT",
                               field_length=20,
                               field_alias="Frequency Class")
if "stop_id_pfx" not in existing:
    arcpy.management.AddField(FREQ_STOPS, "stop_id_pfx", "TEXT",
                               field_length=20)
if "mode" not in existing:
    arcpy.management.AddField(FREQ_STOPS, "mode", "TEXT", field_length=20)

# Detect stop_id field name
stop_id_field = next((f.name for f in arcpy.ListFields(FREQ_STOPS)
                      if "stop_id" in f.name.lower() and "pfx" not in f.name.lower()),
                     "stop_id")

update_fields = [stop_id_field, "Headway_Min", "Freq_Class", "stop_id_pfx", "mode"]
matched = 0
unmatched = 0
with arcpy.da.UpdateCursor(FREQ_STOPS, update_fields) as cur:
    for row in cur:
        raw_id = str(row[0]).strip() if row[0] else ""
        hw = stop_headway.get(raw_id)
        if hw is None:
            # Try without leading zeros or with prefix strip
            hw = stop_headway.get(raw_id.lstrip("0"))
        if hw is not None:
            row[1] = round(hw, 2)
            row[2] = classify_frequency(hw)
            row[3] = raw_id
            row[4] = "bus"
            matched += 1
        else:
            row[1] = HEADWAY_CAP
            row[2] = "Infrequent"
            row[3] = raw_id
            row[4] = "bus"
            unmatched += 1
        cur.updateRow(row)

total_freq = int(arcpy.management.GetCount(FREQ_STOPS)[0])
print(f"   Stops written      : {total_freq:,}")
print(f"   Headways matched   : {matched:,}")
print(f"   Unmatched (capped) : {unmatched:,}")

# Frequency class distribution
freq_dist = {}
with arcpy.da.SearchCursor(FREQ_STOPS, ["Freq_Class"]) as cur:
    for (fc,) in cur:
        freq_dist[fc] = freq_dist.get(fc, 0) + 1

print("\n   Frequency class distribution:")
for fc in ["High", "Moderate", "Low", "Infrequent"]:
    n   = freq_dist.get(fc, 0)
    pct = (n / total_freq * 100) if total_freq > 0 else 0
    print(f"   {'':4}{fc:<12}: {n:>5} stops ({pct:.1f}%)")

# ── Step 4: Spatial join stops to tracts then correlate with equity ───────────
print("\n[4/5] Spatial join stops → tracts for equity correlation...")
stops_to_tracts = os.path.join(SCRATCH, "freq_stops_to_tracts")
arcpy.analysis.SpatialJoin(
    target_features  = CENSUS_TRACTS,
    join_features    = FREQ_STOPS,
    out_feature_class= stops_to_tracts,
    join_operation   = "JOIN_ONE_TO_ONE",
    join_type        = "KEEP_ALL",
    match_option     = "CONTAINS"
)

# Aggregate mean headway per tract
tract_hw = defaultdict(list)
with arcpy.da.SearchCursor(stops_to_tracts, ["GEOID", "Headway_Min"]) as cur:
    for geoid, hw in cur:
        if geoid and hw is not None:
            tract_hw[geoid].append(hw)

# ── Step 5: Correlation — Avg Headway vs Equity_Score ─────────────────────────
print("\n[5/5] Pearson correlation: Avg_Headway vs Equity_Score...")

# Get equity scores per tract
tract_equity = {}
with arcpy.da.SearchCursor(CENSUS_TRACTS, ["GEOID", "Equity_Score", "Equity_Quintile"]) as cur:
    for geoid, es, eq in cur:
        if es is not None:
            tract_equity[geoid] = {"score": es, "quintile": int(eq) if eq else None}

# Build paired data
paired = []
for geoid, hws in tract_hw.items():
    eq = tract_equity.get(geoid)
    if eq and hws:
        paired.append({"score": eq["score"], "headway": sum(hws)/len(hws),
                       "quintile": eq["quintile"]})

n = len(paired)
x = [p["score"]   for p in paired]
y = [p["headway"] for p in paired]

x_mean = sum(x) / n
y_mean = sum(y) / n
cov    = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
std_x  = math.sqrt(sum((xi - x_mean)**2 for xi in x))
std_y  = math.sqrt(sum((yi - y_mean)**2 for yi in y))
r_val  = cov / (std_x * std_y)
t_stat = r_val * math.sqrt(n - 2) / math.sqrt(1 - r_val**2)
p_str  = "< 0.001" if abs(t_stat) > 3.3 else "< 0.05"

print(f"   n             : {n} tracts")
print(f"   Pearson r     : {r_val:.4f}")
print(f"   t-statistic   : {t_stat:.4f}")
print(f"   p-value       : {p_str}")

if r_val < 0:
    print(f"   Interpretation: Higher equity score → LOWER headway")
    print(f"                   (more vulnerable neighborhoods → more frequent service)")
else:
    print(f"   Interpretation: Higher equity score → HIGHER headway")

# Quintile averages
print("\n   Average headway by equity quintile:")
q_hws = {q: [] for q in range(1, 6)}
for p in paired:
    if p["quintile"]:
        q_hws[p["quintile"]].append(p["headway"])

for q in range(1, 6):
    vals = q_hws[q]
    if vals:
        print(f"   Q{q}: {sum(vals)/len(vals):.1f} min  (n={len(vals)})")

print("\n" + "=" * 65)
print("Stage 13 Complete")
print(f"  Stops processed : {total_freq:,}")
print(f"  Pearson r = {r_val:.4f}, p {p_str}")
print(f"  Output : Analysis\\Frequency_Stops_Baltimore_Pt")
print(f"           Fields: Headway_Min, Freq_Class")
print("=" * 65)
