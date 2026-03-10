# ============================================================
# 07_new_fields_calculation.py
# Baltimore Transit Equity Analysis
# Calculate additional fields added after initial index build:
# - Update Pct_Minority to All Non-White definition
# - Pct_ZeroVeh_Combined  (owner + renter zero vehicle)
# - Pct_BusDependent      (bus commuters / workers)
# - Pct_Elderly75Dis      (disabled 75+ / all disabled)
# - Pct_FemaleTravelTime  (female agg travel / workers)
# - Pct_MaleTravelTime    (male agg travel / workers)
#
# Author:  Nathaniel K.A. Stephens
# Date:    March 2026
#
# NOTE: Run this BEFORE 06_equity_index_build.py
#       These fields are inputs to the equity index
#
# Inputs:  CensusTracts_Demographics_Pg (with raw Census vars)
# Outputs: 6 new/updated fields on CensusTracts_Demographics_Pg
# ============================================================

import arcpy

# ── PATHS ────────────────────────────────────────────────────
gdb   = r"C:\Users\kojoa\Documents\ArcGIS\Projects\MyProject\MyProject.gdb"
layer = f"{gdb}\\Base\\CensusTracts_Demographics_Pg"

arcpy.env.overwriteOutput = True

print("=" * 60)
print("NEW FIELDS CALCULATION")
print("=" * 60)

# ── STEP 1 — UPDATE Pct_Minority TO ALL NON-WHITE ────────────
print("\nStep 1 — Updating Pct_Minority to All Non-White definition...")
print("  Previous: (Black_Alone + Hispanic_Latino) / Total_Pop_Race")
print("  Updated:  (Total_Pop_Race - White_Alone)  / Total_Pop_Race")
print("  Reason:   All Non-White = federal Title VI standard")

with arcpy.da.UpdateCursor(
    layer, ["Total_Pop_Race", "White_Alone", "Pct_Minority"]
) as cursor:
    for row in cursor:
        total = row[0] if row[0] else 0
        white = row[1] if row[1] else 0
        if total > 0:
            row[2] = round((total - white) / total * 100, 1)
        else:
            row[2] = 0
        cursor.updateRow(row)

# Show sample comparison
print(f"\n  Sample values after update (first 5 tracts):")
print(f"  {'Tract':8} {'Total Pop':10} {'White':8} {'Pct_Minority':14}")
print("  " + "-" * 45)
with arcpy.da.SearchCursor(
    layer,
    ["TRACTCE", "Total_Pop_Race", "White_Alone", "Pct_Minority"]
) as cursor:
    for i, row in enumerate(cursor):
        if i >= 5:
            break
        print(f"  {row[0]:8} {row[1]:10,} {row[2]:8,} {row[3]:14.1f}%")

print(f"  ✅ Pct_Minority updated — All Non-White definition")

# ── STEP 2 — ADD NEW FIELDS ───────────────────────────────────
print(f"\nStep 2 — Adding new fields...")

new_fields = [
    ("Pct_ZeroVeh_Combined", "DOUBLE", "Zero Vehicle Combined (Owner + Renter)"),
    ("Pct_BusDependent",     "DOUBLE", "Bus Commuters Percentage"),
    ("Pct_Elderly75Dis",     "DOUBLE", "Disabled Age 75+ Percentage"),
    ("Pct_FemaleTravelTime", "DOUBLE", "Female Average Travel Time"),
    ("Pct_MaleTravelTime",   "DOUBLE", "Male Average Travel Time"),
]

for fname, ftype, falias in new_fields:
    try:
        arcpy.management.AddField(
            layer, fname, ftype, field_alias=falias
        )
        print(f"  ✅ {fname} added")
    except Exception as e:
        print(f"  ⚠️  {fname} may already exist: {e}")

# ── STEP 3 — CALCULATE ALL NEW FIELDS ────────────────────────
print(f"\nStep 3 — Calculating values...")

