# ============================================================
# 01_gtfs_conversion.py
# Baltimore Transit Equity Analysis
# Convert GTFS text files to ArcGIS feature classes and tables
#
# Author:  Nathaniel K.A. Stephens
# Date:    March 2026
#
# Inputs:  Raw GTFS folders (5 feeds):
#          - mdotmta_gtfs_localbus
#          - mdotmta_gtfs_lightrail
#          - mdotmta_gtfs_metro
#          - mdotmta_gtfs_marc
#          - mdotmta_gtfs_commuterbus
#
# Outputs: Per feed in GTFS_Database.gdb:
#          - {Feed}_Stops_Pt         (feature class)
#          - {Feed}_Shapes_Ln        (feature class)
#          - {Feed}_Routes_Tbl       (table)
#          - {Feed}_Trips_Tbl        (table)
#          - {Feed}_StopTimes_Tbl    (table)
#          - {Feed}_Calendar_Tbl     (table)
#
#          Merged outputs:
#          - GTFS_AllStops_Merged_Pt
#          - GTFS_BusStops_Baltimore_Pt (clipped to Baltimore)
#          - GTFS_Routes_Baltimore_Ln   (clipped to Baltimore)
# ============================================================

import arcpy
import os
import csv

# ── PATHS ────────────────────────────────────────────────────
project_dir = r"C:\Users\kojoa\Documents\ArcGIS\Projects\MyProject"
gtfs_dir    = os.path.join(project_dir, "data", "gtfs")
gtfs_gdb    = os.path.join(project_dir, "GTFS_Database.gdb")
main_gdb    = os.path.join(project_dir, "MyProject.gdb")

# Coordinate system — NAD 1983 StatePlane Maryland FIPS 1900 US Feet
sr = arcpy.SpatialReference(2248)

arcpy.env.overwriteOutput = True

# ── GTFS FEED DEFINITIONS ────────────────────────────────────
feeds = {
    "LocalBus"    : {"folder": "mdotmta_gtfs_localbus",    "mode": "Local Bus"},
    "LightRail"   : {"folder": "mdotmta_gtfs_lightrail",   "mode": "Light Rail"},
    "Metro"       : {"folder": "mdotmta_gtfs_metro",       "mode": "Metro Subway"},
    "MARC"        : {"folder": "mdotmta_gtfs_marc",        "mode": "MARC Train"},
    "CommuterBus" : {"folder": "mdotmta_gtfs_commuterbus", "mode": "Commuter Bus"},
}

print("=" * 60)
print("GTFS CONVERSION — ALL 5 MTA MARYLAND FEEDS")
print("=" * 60)

all_stop_layers  = []
all_route_layers = []

for feed_name, feed_info in feeds.items():
    folder    = os.path.join(gtfs_dir, feed_info["folder"])
    mode_name = feed_info["mode"]

    print(f"\nProcessing: {feed_name} ({mode_name})")
    print("-" * 40)

    # ── Convert stops.txt to feature class ───────────────────
    stops_txt = os.path.join(folder, "stops.txt")
    stops_out = f"{gtfs_gdb}\\{feed_name}_Stops_Pt"

    if os.path.exists(stops_txt):
        stops_fc = arcpy.management.XYTableToPoint(
            in_table        = stops_txt,
            out_feature_class = stops_out,
            x_field         = "stop_lon",
            y_field         = "stop_lat",
            coordinate_system = arcpy.SpatialReference(4326)
        )
        # Project to EPSG 2248
        stops_proj = stops_out + "_Proj"
        arcpy.management.Project(stops_out, stops_proj, sr)
        arcpy.management.Delete(stops_out)
        arcpy.management.Rename(stops_proj, stops_out)

        # Add Transit_Mode field
        arcpy.management.AddField(stops_out, "Transit_Mode", "TEXT", field_length=50)
        arcpy.management.CalculateField(stops_out, "Transit_Mode", f'"{mode_name}"')

        count = int(arcpy.management.GetCount(stops_out)[0])
        print(f"  ✅ {feed_name}_Stops_Pt → {count} stops")
        all_stop_layers.append(stops_out)
    else:
        print(f"  ⚠️  stops.txt not found at {stops_txt}")

    # ── Convert routes.txt to table ──────────────────────────
    routes_txt = os.path.join(folder, "routes.txt")
    routes_out = f"{gtfs_gdb}\\{feed_name}_Routes_Tbl"
    if os.path.exists(routes_txt):
        arcpy.conversion.TableToTable(routes_txt, gtfs_gdb, f"{feed_name}_Routes_Tbl")
        count = int(arcpy.management.GetCount(routes_out)[0])
        print(f"  ✅ {feed_name}_Routes_Tbl → {count} rows")

    # ── Convert trips.txt to table ───────────────────────────
    trips_txt = os.path.join(folder, "trips.txt")
    if os.path.exists(trips_txt):
        arcpy.conversion.TableToTable(trips_txt, gtfs_gdb, f"{feed_name}_Trips_Tbl")
        print(f"  ✅ {feed_name}_Trips_Tbl created")

    # ── Convert stop_times.txt to table ──────────────────────
    st_txt = os.path.join(folder, "stop_times.txt")
    if os.path.exists(st_txt):
        arcpy.conversion.TableToTable(st_txt, gtfs_gdb, f"{feed_name}_StopTimes_Tbl")
        count = int(arcpy.management.GetCount(f"{gtfs_gdb}\\{feed_name}_StopTimes_Tbl")[0])
        print(f"  ✅ {feed_name}_StopTimes_Tbl → {count} rows")

    # ── Convert calendar.txt to table ────────────────────────
    cal_txt = os.path.join(folder, "calendar.txt")
    if os.path.exists(cal_txt):
        arcpy.conversion.TableToTable(cal_txt, gtfs_gdb, f"{feed_name}_Calendar_Tbl")
        print(f"  ✅ {feed_name}_Calendar_Tbl created")

    # ── Convert shapes.txt to polyline ───────────────────────
    shapes_txt = os.path.join(folder, "shapes.txt")
    if os.path.exists(shapes_txt):
        shapes_out = f"{gtfs_gdb}\\{feed_name}_Shapes_Ln"
        # Build shapes from point file
        shape_pts = f"{gtfs_gdb}\\{feed_name}_ShapePts_Temp"
        arcpy.management.XYTableToPoint(
            shapes_txt, shape_pts,
            x_field="shape_pt_lon",
            y_field="shape_pt_lat",
            coordinate_system=arcpy.SpatialReference(4326)
        )
        arcpy.management.PointsToLine(
            shape_pts, shapes_out,
            Line_Field="shape_id",
            Sort_Field="shape_pt_sequence"
        )
        arcpy.management.Project(shapes_out, shapes_out + "_Proj", sr)
        arcpy.management.Delete(shapes_out)
        arcpy.management.Rename(shapes_out + "_Proj", shapes_out)
        arcpy.management.Delete(shape_pts)

        # Add Transit_Mode
        arcpy.management.AddField(shapes_out, "Transit_Mode", "TEXT", field_length=50)
        arcpy.management.CalculateField(shapes_out, "Transit_Mode", f'"{mode_name}"')

        count = int(arcpy.management.GetCount(shapes_out)[0])
        print(f"  ✅ {feed_name}_Shapes_Ln → {count} shapes")
        all_route_layers.append(shapes_out)

