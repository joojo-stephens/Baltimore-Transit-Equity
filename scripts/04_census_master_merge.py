# ============================================================
# 04_census_master_merge.py
# Baltimore Transit Equity Analysis
# Merge all cleaned Census tables into one master CSV
# Calculate all derived percentage fields
#
# Author:  Nathaniel K.A. Stephens
# Date:    March 2026
#
# Inputs:  Cleaned CSV files from data/census/cleaned/
# Outputs: Baltimore_Census_Master.csv (199 tracts x 108 cols)
#          17 calculated Pct_ fields included
# ============================================================

import pandas as pd
import numpy as np
import os

# ── PATHS ────────────────────────────────────────────────────
project_dir = r"C:\Users\kojoa\Documents\ArcGIS\Projects\MyProject"
cleaned_dir = os.path.join(project_dir, "data", "census", "cleaned")
out_path    = os.path.join(cleaned_dir, "Baltimore_Census_Master.csv")

print("=" * 60)
print("CENSUS MASTER MERGE")
print("=" * 60)

# ── SAFE PERCENTAGE HELPER ───────────────────────────────────
def safe_pct(numerator, denominator):
    """Calculate percentage safely — returns 0 if denominator is 0"""
    result = numerator.copy().astype(float)
    mask   = denominator > 0
    result[mask]  = (numerator[mask] / denominator[mask]) * 100
    result[~mask] = 0
    return result.round(1)

# ── LOAD ALL CLEANED TABLES ──────────────────────────────────
print("\nLoading cleaned tables...")

table_files = [f for f in os.listdir(cleaned_dir)
               if f.endswith("_cleaned.csv")]

frames = []
for fname in sorted(table_files):
    fpath = os.path.join(cleaned_dir, fname)
    df    = pd.read_csv(fpath, index_col=0)
    frames.append(df)
    print(f"  ✅ {fname:30} → {df.shape[1]} variables")

# ── MERGE ALL TABLES ─────────────────────────────────────────
print(f"\nMerging {len(frames)} tables...")
master = pd.concat(frames, axis=1)

# Remove duplicate columns if any
master = master.loc[:, ~master.columns.duplicated()]
print(f"  ✅ Merged: {master.shape[0]} tracts × {master.shape[1]} columns")

# ── EXTRACT TRACTCE FROM INDEX ───────────────────────────────
# Index contains Census GeoID — extract tract number
print(f"\nExtracting TRACTCE from GeoID...")

def extract_tractce(geoid):
    """Extract 6-digit TRACTCE from Census GeoID string"""
    try:
        # GeoID format: 1400000US24510XXXXXX
        # Last 6 digits = tract code
        s = str(geoid).strip()
        if "US" in s:
            return s[-6:]
        elif len(s) == 6:
            return s
        else:
            return str(int(float(s))).zfill(6)
    except:
        return "000000"

master["TRACTCE_STR"] = master.index.map(extract_tractce)
master["TRACTCE"]     = master["TRACTCE_STR"].astype(int)

print(f"  ✅ TRACTCE_STR and TRACTCE fields created")
print(f"  Sample: {master['TRACTCE_STR'].head(5).tolist()}")

# ── CALCULATE DERIVED FIELDS ─────────────────────────────────
print(f"\nCalculating derived percentage fields...")

# Aggregate fields needed before percentages
if "Male_Under5" in master.columns:
    master["Under_5"]       = master.get("Male_Under5",0)      + master.get("Female_Under5",0)
    master["Age_5_to_17"]   = (master.get("Male_5to9",0)       + master.get("Male_10to14",0) +
                                master.get("Female_5to9",0)     + master.get("Female_10to14",0))
    master["Age_65_to_74"]  = master.get("Male_65to74",0)      + master.get("Female_65to74",0)
    master["Age_75_Plus"]   = (master.get("Male_75to84",0)     + master.get("Male_85Plus",0) +
                                master.get("Female_75to84",0)   + master.get("Female_85Plus",0))

if "Male_With_Disability" in master.columns:
    master["With_Disability"]      = master.get("Male_With_Disability",0)   + master.get("Female_With_Disability",0)
    master["Age75_Plus_Disability"]= master.get("Male_75Plus_Disability",0) + master.get("Female_75Plus_Disability",0)

