# 🚌 Baltimore City Transit Equity Analysis

**A spatial equity analysis of the MTA transit network across 199 Baltimore census tracts**

> *Graduate Portfolio Project — MSc Urban Transportation · Morgan State University · March 2026*
> *Nathaniel K.A. Stephens*

[![ArcGIS Online](https://img.shields.io/badge/ArcGIS-Feature_Service-0079C1?style=flat&logo=esri&logoColor=white)](https://services3.arcgis.com/f6DdLR4lY5RnYDuG/arcgis/rest/services/Baltimore_Transit_Equity/FeatureServer)
[![StoryMap](https://img.shields.io/badge/ArcGIS-StoryMap-56A0D3?style=flat&logo=esri&logoColor=white)](https://arcg.is/zTrOO)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Nathaniel_Stephens-0077B5?style=flat&logo=linkedin&logoColor=white)](https://linkedin.com/in/nathaniel-stephens1)

---

## 📋 Overview

This project examines how equitably the Maryland Transit Administration (MTA) serves Baltimore City's diverse communities. Using GTFS transit data, US Census ACS 2020 estimates, and an OpenStreetMap pedestrian network, a complete spatial analysis pipeline was built in ArcGIS Pro with Python (arcpy) to evaluate five dimensions of transit equity:

| Dimension | Method | Key Outcome |
|---|---|---|
| Spatial Coverage | Network Analyst service areas | 12.4% of city is a transit desert |
| Service Frequency | GTFS headway analysis | Frequency paradox confirmed (r = −0.356) |
| Commute Burden | ACS travel time + equity quintiles | **FTA Title VI finding** (1.36×) |
| Modal Access | Stop-level mode classification | 95.8% bus dependency |
| Network Connectivity | Route diversity per stop | Equitably distributed (p = 0.567) |

---

## ⚖️ FTA Title VI Findings

Two **formal disparate impact findings** were confirmed under FTA Circular 4702.1B (2012), which sets a 1.25× threshold for federal equity violations:

| Finding | Population | Disparity Ratio | Threshold | Result |
|---|---|---|---|---|
| Transit Desert Overrepresentation | Hispanic residents | **1.54×** | 1.25× | ❌ VIOLATION |
| Commute Time Burden | Minority residents | **1.36×** | 1.25× | ❌ VIOLATION |

---

## 🗺️ 12-Map Portfolio Series

| # | Map Title | Analysis |
|---|---|---|
| 01 | Study Area Overview | 433 routes, 5 modes, 199 tracts |
| 02 | Transit Network | MTA routes and 2,678 stops by mode |
| 03 | Service Area Coverage | Walkable access within 5 and 10 minutes |
| 04 | Transit Desert Zones | Areas beyond 10-min walk — 10.04 sq mi |
| 05 | Neighbourhood Equity Index | 19-indicator composite vulnerability score |
| 06 | Service Frequency | Average headway by census tract |
| 07 | Frequency Gap Zones | 18 tracts with headway > 30 minutes |
| 08 | Commute Time Burden | Travel time to work · **Title VI finding** |
| 09 | Transit Modal Access | Bus-only vs. rail-served tracts |
| 10 | Network Connectivity | Transfer points and route density |
| 11 | FTA Title VI Findings | Disparate impact by race and ethnicity |
| 12 | Composite Equity Summary | Service, access and burden synthesis |

---

## 📊 Key Findings at a Glance

- **57% longer commutes** for low-income residents vs. wealthy residents (30.9 vs. 19.7 min)
- **The Frequency Paradox** — MTA actually serves vulnerable neighborhoods *more* frequently (r = −0.356, p < 0.001). Frequency is not the equity problem.
- **The real problem is spatial mismatch** — low-income and minority residents live far from employment centers, resulting in disproportionate commute burden regardless of service quality.
- **95.8% bus dependency** — only 21 of 199 census tracts (10.5%) have any rail access.
- **1,107 transfer points** citywide — network connectivity is Baltimore's most equitably distributed transit attribute (p = 0.567).

---

## 🛠️ Technical Stack

| Tool | Purpose |
|---|---|
| **ArcGIS Pro 3.x** | Spatial analysis, Network Analyst, map production |
| **Python (arcpy)** | 13-script analysis automation pipeline |
| **MTA GTFS 2024** | Transit route and stop data, all 5 modes |
| **US Census ACS 2020** | 14 demographic tables, census tract level |
| **OpenStreetMap** | Pedestrian road network for walk-time service areas |
| **scipy / pandas** | Statistical analysis, Welch t-tests, correlation |
| **ArcGIS Online** | Feature service hosting and web publishing |
| **ArcGIS StoryMaps** | Public-facing narrative presentation |

**Coordinate Reference System:** EPSG 2248 (NAD 1983 StatePlane Maryland FIPS 1900, US Feet)

---

## 📁 Repository Structure

```
Baltimore-Transit-Equity/
│
├── scripts/                    # Python analysis pipeline (arcpy)
│   ├── 01_project_data.py
│   ├── 02_clip_layers.py
│   ├── 03_rename_osm.py
│   ├── 04_join_acs.py
│   ├── 05_build_network.py
│   ├── 06_gtfs_to_features.py
│   ├── 07_equity_index.py
│   ├── 08_gap_analysis.py
│   ├── 09_desert_demographics.py
│   ├── 10_travel_time_by_equity.py
│   ├── 11_mode_stops_export.py
│   ├── 12_connectivity_analysis.py
│   └── 13_frequency_analysis.py
│
├── maps/                       # Exported map images (300 DPI PNG + PDF)
│   ├── image/                  # PNG exports
│   └── pdf/                    # PDF exports
│
├── docs/                       # Project documentation
│   ├── Methodology_Report.docx
│   ├── Findings_and_Questions.docx
│   ├── Charts_Report.docx
│   └── Project_Outline.docx
│
├── transit_equity_showcase.html                  # Project showcase webpage
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- ArcGIS Pro 3.x with Network Analyst extension
- Python 3.x with arcpy (included with ArcGIS Pro)
- ArcGIS Pro conda environment: `arcgispro-py3`

### Data Requirements

Before running scripts, obtain the following:

1. **MTA GTFS Feed** — [Maryland Open Data / mta.maryland.gov](https://mta.maryland.gov/developer-resources)
2. **Census ACS 2020** — [data.census.gov](https://data.census.gov) — Tables: B02001, B03002, B08136, B08013, B08301, B08201, B17001, B01001, B18101, B16004, B05001, B25003, B25044, B19013
3. **OpenStreetMap** — [Geofabrik Maryland shapefile](https://download.geofabrik.de/north-america/us/maryland.html)
4. **Baltimore City Boundary** — [Baltimore City Open GIS Data](https://data.baltimorecity.gov)

### Running the Pipeline

Scripts must be executed in numbered order from the ArcGIS Pro Python console or Notebook interface:

```python
# Stages 01–07: Data preparation (run in order)
exec(open('scripts/01_project_data.py').read())
# ... through 07

# Stages 08–13: Analysis (independent of each other once 01–07 complete)
exec(open('scripts/08_gap_analysis.py').read())
# ... etc.
```

> **Note:** Script 14 (job access analysis) requires LEHD LODES 2020 employment data and is not yet implemented.

---

## 📐 Analytical Framework

The project applies the **FTA Title VI compliance framework** used by federal transit agencies:

```
Layer 1 — Who needs transit most?       →  Composite Equity Index (19 indicators)
Layer 2 — What service do they get?     →  GTFS coverage, frequency, connectivity
Layer 3 — What outcomes do they face?   →  Commute time burden, modal access
                                                    ↕
                              GAP = Layer 3 – Layer 1 disparity
```

---

## 📈 Statistical Methods

- **Significance threshold:** α = 0.05 (two-tailed)
- **T-tests:** Welch (unequal variance) throughout
- **Correlation:** Pearson r with p-value
- **FTA threshold:** 1.25× disparity ratio per Circular 4702.1B (2012)
- **Library:** `scipy.stats` (Python)

---

## 🔗 Links

| Resource | URL |
|---|---|
| 🗺 ArcGIS StoryMap | [arcg.is/zTrOO](https://arcg.is/zTrOO) |
| 🌐 ArcGIS Feature Service | [View on ArcGIS Online](https://services3.arcgis.com/f6DdLR4lY5RnYDuG/arcgis/rest/services/Baltimore_Transit_Equity/FeatureServer) |
| 🌍 Project Showcase | [View on GitHub Pages](https://joojo-stephens.github.io/Baltimore-Transit-Equity/) |
| 💼 LinkedIn | [linkedin.com/in/nathaniel-stephens1](https://linkedin.com/in/nathaniel-stephens1) |

---

## 📚 References

- Federal Transit Administration. (2012). *Title VI Requirements and Guidelines for Federal Transit Administration Recipients.* FTA Circular 4702.1B. U.S. DOT.
- Latshaw, M. and Jordan, S. (2021). *Transit Equity in Baltimore City.* Baltimore Transit Equity Coalition / Johns Hopkins Bloomberg School of Public Health.
- Maryland Transit Administration. (2024). *MTA GTFS Feed.* Retrieved from mta.maryland.gov.
- US Census Bureau. (2021). *American Community Survey 5-Year Estimates 2016–2020.* Washington, DC.
- Transportation Research Board. (2013). *TCRP Report 165: Transit Capacity and Quality of Service Manual (3rd ed.).* National Academies Press.

---

## 📄 License

This project is open for academic and research use. Please cite appropriately if building on this work.

---

*© 2026 Nathaniel K.A. Stephens · MSc Urban Transportation · Morgan State University*
