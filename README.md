# Baltimore Transit Equity Analysis
### Does MTA Maryland's transit system equitably serve Baltimore's most vulnerable residents?

**Author:** Nathaniel K.A. Stephens  
**Institution:** Morgan State University — MSc Urban Transportation  

---

![Analysis Status](https://img.shields.io/badge/Status-In%20Progress-orange)
![ArcGIS Pro](https://img.shields.io/badge/ArcGIS%20Pro-3.x-blue)
![Python](https://img.shields.io/badge/Python-3.x-green)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## 🔑 Key Finding

> Baltimore's MTA covers **99.7% of residential land** within a 15-minute walk.
> Yet residents in the city's most vulnerable neighborhoods spend **57% longer commuting** —
> an **11.2-minute gap** that reveals systemic inequity in service quality, not geographic access.

| Equity Level | Avg Commute | Gap vs Very Low |
|-------------|-------------|-----------------|
| Very Low | 19.7 min | — |
| Low | 21.4 min | +1.7 min |
| Moderate | 23.9 min | +4.2 min |
| High | 27.3 min | +7.6 min |
| **Very High** | **30.9 min** | **+11.2 min** |

---

## 📁 Repository Structure

```
baltimore-transit-equity/
│
├── scripts/
│   ├── 01_gtfs_conversion.py          ← Convert 5 GTFS feeds to feature classes
│   ├── 02_walktime_calculation.py     ← WalkTime field (Shape_Length / 264)
│   ├── 03_census_extraction.py        ← Extract variables from transposed CSVs
│   ├── 04_census_master_merge.py      ← Merge tables + calculate Pct_ fields
│   ├── 05_tractce_format_fix.py       ← Fix leading zero + join to shapefile
│   ├── 06_equity_index_build.py       ← 19-indicator index + quintile breaks
│   ├── 07_new_fields_calculation.py   ← 5 additional fields + Pct_Minority update
│   └── 08_gap_analysis.py             ← Transit desert identification (coming)
│
├── data/
│   ├── gtfs/                          ← Raw GTFS feeds (not tracked — see below)
│   └── census/
│       └── cleaned/                   ← Cleaned Census CSVs (not tracked)
│
├── docs/
│   ├── Baltimore_Transit_Equity_ProjectLog.md   ← Full methodology log
│   └── methodology_decisions.md                 ← Key decisions + rationale
│
├── maps/                              ← Exported map images (300 dpi, coming)
│
├── index.html                         ← Portfolio page (GitHub Pages)
├── README.md
└── .gitignore
```

---

## 📊 Analysis Overview

### Study Area
Baltimore City, Maryland — 199 Census Tracts, 92 square miles

### Software & Tools
- ArcGIS Pro 3.x (Network Analyst, Spatial Statistics)
- Python 3.x with arcpy and NumPy
- Coordinate System: NAD 1983 StatePlane Maryland FIPS 1900 US Feet (EPSG 2248)

### Data Sources

| Dataset | Source | Year |
|---------|--------|------|
| GTFS Transit Feeds (5 feeds) | MTA Maryland — feeds.mta.maryland.gov | 2025 |
| Census Demographics (14 tables) | US Census ACS 5-Year | 2022 |
| Road Network | OpenStreetMap | 2025 |
| Land Use | OpenStreetMap | 2025 |

---

## ✅ Completed Steps

### 1. Pedestrian Network Dataset
- OSM road network filtered and projected to EPSG 2248
- `WalkTime = Shape_Length / 264` (feet per minute at 3mph)
- Network dataset: `Baltimore_Walk_ND`

### 2. GTFS Processing
Five MTA Maryland feeds downloaded and converted:

| Feed | Stops (All Maryland) | Stops (Baltimore Only) |
|------|---------------------|----------------------|
| Local Bus | 4,032 | 2,601 (88.1%) |
| Metro Subway | 239 | 207 (7.0%) |
| Light Rail | 161 | 82 (2.8%) |
| Commuter Bus | 487 | 57 (1.9%) |
| MARC Train | 79 | 5 (0.2%) |
| **Total** | **4,998** | **2,952** |

### 3. Service Area Analysis
- 5 / 10 / 15 minute walk ring polygons from all 2,952 stops
- **Rings** method (not disks) preserves access quality gradient
- Water bodies erased from polygons
- Output: `ServiceArea_Rings_Clean_Pg`

**Coverage Results (Land Area Only):**
```
Total city area:          92.0 sq miles
Water area:               11.3 sq miles (12.3%)
Land area only:           80.7 sq miles
Covered land:             75.4 sq miles (93.4%)
Transit desert (all land): 5.3 sq miles  (6.6%)
Residential desert:        0.08 sq miles (0.3%)
```

### 4. Census Data Processing
- 14 ACS 5-Year 2022 tables downloaded from data.census.gov
- 199 Baltimore City Census tracts × 108 variables
- **Critical fix:** TRACTCE integer→string format (`.zfill(6)`) required for join
- Output: `CensusTracts_Demographics_Pg`

### 5. Composite Equity Need Index — 19 Indicators

Method: Min-max normalize → invert income → apply weights → scale 0–100 → percentile quintiles

| # | Indicator | Weight |
|---|-----------|--------|
| 1 | Pct_Minority (All Non-White) | 12% |
| 2 | Pct_Poverty | 9% |
| 3 | Med_HH_Income (inverted) | 7% |
| 4 | Pct_ZeroVehicle | 6% |
| 5 | Pct_ZeroVeh_Combined | 6% |
| 6 | Pct_Disability | 5% |
| 7 | Pct_Elderly | 5% |
| 8 | Pct_LimitedEnglish | 5% |
| 9 | Pct_TransitCommute | 5% |
| 10 | Avg_Travel_Time | 5% |
| 11 | Pct_BusDependent | 5% |
| 12 | Pct_NotCitizen | 4% |
| 13 | Pct_Youth | 4% |
| 14 | Pct_Under18Poverty | 4% |
| 15 | Pct_Elderly75Dis | 4% |
| 16 | Pct_FemaleTravelTime | 4% |
| 17 | Pct_MaleTravelTime | 4% |
| 18 | Pct_Over65Poverty | 3% |
| 19 | Pct_Renters | 3% |

**Quintile Results:**

| Level | Tracts | Score Range |
|-------|--------|-------------|
| Very Low | 40 | 11.1 — 26.3 |
| Low | 40 | 26.3 — 36.4 |
| Moderate | 39 | 36.4 — 43.2 |
| High | 41 | 43.2 — 49.1 |
| Very High | 39 | 49.1 — 67.3 |

> Quintile breaks use the 20/40/60/80th percentile method — the federal standard for equity analysis (used by USDOT, FTA, and MPOs).

---

## 🔄 In Progress

### Gap Analysis
Identifying transit desert zones by erasing service area from land-only city boundary.
Filtering desert to residential, retail, and commercial land uses.

### Service Quality Analysis — 4 Causes of the 11.2 Min Gap

| Cause | Hypothesis | Status |
|-------|-----------|--------|
| Rail vs Bus Speed | Low-need areas near rail; high-need areas bus-only | 🔄 In Progress |
| Route Frequency | Fewer trips/hour in high-need tracts | ⏳ Pending |
| Transfer Requirements | Fewer routes per stop = more transfers | ⏳ Pending |
| Job Accessibility | Routes don't connect to employment centers | ⏳ Pending |

---

## ⏳ Upcoming

- [ ] Hot Spot Analysis (Getis-Ord Gi* on Equity_Score)
- [ ] Destination Access (hospitals, schools, grocery stores)
- [ ] 12 static map exports at 300 dpi
- [ ] ArcGIS StoryMap
- [ ] ArcGIS Dashboard
- [ ] PDF technical report

---

## 🗺️ Portfolio & StoryMap

**Portfolio Page:** [nathanielstephens.github.io/baltimore-transit-equity](https://github.io)  
**ArcGIS StoryMap:** Coming soon — hosted via Morgan State University ArcGIS Online  
**ArcGIS Dashboard:** Coming soon

---

## ▶️ Running The Scripts

All scripts require ArcGIS Pro with the Network Analyst extension and arcpy.

```bash
# Run in order
python scripts/01_gtfs_conversion.py
python scripts/02_walktime_calculation.py
python scripts/03_census_extraction.py
python scripts/04_census_master_merge.py
python scripts/05_tractce_format_fix.py
python scripts/07_new_fields_calculation.py   # Note: 07 before 06
python scripts/06_equity_index_build.py
```

> **Note:** Service area analysis (Step 3) is run manually in ArcGIS Pro
> due to the complexity of the network solver configuration.
> All other steps are fully scripted.

**Update paths** in each script before running:
```python
gdb = r"C:\Users\YOUR_USERNAME\Documents\ArcGIS\Projects\MyProject\MyProject.gdb"
```

---

## 📋 Methodology Notes

**Why Rings not Disks?**
Rings (annular polygons) show the access quality gradient — 5-minute = excellent, 10-minute = good, 15-minute = marginal. Disks would show cumulative coverage but obscure quality differences.

**Why Percentile Quintiles?**
The 20/40/60/80th percentile method is the federal standard for equity analysis used by USDOT, FTA, and EPA Environmental Justice programs. It ensures approximately equal numbers of tracts in each class and is statistically defensible.

**Why All Non-White for Minority?**
The federal Title VI definition of minority includes all non-white populations. Using Black + Hispanic only would undercount Latino, Asian, and other communities facing transit equity concerns in Baltimore.

**Why is the desert 0.3% not 6.6%?**
The 5.3 sq mile desert figure includes highways, parks, cemeteries, and industrial land where people don't live or work. Filtered to residential, retail, and commercial land only, the meaningful desert is 0.08 sq miles (0.3%).

---

## 📄 License

MIT License — data is publicly sourced and freely reproducible.

---

*Morgan State University · Department of Transportation Studies · Baltimore, MD*
