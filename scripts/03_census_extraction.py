# ============================================================
# 03_census_extraction.py
# Baltimore Transit Equity Analysis
# Extract variables from transposed Census CSV files
#
# Author:  Nathaniel K.A. Stephens
# Date:    March 2026
#
# Inputs:  14 Census ACS 5-Year 2022 CSV files in data/census/
#          Downloaded from data.census.gov
#          Baltimore City, Census Tract level
#
# CRITICAL: Census CSVs are in TRANSPOSED format
#           Rows = variables, Columns = tracts
#           Script uses exact row indices to extract variables
#
# Outputs: Cleaned CSV files in data/census/cleaned/
#          One file per table with correct variables extracted
# ============================================================

import pandas as pd
import os
import numpy as np

# ── PATHS ────────────────────────────────────────────────────
project_dir  = r"C:\Users\kojoa\Documents\ArcGIS\Projects\MyProject"
census_dir   = os.path.join(project_dir, "data", "census")
cleaned_dir  = os.path.join(project_dir, "data", "census", "cleaned")

os.makedirs(cleaned_dir, exist_ok=True)

print("=" * 60)
print("CENSUS DATA EXTRACTION")
print("ACS 5-Year 2022 — Baltimore City Census Tracts")
print("=" * 60)

# ── HELPER FUNCTION ──────────────────────────────────────────
def load_transposed_census(filepath, var_rows, new_names):
    """
    Load a transposed Census CSV where:
    - Row 0 = header (tract IDs)
    - Subsequent rows = one variable per row
    var_rows: list of row indices to extract (0-indexed from data rows)
    new_names: list of new column names for extracted variables
    Returns: DataFrame with TRACTCE as index and variables as columns
    """
    df = pd.read_csv(filepath, header=0, index_col=0)
    # Extract specified rows
    extracted = df.iloc[var_rows].T.copy()
    extracted.columns = new_names
    # Convert to numeric
    for col in extracted.columns:
        extracted[col] = pd.to_numeric(extracted[col], errors='coerce').fillna(0)
    return extracted

# ── TABLE EXTRACTION DEFINITIONS ────────────────────────────
# Each entry: (filename, var_rows, new_names)
# var_rows = 0-indexed row positions in the CSV data rows

tables = {

    # B01003 — Total Population
    "B01003": (
        "B01003_Population.csv",
        [0],
        ["Total_Pop"]
    ),

    # B03002 — Hispanic or Latino by Race
    "B03002": (
        "B03002_Race.csv",
        [0, 2, 3, 4, 5, 6, 7, 8, 12],
        ["Total_Pop_Race", "White_Alone", "Black_Alone",
         "Native_American", "Asian_Alone", "Pacific_Islander",
         "Other_Race", "Two_Or_More_Races", "Hispanic_Latino"]
    ),

    # B19013 — Median Household Income
    "B19013": (
        "B19013_Income.csv",
        [0],
        ["Med_HH_Income"]
    ),

    # B08201 — Household Vehicle Availability
    "B08201": (
        "B08201_Vehicles.csv",
        [0, 2, 7],
        ["Total_HH", "Zero_Vehicle_HH", "Owner_Zero_Vehicle"]
    ),

    # B17001 — Poverty Status
    "B17001": (
        "B17001_Poverty.csv",
        [0, 2, 3, 17],
        ["Total_Poverty_Pop", "Below_Poverty",
         "Under18_Below_Poverty", "Over65_Below_Poverty"]
    ),

    # B01001 — Sex by Age
    "B01001": (
        "B01001_Age.csv",
        [0, 3, 4, 5, 27, 28, 29,
         20, 21, 22, 44, 45, 46],
        ["Total_Pop_Age",
         "Male_Under5", "Male_5to9", "Male_10to14",
         "Female_Under5", "Female_5to9", "Female_10to14",
         "Male_65to74", "Male_75to84", "Male_85Plus",
         "Female_65to74", "Female_75to84", "Female_85Plus"]
    ),

    # B08301 — Means of Transportation to Work
    "B08301": (
        "B08301_TransportMode.csv",
        [0, 2, 10, 11, 12, 13, 18],
        ["Total_Workers", "Drove_Alone",
         "Bus_Trolley", "Subway_Elevated",
         "Railroad", "Light_Rail", "Transit_Total"]
    ),

    # B18101 — Disability Status
    "B18101": (
        "B18101_Disability.csv",
        [0, 4, 7, 23, 26],
        ["Total_Pop_Dis", "Male_With_Disability",
         "Male_75Plus_Disability", "Female_With_Disability",
         "Female_75Plus_Disability"]
    ),

    # B16005 — Language Spoken at Home
    "B16005": (
        "B16005_Language.csv",
        [0, 5, 10, 15, 20],
        ["Total_Pop_Lang", "Spanish_Limited",
         "IndoEuropean_Limited", "AsianPacific_Limited",
         "OtherLanguage_Limited"]
    ),

    # B05002 — Nativity and Citizenship
    "B05002": (
        "B05002_Nativity.csv",
        [0, 13, 14, 15],
        ["Total_Pop_FB", "Foreign_Born",
         "Naturalized_Citizen", "Not_Citizen"]
    ),

    # B08013 — Aggregate Travel Time to Work
    "B08013": (
        "B08013_TravelTime.csv",
        [0, 2, 3],
        ["Total_Pop_TT", "Male_Travel_Time", "Female_Travel_Time"]
    ),

    # B25003 — Tenure
    "B25003": (
        "B25003_Tenure.csv",
        [0, 2, 3],
        ["Total_HH_Ten", "Owner_Occupied", "Renter_Occupied"]
    ),

    # B25044 — Tenure by Vehicles Available
    "B25044": (
        "B25044_TenureVehicles.csv",
        [0, 2, 7],
        ["Total_HH_Veh_Ten", "Owner_Zero_Vehicle", "Renter_Zero_Vehicle"]
    ),
}

# ── EXTRACT ALL TABLES ───────────────────────────────────────
all_frames = {}

for table_id, (filename, var_rows, new_names) in tables.items():
    filepath = os.path.join(census_dir, filename)

    if not os.path.exists(filepath):
        print(f"  ⚠️  {filename} not found — skipping")
        continue

    try:
        df = load_transposed_census(filepath, var_rows, new_names)
        all_frames[table_id] = df

        # Save cleaned file
        out_path = os.path.join(cleaned_dir, f"{table_id}_cleaned.csv")
        df.to_csv(out_path)
        print(f"  ✅ {table_id:8} → {df.shape[1]:3} variables, "
              f"{df.shape[0]:3} tracts → {table_id}_cleaned.csv")

    except Exception as e:
        print(f"  ❌ {table_id}: {e}")

print(f"\n{'='*60}")
print(f"EXTRACTION COMPLETE")
print(f"  Tables processed:  {len(all_frames)}")
print(f"  Output directory:  data/census/cleaned/")
print(f"  Next step:         Run 04_census_master_merge.py")
print(f"{'='*60}")
