"""GeoPandas Spatial Risk Overlay Prototype (EPSG:4326 -> EPSG:6933 Buffer & Spatial Join).

Applies cadastral/GIS spatial concepts (CRS projection, metric buffering, polygon/point overlay)
to map geocoded OSINT signals against maritime chokepoints and semiconductor supply-chain hubs.

Note: Spatial exposure is an auxiliary analytical signal; it does NOT override deterministic
Alert Levels or human review gates.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.geometry import Point

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSETS_GEOJSON = PROJECT_ROOT / "config" / "spatial" / "supply_chain_assets.geojson"
CANONICAL_JSON = PROJECT_ROOT / "data" / "automation" / "canonical_signals_latest.json"
OUT_DIR = PROJECT_ROOT / "data" / "spatial"

# Deterministic Gazetteer (lon, lat) in WGS84 (EPSG:4326)
PLACE_GAZETTEER: list[tuple[str, str, float, float]] = [
    (r"\bhormuz\b|호르무즈", "Strait of Hormuz", 56.35, 26.57),
    (r"\btaiwan\b|\btaipei\b|\btsmc\b|대만", "Taiwan / Hsinchu", 121.00, 24.78),
    (r"\bred sea\b|\bsuez\b|\bhouthi\b|\byemen\b|홍해|수에즈", "Red Sea / Bab el-Mandeb", 43.30, 12.60),
    (r"\bmalacca\b|\bsingapore\b|말라카", "Strait of Malacca", 102.25, 2.20),
    (r"\bpanama\b|파나마", "Panama Canal", -79.75, 9.08),
    (r"\biran\b|\btehran\b|이란", "Tehran, Iran", 51.39, 35.69),
    (r"\bisrael\b|\bgaza\b|\blebanon\b|\bsyria\b|이스라엘|가자", "Levant / Israel", 35.21, 31.77),
    (r"\bukraine\b|\bkyiv\b|\bblack sea\b|우크라이나", "Kyiv, Ukraine", 30.52, 50.45),
    (r"\brussia\b|\bmoscow\b|\bputin\b|\bbelarus\b|러시아", "Moscow, Russia", 37.62, 55.75),
    (r"\bkorea\b|\bseoul\b|\bpyongyang\b|\bsamsung\b|\bhynix\b|한국|북한", "Korean Peninsula", 127.00, 37.55),
    (r"\bjapan\b|\btokyo\b|\bkumamoto\b|일본", "Japan", 139.69, 35.69),
    (r"\bchina\b|\bbeijing\b|\bshanghai\b|중국", "Beijing, China", 116.40, 39.90),
    (r"\basml\b|\bnetherlands\b|\beurope\b|\beu\b|네덜란드|유럽", "Veldhoven, Netherlands", 5.41, 51.41),
    (r"\bmexico\b|\bvenezuela\b|\bbrazil\b|멕시코", "Mexico City", -99.13, 19.43),
    (r"\bunited states\b|\bu\.s\.\b|\bus\b|\bwashington\b|\bnvidia\b|\bchips act\b|미국", "Washington / US Tech", -112.07, 33.45),
]

MACRO_REGION_CENTROIDS: dict[str, tuple[str, float, float]] = {
    "EAST_ASIA": ("East Asia Centroid", 121.5, 31.2),
    "MIDDLE_EAST": ("Middle East Centroid", 46.5, 27.5),
    "EASTERN_EUROPE": ("Eastern Europe Centroid", 32.0, 50.0),
    "WESTERN_EUROPE": ("Western Europe Centroid", 5.4, 51.4),
    "NORTH_AMERICA": ("North America Centroid", -105.0, 36.0),
    "LATIN_AMERICA": ("Latin America Centroid", -80.0, 9.5),
    "SOUTHEAST_ASIA": ("Southeast Asia Centroid", 103.8, 1.35),
}


def geocode_signal(sig: dict[str, Any]) -> tuple[str, float, float, str] | None:
    title = str(sig.get("representative_title") or sig.get("canonical_title") or "")
    for pattern, place_name, lon, lat in PLACE_GAZETTEER:
        if re.search(pattern, title, flags=re.IGNORECASE):
            return place_name, lon, lat, "title_gazetteer"

    where_raw = str((sig.get("event_tuple") or {}).get("where") or "")
    for token in [w.strip() for w in where_raw.split(",") if w.strip()]:
        if token in MACRO_REGION_CENTROIDS:
            place_name, lon, lat = MACRO_REGION_CENTROIDS[token]
            return place_name, lon, lat, "macro_region_centroid"
    return None


def run_spatial_overlay(buffer_km: float = 300.0) -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    assets_gdf = gpd.read_file(ASSETS_GEOJSON).to_crs("EPSG:4326")

    raw = json.loads(CANONICAL_JSON.read_text(encoding="utf-8"))
    signals = raw.get("signals", [])

    sig_records: list[dict[str, Any]] = []
    for s in signals:
        geo = geocode_signal(s)
        if not geo:
            continue
        place_name, lon, lat, geo_method = geo
        sig_records.append({
            "signal_id": s.get("signal_id") or s.get("cluster_id"),
            "title": str(s.get("representative_title") or "")[:160],
            "purity_tier": s.get("purity_tier", "UNVERIFIED"),
            "unique_sources": int(s.get("unique_sources_count") or 1),
            "place_name": place_name,
            "geo_method": geo_method,
            "geometry": Point(lon, lat),
        })

    if not sig_records:
        raise RuntimeError("No geocodable signals found in canonical_signals_latest.json")

    signals_gdf = gpd.GeoDataFrame(sig_records, crs="EPSG:4326")

    # Project to EPSG:6933 (World Cylindrical Equal Area, meters) for distortion-free metric buffering
    assets_m = assets_gdf.to_crs("EPSG:6933")
    signals_m = signals_gdf.to_crs("EPSG:6933")

    buffers_m = signals_m.copy()
    buffers_m["geometry"] = signals_m.geometry.buffer(buffer_km * 1000.0)

    joined = gpd.sjoin(assets_m, buffers_m, how="left", predicate="intersects")

    asset_summaries: list[dict[str, Any]] = []
    for idx, asset_row in assets_m.iterrows():
        asset_id = asset_row["asset_id"]
        sub = joined[joined["asset_id"] == asset_id].dropna(subset=["signal_id"])
        overlap_cnt = len(sub)
        tier1_cnt = int((sub["purity_tier"] == "TIER_1_CORROBORATED").sum()) if overlap_cnt else 0

        # Exact metric nearest distance (km) in EPSG:6933
        nearest_km = round(float(signals_m.geometry.distance(asset_row.geometry).min()) / 1000.0, 1)

        if tier1_cnt >= 3 or overlap_cnt >= 10:
            exposure = "HIGH"
        elif overlap_cnt >= 3:
            exposure = "MODERATE"
        elif overlap_cnt >= 1:
            exposure = "LOW"
        else:
            exposure = "NONE"

        assets_gdf.loc[idx, "overlapping_signals"] = overlap_cnt
        assets_gdf.loc[idx, "tier1_overlapping"] = tier1_cnt
        assets_gdf.loc[idx, "nearest_signal_km"] = nearest_km
        assets_gdf.loc[idx, "spatial_exposure_level"] = exposure

        asset_summaries.append({
            "asset_id": asset_id,
            "name": asset_row["name"],
            "asset_type": asset_row["asset_type"],
            "sector": asset_row["sector"],
            "overlapping_signals": overlap_cnt,
            "tier1_overlapping": tier1_cnt,
            "nearest_signal_km": nearest_km,
            "spatial_exposure_level": exposure,
        })

    assets_out = OUT_DIR / "spatial_assets_exposure.geojson"
    signals_out = OUT_DIR / "spatial_signals_latest.geojson"
    summary_out = OUT_DIR / "spatial_exposure_summary.json"

    assets_gdf.to_file(assets_out, driver="GeoJSON")
    signals_gdf.to_file(signals_out, driver="GeoJSON")

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "geopandas_version": gpd.__version__,
        "crs_input": "EPSG:4326",
        "crs_metric_analysis": "EPSG:6933",
        "buffer_km": buffer_km,
        "total_canonical_signals": len(signals),
        "geocoded_signals": len(signals_gdf),
        "assets": sorted(asset_summaries, key=lambda x: (-x["overlapping_signals"], x["nearest_signal_km"])),
    }
    summary_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run GeoPandas spatial risk overlay prototype.")
    parser.add_argument("--buffer-km", type=float, default=300.0, help="Metric buffer radius in km (EPSG:6933).")
    args = parser.parse_args()

    summary = run_spatial_overlay(buffer_km=args.buffer_km)
    print(f"=== GeoPandas {summary['geopandas_version']} Spatial Overlay (CRS: {summary['crs_metric_analysis']}, Buffer: {summary['buffer_km']}km) ===")
    print(f"Geocoded signals: {summary['geocoded_signals']} / {summary['total_canonical_signals']}")
    for a in summary["assets"]:
        print(
            f"- {a['asset_id']:20s} | {a['spatial_exposure_level']:8s} | "
            f"overlap={a['overlapping_signals']:3d} (T1={a['tier1_overlapping']:2d}) | "
            f"nearest={a['nearest_signal_km']:7.1f} km | {a['name']}"
        )


if __name__ == "__main__":
    main()