if "Spanish_Limited" in master.columns:
    master["Total_Limited_English"] = (master.get("Spanish_Limited",0) +
                                       master.get("IndoEuropean_Limited",0) +
                                       master.get("AsianPacific_Limited",0) +
                                       master.get("OtherLanguage_Limited",0))

# Rename Total_Pop from B01003 if needed
if "Total_Pop" not in master.columns and "Total_Pop_x" in master.columns:
    master.rename(columns={"Total_Pop_x": "Total_Pop"}, inplace=True)

# Percentage calculations
pct_fields = {
    "Pct_Black"          : (master.get("Black_Alone",         0), master.get("Total_Pop_Race",  1)),
    "Pct_Hispanic"       : (master.get("Hispanic_Latino",     0), master.get("Total_Pop_Race",  1)),
    "Pct_White"          : (master.get("White_Alone",         0), master.get("Total_Pop_Race",  1)),
    "Pct_Poverty"        : (master.get("Below_Poverty",       0), master.get("Total_Poverty_Pop",1)),
    "Pct_ZeroVehicle"    : (master.get("Zero_Vehicle_HH",     0), master.get("Total_HH",        1)),
    "Pct_LimitedEnglish" : (master.get("Total_Limited_English",0),master.get("Total_Pop_Lang",  1)),
    "Pct_ForeignBorn"    : (master.get("Foreign_Born",        0), master.get("Total_Pop_FB",    1)),
    "Pct_NotCitizen"     : (master.get("Not_Citizen",         0), master.get("Total_Pop_FB",    1)),
    "Pct_TransitCommute" : (master.get("Transit_Total",       0), master.get("Total_Workers",   1)),
    "Pct_RenterZeroVeh"  : (master.get("Renter_Zero_Vehicle", 0), master.get("Total_HH_Veh_Ten",1)),
    "Pct_Under18Poverty" : (master.get("Under18_Below_Poverty",0),master.get("Total_Poverty_Pop",1)),
    "Pct_Over65Poverty"  : (master.get("Over65_Below_Poverty",0), master.get("Total_Poverty_Pop",1)),
    "Pct_Renters"        : (master.get("Renter_Occupied",     0), master.get("Total_HH_Ten",    1)),
}

# Disability, Elderly, Youth need aggregated fields
if "With_Disability" in master.columns:
    pct_fields["Pct_Disability"] = (master["With_Disability"], master.get("Total_Pop_Dis", 1))

if "Age_65_to_74" in master.columns:
    pct_fields["Pct_Elderly"] = (master["Age_65_to_74"] + master["Age_75_Plus"],
                                  master.get("Total_Pop_Age", 1))

if "Under_5" in master.columns:
    pct_fields["Pct_Youth"] = (master["Under_5"] + master["Age_5_to_17"],
                                master.get("Total_Pop_Age", 1))

# Pct_Minority = All Non-White (federal standard)
if "White_Alone" in master.columns and "Total_Pop_Race" in master.columns:
    pct_fields["Pct_Minority"] = (master["Total_Pop_Race"] - master["White_Alone"],
                                   master["Total_Pop_Race"])

# Avg_Travel_Time
if "Male_Travel_Time" in master.columns and "Total_Workers" in master.columns:
    master["Avg_Travel_Time"] = (
        (master["Male_Travel_Time"] + master["Female_Travel_Time"]) /
        master["Total_Workers"].replace(0, np.nan)
    ).fillna(0).round(1)
    print(f"  ✅ Avg_Travel_Time calculated")

# Apply all percentage calculations
for field_name, (num, denom) in pct_fields.items():
    master[field_name] = safe_pct(
        pd.Series(num).fillna(0).values,
        pd.Series(denom).replace(0, np.nan).fillna(1).values
    )
    print(f"  ✅ {field_name}")

# ── SAVE MASTER CSV ──────────────────────────────────────────
master.to_csv(out_path, index=True)

print(f"\n{'='*60}")
print(f"MASTER CSV COMPLETE")
print(f"{'='*60}")
print(f"  Output:   Baltimore_Census_Master.csv")
print(f"  Tracts:   {master.shape[0]}")
print(f"  Columns:  {master.shape[1]}")
print(f"\n  Pct_ fields calculated:")
for f in sorted([c for c in master.columns if c.startswith("Pct_")]):
    print(f"  → {f}")
print(f"\n  Next step: Run 05_tractce_format_fix.py")
print(f"{'='*60}")