# ── MERGE ALL STOPS ──────────────────────────────────────────
print(f"\nMerging all stops...")
all_stops_merged = f"{gtfs_gdb}\\GTFS_AllStops_Merged_Pt"
arcpy.management.Merge(all_stop_layers, all_stops_merged)
count = int(arcpy.management.GetCount(all_stops_merged)[0])
print(f"  ✅ GTFS_AllStops_Merged_Pt → {count} total stops")

# ── CLIP TO BALTIMORE ────────────────────────────────────────
print(f"\nClipping stops to Baltimore City boundary...")
baltimore_boundary = f"{main_gdb}\\Base\\Baltimore_City_Boundary"

if arcpy.Exists(baltimore_boundary):
    arcpy.analysis.Clip(
        in_features       = all_stops_merged,
        clip_features     = baltimore_boundary,
        out_feature_class = f"{gtfs_gdb}\\GTFS_BusStops_Baltimore_Pt"
    )
    count = int(arcpy.management.GetCount(
        f"{gtfs_gdb}\\GTFS_BusStops_Baltimore_Pt")[0])
    print(f"  ✅ GTFS_BusStops_Baltimore_Pt → {count} stops")
else:
    print(f"  ⚠️  Baltimore_City_Boundary not found")
    print(f"       Run 08_gap_analysis.py first to create it")
    print(f"       Then re-run this clip step")

# ── MERGE ALL ROUTES ─────────────────────────────────────────
if all_route_layers:
    print(f"\nMerging all route shapes...")
    all_routes_merged = f"{gtfs_gdb}\\GTFS_AllRoutes_Merged_Ln"
    arcpy.management.Merge(all_route_layers, all_routes_merged)

    if arcpy.Exists(baltimore_boundary):
        arcpy.analysis.Clip(
            in_features       = all_routes_merged,
            clip_features     = baltimore_boundary,
            out_feature_class = f"{gtfs_gdb}\\GTFS_Routes_Baltimore_Ln"
        )
        count = int(arcpy.management.GetCount(
            f"{gtfs_gdb}\\GTFS_Routes_Baltimore_Ln")[0])
        print(f"  ✅ GTFS_Routes_Baltimore_Ln → {count} routes")

# ── FINAL SUMMARY ─────────────────────────────────────────────
print(f"\n{'='*60}")
print("GTFS CONVERSION COMPLETE")
print(f"{'='*60}")

# Count by mode in final Baltimore stops layer
balt_stops = f"{gtfs_gdb}\\GTFS_BusStops_Baltimore_Pt"
if arcpy.Exists(balt_stops):
    modes = {}
    with arcpy.da.SearchCursor(balt_stops, ["Transit_Mode"]) as cursor:
        for row in cursor:
            mode = row[0] if row[0] else "Unknown"
            modes[mode] = modes.get(mode, 0) + 1
    print(f"\n  Stops in Baltimore by mode:")
    total = sum(modes.values())
    for mode, count in sorted(modes.items(), key=lambda x: x[1], reverse=True):
        print(f"  {mode:20} → {count:5} stops ({count/total*100:.1f}%)")
    print(f"  {'TOTAL':20} → {total:5} stops")

print(f"\n  Outputs in GTFS_Database.gdb:")
print(f"  → GTFS_AllStops_Merged_Pt")
print(f"  → GTFS_BusStops_Baltimore_Pt")
print(f"  → GTFS_Routes_Baltimore_Ln")
print(f"{'='*60}")
