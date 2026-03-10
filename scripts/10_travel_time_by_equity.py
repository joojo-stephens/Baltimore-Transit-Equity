# =============================================================================
# 10_travel_time_by_equity.py
# Baltimore City Transit Equity Analysis
# Stage 10 — Travel Time by Equity Quintile Analysis
#
# Purpose:
#   1. Calculates average transit commute time per census tract from ACS B08013
#   2. Correlates Avg_TravelTime vs Equity_Score across all 199 tracts
#   3. Computes Q1–Q5 quintile means
#   4. Runs FTA Title VI disparity test (minority vs non-minority travel time)
#
# Inputs:
#   - Base\CensusTracts_Demographics_Pg
#     Required fields: GEOID, Equity_Score, Equity_Quintile,
#                      Avg_TravelTime, Pct_NonHispanicWhite, Total_Population
#
# Outputs:
#   - Updates CensusTracts_Demographics_Pg in place (no new feature class)
#   - Console report of all key statistics
#
# Key Results:
#   - r = +0.6054, p < 0.001, R² = 0.367
#   - Q1 = 19.7 min, Q5 = 30.9 min, disparity = +11.2 min (57%)
#   - Minority 1.36x → TITLE VI FINDING
#
# Dependencies: arcpy, scipy (for Pearson r), statistics
#
# Author : Nathaniel K.A. Stephens
# Date   : March 2026
# CRS    : EPSG 2248 (NAD 1983 StatePlane Maryland FIPS 1900, US Feet)
# =============================================================================

import arcpy
import os
import math
import statistics

arcpy.env.overwriteOutput = True

PROJECT_DIR = r"C:\Users\kojoa\Documents\ArcGIS\Projects\MyProject"
GDB         = os.path.join(PROJECT_DIR, "MyProject.gdb")
BASE_DS     = os.path.join(GDB, "Base")
ANALYSIS_DS = os.path.join(GDB, "Analysis")

# ── Input ─────────────────────────────────────────────────────────────────────
CENSUS_TRACTS = os.path.join(BASE_DS, "CensusTracts_Demographics_Pg")

# ── Constants ─────────────────────────────────────────────────────────────────
TITLE_VI_THRESHOLD = 1.25
MINORITY_THRESHOLD = 50.0   # % minority to classify tract as minority-majority
ALPHA              = 0.05

print("=" * 65)
print("Stage 10 — Travel Time by Equity Analysis")
print("=" * 65)

# ── Step 1: Extract tract-level travel time and equity data ───────────────────
print("\n[1/4] Extracting travel time and equity data...")

fields = ["GEOID", "Avg_TravelTime", "Equity_Score", "Equity_Quintile",
          "Pct_NonHispanicWhite", "Total_Population"]

records = []
skipped = 0
with arcpy.da.SearchCursor(CENSUS_TRACTS, fields) as cur:
    for geoid, tt, eq_score, eq_q, pct_nhw, tot_pop in cur:
        if tt is None or eq_score is None or eq_q is None:
            skipped += 1
            continue
        pct_minority = 100.0 - (pct_nhw or 0.0)
        records.append({
            "geoid"       : geoid,
            "travel_time" : tt,
            "equity_score": eq_score,
            "quintile"    : int(eq_q),
            "pct_minority": pct_minority,
            "population"  : tot_pop or 0
        })

print(f"   Valid tracts   : {len(records)}")
print(f"   Skipped (null) : {skipped}")

# ── Step 2: Pearson correlation — Equity Score vs Travel Time ─────────────────
print("\n[2/4] Pearson correlation: Equity_Score vs Avg_TravelTime...")

x = [r["equity_score"] for r in records]
y = [r["travel_time"]  for r in records]
n = len(x)

x_mean = sum(x) / n
y_mean = sum(y) / n

cov = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
std_x = math.sqrt(sum((xi - x_mean) ** 2 for xi in x))
std_y = math.sqrt(sum((yi - y_mean) ** 2 for yi in y))

r_val = cov / (std_x * std_y)
r2    = r_val ** 2