read_fields = [
    "OBJECTID",
    "Owner_Zero_Vehicle",    # 1
    "Renter_Zero_Vehicle",   # 2
    "Total_HH_Veh_Ten",      # 3
    "Bus_Trolley",           # 4
    "Total_Workers",         # 5
    "Age75_Plus_Disability", # 6
    "Total_Pop_Dis",         # 7
    "Female_Travel_Time",    # 8
    "Male_Travel_Time",      # 9
    "Pct_ZeroVeh_Combined",  # 10  ← write
    "Pct_BusDependent",      # 11  ← write
    "Pct_Elderly75Dis",      # 12  ← write
    "Pct_FemaleTravelTime",  # 13  ← write
    "Pct_MaleTravelTime",    # 14  ← write
]

updated = 0
with arcpy.da.UpdateCursor(layer, read_fields) as cursor:
    for row in cursor:
        total_hh = row[3]  if row[3]  else 0
        owner_zv = row[1]  if row[1]  else 0
        renter_zv= row[2]  if row[2]  else 0
        workers  = row[5]  if row[5]  else 0
        bus      = row[4]  if row[4]  else 0
        pop_dis  = row[7]  if row[7]  else 0
        dis_75   = row[6]  if row[6]  else 0
        fem_time = row[8]  if row[8]  else 0
        mal_time = row[9]  if row[9]  else 0

        # Pct_ZeroVeh_Combined = (owner + renter zero veh) / all HH
        row[10] = round((owner_zv + renter_zv) / total_hh * 100, 1) \
                  if total_hh > 0 else 0

        # Pct_BusDependent = bus trolley commuters / total workers
        row[11] = round(bus / workers * 100, 1) \
                  if workers > 0 else 0

        # Pct_Elderly75Dis = disabled 75+ / all disabled
        row[12] = round(dis_75 / pop_dis * 100, 1) \
                  if pop_dis > 0 else 0

        # Pct_FemaleTravelTime = female aggregate travel / workers
        # (avg minutes female workers spend commuting)
        row[13] = round(fem_time / workers, 1) \
                  if workers > 0 else 0

        # Pct_MaleTravelTime = male aggregate travel / workers
        # (avg minutes male workers spend commuting)
        row[14] = round(mal_time / workers, 1) \
                  if workers > 0 else 0

        cursor.updateRow(row)
        updated += 1

print(f"  ✅ {updated} tracts updated")

# ── STEP 4 — VERIFY SAMPLE VALUES ───────────────────────────
print(f"\nStep 4 — Verifying sample values (first 5 tracts):")
print("-" * 75)
print(f"  {'Tract':8} {'ZeroVeh':9} {'Bus%':7} "
      f"{'Dis75%':8} {'FemTime':9} {'MalTime':9}")
print("  " + "-" * 55)

check_fields = [
    "TRACTCE", "Pct_ZeroVeh_Combined", "Pct_BusDependent",
    "Pct_Elderly75Dis", "Pct_FemaleTravelTime", "Pct_MaleTravelTime"
]

with arcpy.da.SearchCursor(layer, check_fields) as cursor:
    for i, row in enumerate(cursor):
        if i >= 5:
            break
        print(f"  {row[0]:8} {row[1]:9.1f} {row[2]:7.1f} "
              f"{row[3]:8.1f} {row[4]:9.1f} {row[5]:9.1f}")

# ── SUMMARY STATISTICS ────────────────────────────────────────
print(f"\n  Summary statistics for new fields:")
print(f"  {'Field':25} {'Min':8} {'Max':8} {'Mean':8}")
print("  " + "-" * 52)

for field in ["Pct_ZeroVeh_Combined", "Pct_BusDependent",
              "Pct_Elderly75Dis", "Pct_FemaleTravelTime",
              "Pct_MaleTravelTime"]:
    values = [row[0] for row in arcpy.da.SearchCursor(layer, [field])
              if row[0] is not None and row[0] > 0]
    if values:
        print(f"  {field:25} {min(values):8.1f} {max(values):8.1f} "
              f"{sum(values)/len(values):8.1f}")

print(f"\n{'='*60}")
print(f"NEW FIELDS CALCULATION COMPLETE")
print(f"{'='*60}")
print(f"  Updated:  Pct_Minority (All Non-White definition)")
print(f"  Added:    Pct_ZeroVeh_Combined")
print(f"            Pct_BusDependent")
print(f"            Pct_Elderly75Dis")
print(f"            Pct_FemaleTravelTime")
print(f"            Pct_MaleTravelTime")
print(f"  Next step: Run 06_equity_index_build.py")
print(f"{'='*60}")
