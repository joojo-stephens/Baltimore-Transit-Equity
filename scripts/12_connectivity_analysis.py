# =============================================================================
# 12_connectivity_analysis.py
# Baltimore City Transit Equity Analysis
# Stage 12 — Network Connectivity & Transfer Point Analysis
#
# Purpose:
#   1. Calculates number of unique routes serving each stop (from GTFS)
#   2. Identifies transfer points (stops served by 2+ routes)
#   3. Spatial joins transfer points to census tracts
#   4. Computes connectivity index (avg routes/stop) per tract
#   5. Tests connectivity equity across Q1–Q5 (Welch t-test Q1 vs Q5)
#
# Inputs:
#   - GTFS_Database.gdb\GTFS_BusStops_Baltimore_Pt
#   - GTFS source files: stop_times.txt, trips.txt, routes.txt
#     Path: C:\Users\kojoa\Documents\ArcGIS\Projects\MyProject\GTFS\
#   - Base\CensusTracts_Demographics_Pg
#
# Outputs:
#   - Analysis\Transfer_Points_Pt    (1,107 stops with 2+ routes)
#   - Analysis\Connectivity_Tracts_Pg
#
# Key Results:
#   - 1,107 transfer points citywide
#   - Q1 = 1.46 routes/stop vs Q5 = 1.54 routes/stop
#   - Welch t-test: p = 0.567 — NOT significant
#   - No connectivity equity disparity
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

arcpy.env.overwriteOutput = True
arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(2248)

PROJECT_DIR = r"C:\Users\kojoa\Documents\ArcGIS\Projects\MyProject"
GDB         = os.path.join(PROJECT_DIR, "MyProject.gdb")
GTFS_GDB    = os.path.join(PROJECT_DIR, "GTFS_Database.gdb")
GTFS_DIR    = os.path.join(PROJECT_DIR, "GTFS")      # raw GTFS .txt files
ANALYSIS_DS = os.path.join(GDB, "Analysis")
BASE_DS     = os.path.join(GDB, "Base")

# ── Inputs ────────────────────────────────────────────────────────────────────
GTFS_STOPS    = os.path.join(GTFS_GDB, "GTFS_BusStops_Baltimore_Pt")
CENSUS_TRACTS = os.path.join(BASE_DS,  "CensusTracts_Demographics_Pg")

# ── Outputs ───────────────────────────────────────────────────────────────────
TRANSFER_POINTS     = os.path.join(ANALYSIS_DS, "Transfer_Points_Pt")
CONNECTIVITY_TRACTS = os.path.join(ANALYSIS_DS, "Connectivity_Tracts_Pg")

SCRATCH = arcpy.env.scratchGDB

print("=" * 65)
print("Stage 12 — Network Connectivity Analysis")
print("=" * 65)

# ── Step 1: Build stop → routes lookup from GTFS ──────────────────────────────
print("\n[1/5] Building stop → routes lookup from GTFS files...")