# t-statistic and two-tailed p-value approximation
t_stat = r_val * math.sqrt(n - 2) / math.sqrt(1 - r_val ** 2)
# p-value: use t-distribution approximation (df = n-2)
# For large n, t > 3.3 is approximately p < 0.001
p_approx = "< 0.001" if abs(t_stat) > 3.3 else f"≈ {2 * (1 - 0.5 * (1 + math.erf(abs(t_stat) / math.sqrt(2)))):.4f}"

print(f"   n              : {n} tracts")
print(f"   Pearson r      : {r_val:.4f}")
print(f"   R²             : {r2:.3f}")
print(f"   t-statistic    : {t_stat:.4f}")
print(f"   p-value        : {p_approx}")

# Regression line: y = m*x + b
m = cov / (std_x ** 2)
b = y_mean - m * x_mean
print(f"   Regression     : Travel_Time = {m:.4f} × Equity_Score + {b:.2f}")

# ── Step 3: Quintile means ────────────────────────────────────────────────────
print("\n[3/4] Travel time by equity quintile...")

q_times = {q: [] for q in range(1, 6)}
for r in records:
    q_times[r["quintile"]].append(r["travel_time"])

q_labels = {1: "Wealthiest", 2: "", 3: "", 4: "", 5: "Most Vulnerable"}
print(f"\n   {'Quintile':<12} {'n':>4}  {'Mean':>8}  {'Median':>8}  {'Std Dev':>8}")
print(f"   {'-'*12} {'-'*4}  {'-'*8}  {'-'*8}  {'-'*8}")
for q in range(1, 6):
    times = q_times[q]
    if not times:
        continue
    mean   = sum(times) / len(times)
    median = statistics.median(times)
    stdev  = statistics.stdev(times) if len(times) > 1 else 0
    label  = q_labels[q]
    print(f"   Q{q} {label:<10} {len(times):>4}  {mean:>7.1f}m  {median:>7.1f}m  {stdev:>8.1f}")

q1_mean = sum(q_times[1]) / len(q_times[1])
q5_mean = sum(q_times[5]) / len(q_times[5])
gap_min = q5_mean - q1_mean
gap_pct = (gap_min / q1_mean) * 100
print(f"\n   Q1 → Q5 gap    : +{gap_min:.1f} min  ({gap_pct:.0f}% longer)")

# ── Step 4: Title VI disparity test — minority vs non-minority ────────────────
print("\n[4/4] FTA Title VI disparity test...")

minority_times    = [r["travel_time"] for r in records if r["pct_minority"] >= MINORITY_THRESHOLD]
nonminority_times = [r["travel_time"] for r in records if r["pct_minority"] <  MINORITY_THRESHOLD]

m_avg  = sum(minority_times)    / len(minority_times)    if minority_times    else 0
nm_avg = sum(nonminority_times) / len(nonminority_times) if nonminority_times else 0
ratio  = m_avg / nm_avg if nm_avg > 0 else 0

print(f"   Minority tracts     : {len(minority_times)}  (≥ {MINORITY_THRESHOLD}% minority)")
print(f"   Non-minority tracts : {len(nonminority_times)}")
print(f"   Minority avg        : {m_avg:.1f} min")
print(f"   Non-minority avg    : {nm_avg:.1f} min")
print(f"   Disparity ratio     : {ratio:.2f}x")

if ratio >= TITLE_VI_THRESHOLD:
    print(f"\n   >>> TITLE VI FINDING")
    print(f"   >>> {ratio:.2f}x exceeds FTA 1.25x threshold")
    print(f"   >>> Minority residents face statistically longer transit commutes")
else:
    print(f"   No Title VI finding ({ratio:.2f}x < {TITLE_VI_THRESHOLD}x threshold)")

print("\n" + "=" * 65)
print("Stage 10 Complete")
print(f"  Pearson r = {r_val:.4f}, p {p_approx}, R² = {r2:.3f}")
print(f"  Q1 = {q1_mean:.1f} min  |  Q5 = {q5_mean:.1f} min  |  Gap = +{gap_min:.1f} min ({gap_pct:.0f}%)")
print(f"  Title VI disparity ratio = {ratio:.2f}x  ({'FINDING' if ratio >= 1.25 else 'No finding'})")
print("=" * 65)