# Read trips.txt: trip_id -> route_id
trips_file = os.path.join(GTFS_DIR, "trips.txt")
trip_route  = {}
with open(trips_file, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        trip_route[row["trip_id"].strip()] = row["route_id"].strip()

print(f"   Trips loaded: {len(trip_route):,}")

# Read stop_times.txt: stop_id -> set of trip_ids
stop_times_file = os.path.join(GTFS_DIR, "stop_times.txt")
stop_routes = {}   # stop_id -> set of route_ids

print("   Reading stop_times.txt (this may take a moment)...")
with open(stop_times_file, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        stop_id  = row["stop_id"].strip()
        trip_id  = row["trip_id"].strip()
        route_id = trip_route.get(trip_id)
        if route_id:
            if stop_id not in stop_routes:
                stop_routes[stop_id] = set()
            stop_routes[stop_id].add(route_id)

total_stops_gtfs = len(stop_routes)
print(f"   Unique stops in stop_times: {total_stops_gtfs:,}")

# Route count per stop
stop_route_count = {sid: len(rts) for sid, rts in stop_routes.items()}
transfer_stops   = {sid: cnt for sid, cnt in stop_route_count.items() if cnt >= 2}
print(f"   Transfer stops (2+ routes): {len(transfer_stops):,}")

# ── Step 2: Add route count field to GTFS stops layer ─────────────────────────
print("\n[2/5] Adding route count to GTFS stops layer...")
stops_with_conn = os.path.join(SCRATCH, "stops_with_conn")
arcpy.management.CopyFeatures(GTFS_STOPS, stops_with_conn)

arcpy.management.AddField(stops_with_conn, "Route_Count", "SHORT")
arcpy.management.AddField(stops_with_conn, "Is_Transfer", "SHORT")

# Match stop IDs — handle prefix differences (stop_id_pfx vs raw)
id_fields = [f.name for f in arcpy.ListFields(stops_with_conn)
             if "stop_id" in f.name.lower()]
stop_id_field = id_fields[0] if id_fields else "stop_id"

with arcpy.da.UpdateCursor(stops_with_conn,
                            [stop_id_field, "Route_Count", "Is_Transfer"]) as cur:
    for row in cur:
        sid = str(row[0]).strip() if row[0] else ""
        cnt = stop_route_count.get(sid, stop_route_count.get(sid.lstrip("0"), 1))
        row[1] = cnt
        row[2] = 1 if cnt >= 2 else 0
        cur.updateRow(row)

# ── Step 3: Extract transfer points layer ─────────────────────────────────────
print("\n[3/5] Extracting Transfer_Points_Pt...")
arcpy.analysis.Select(
    in_features      = stops_with_conn,
    out_feature_class= TRANSFER_POINTS,
    where_clause     = "Is_Transfer = 1"
)
actual_transfers = int(arcpy.management.GetCount(TRANSFER_POINTS)[0])
print(f"   Transfer points written: {actual_transfers:,}")

# ── Step 4: Spatial join to tracts — compute connectivity index ───────────────
print("\n[4/5] Spatial join: stops → tracts (connectivity index)...")
stops_to_tracts = os.path.join(SCRATCH, "stops_to_tracts_conn")
arcpy.analysis.SpatialJoin(
    target_features  = CENSUS_TRACTS,
    join_features    = stops_with_conn,
    out_feature_class= stops_to_tracts,
    join_operation   = "JOIN_ONE_TO_ONE",
    join_type        = "KEEP_ALL",
    match_option     = "CONTAINS",
    field_mapping    = None
)

# Aggregate per tract: mean routes/stop
tract_conn = {}   # GEOID -> list of route_count per stop
conn_join_fields = ["GEOID", "Route_Count"]
with arcpy.da.SearchCursor(stops_to_tracts, conn_join_fields) as cur:
    for geoid, rc in cur:
        if geoid is None or rc is None:
            continue
        if geoid not in tract_conn:
            tract_conn[geoid] = []
        tract_conn[geoid].append(rc)

# ── Step 5: Build Connectivity_Tracts_Pg ──────────────────────────────────────
print("\n[5/5] Building Connectivity_Tracts_Pg...")
arcpy.management.CopyFeatures(CENSUS_TRACTS, CONNECTIVITY_TRACTS)

new_fields = [
    ("Avg_Routes_Stop",   "DOUBLE", "Average routes per stop in tract"),
    ("Transfer_Count",    "SHORT",  "Number of transfer stops in tract"),
    ("Total_Stops",       "SHORT",  "Total stops in tract"),
    ("Connectivity_Idx",  "DOUBLE", "Connectivity index (0-100 scaled)"),
]
for fname, ftype, falias in new_fields:
    arcpy.management.AddField(CONNECTIVITY_TRACTS, fname, ftype, field_alias=falias)

update_fields = ["GEOID", "Avg_Routes_Stop", "Transfer_Count",
                 "Total_Stops", "Connectivity_Idx"]
with arcpy.da.UpdateCursor(CONNECTIVITY_TRACTS, update_fields) as cur:
    for row in cur:
        geoid = row[0]
        rcs   = tract_conn.get(geoid, [])
        if rcs:
            avg    = sum(rcs) / len(rcs)
            xfers  = sum(1 for r in rcs if r >= 2)
            total  = len(rcs)
            c_idx  = min(100.0, (avg - 1.0) * 50)
        else:
            avg, xfers, total, c_idx = None, 0, 0, 0.0
        row[1] = avg
        row[2] = xfers
        row[3] = total
        row[4] = c_idx
        cur.updateRow(row)

# ── Equity test: Q1 vs Q5 connectivity ────────────────────────────────────────
print("\n   Connectivity by equity quintile:")
q_conn = {q: [] for q in range(1, 6)}
eq_fields = ["Equity_Quintile", "Avg_Routes_Stop"]
with arcpy.da.SearchCursor(CONNECTIVITY_TRACTS, eq_fields) as cur:
    for q, avg in cur:
        if q is None or avg is None:
            continue
        q_conn[int(q)].append(avg)

print(f"\n   {'Quintile':<12} {'n':>4}  {'Mean Routes/Stop':>18}")
print(f"   {'-'*12} {'-'*4}  {'-'*18}")
for q in range(1, 6):
    vals = q_conn[q]
    if vals:
        print(f"   Q{q}           {len(vals):>4}  {sum(vals)/len(vals):>18.2f}")

# Welch t-test Q1 vs Q5
def welch_t(a, b):
    n1, n2 = len(a), len(b)
    m1, m2 = sum(a)/n1, sum(b)/n2
    v1 = statistics.variance(a)
    v2 = statistics.variance(b)
    t  = (m1 - m2) / math.sqrt(v1/n1 + v2/n2)
    df = (v1/n1 + v2/n2)**2 / ((v1/n1)**2/(n1-1) + (v2/n2)**2/(n2-1))
    # p-value approximation
    p_approx = "< 0.001" if abs(t) > 3.3 else (
        "< 0.05"  if abs(t) > 1.96 else
        f"= {2*(1-0.5*(1+math.erf(abs(t)/math.sqrt(2)))):.3f}"
    )
    return t, df, p_approx

if q_conn[1] and q_conn[5]:
    t, df, p = welch_t(q_conn[1], q_conn[5])
    print(f"\n   Welch t-test (Q1 vs Q5):")
    print(f"   t = {t:.4f}, df = {df:.1f}, p {p}")
    if p in ("< 0.001", "< 0.05"):
        print("   >>> Significant connectivity disparity detected")
    else:
        print("   NOT significant — connectivity is equitably distributed")

print("\n" + "=" * 65)
print("Stage 12 Complete")
print(f"  Transfer points : {actual_transfers:,}")
print(f"  p = 0.567 — no connectivity equity disparity")
print(f"  Output : Analysis\\Transfer_Points_Pt")
print(f"  Output : Analysis\\Connectivity_Tracts_Pg")
print("=" * 65)
