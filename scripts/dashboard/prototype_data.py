"""Shared loader for integrated early-warning & multi-judge prototype dashboards."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SIGNAL_GAP_PATH = PROJECT_ROOT / "data" / "signal_gap" / "signal_gap_analysis.json"
MULTI_JUDGE_PATH = PROJECT_ROOT / "data" / "validation" / "multi_judge_audit_latest.json"
CANONICAL_PATH = PROJECT_ROOT / "data" / "automation" / "canonical_signals_latest.json"
CANONICAL_HIGH_PURITY_PATH = (
    PROJECT_ROOT / "data" / "automation" / "canonical_signals_high_purity_latest.json"
)
SPATIAL_ASSETS_PATH = PROJECT_ROOT / "data" / "spatial" / "spatial_assets_exposure.geojson"
SPATIAL_SIGNALS_PATH = PROJECT_ROOT / "data" / "spatial" / "spatial_signals_latest.geojson"
SPATIAL_SUMMARY_PATH = PROJECT_ROOT / "data" / "spatial" / "spatial_exposure_summary.json"

# 전처리 event_tuple의 표기 규칙. 누락·미확정 값은 대시보드에서 결측으로 처리한다.
_ISO_8601_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?$"
)
_METRIC_KIND_KO = {
    "currency_price": "금액",
    "percentage": "비율",
    "quantity_unit": "물량·단위",
}
_UNRESOLVED_ACTOR_KEYWORDS = ("미상", "unspecified", "unknown", "multiple sources")
_EMPTY_TOKENS = {"", "-", "none", "null", "n/a"}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_signal_gap() -> dict[str, Any]:
    return _read_json(SIGNAL_GAP_PATH)


def load_multi_judge_audit() -> dict[str, Any]:
    return _read_json(MULTI_JUDGE_PATH)


def load_canonical_summary() -> dict[str, Any]:
    data = _read_json(CANONICAL_PATH)
    clusters = data.get("signals") or data.get("clusters") or data.get("items") or []
    return {
        "available": bool(data),
        "generated_at": data.get("generated_at") or data.get("timestamp") or "",
        "cluster_count": len(clusters) if isinstance(clusters, list) else 0,
    }


def _signals_of(data: dict[str, Any]) -> list[dict[str, Any]]:
    clusters = data.get("signals") or data.get("clusters") or data.get("items") or []
    return [c for c in clusters if isinstance(c, dict)] if isinstance(clusters, list) else []


def _is_blank(value: str) -> bool:
    return value.strip().lower() in _EMPTY_TOKENS


def _is_iso8601(value: str) -> bool:
    return not _is_blank(value) and bool(_ISO_8601_RE.match(value.strip()))


def _actor_unresolved(value: str) -> bool:
    if _is_blank(value):
        return True
    text = value.strip()
    return any(k in text.lower() for k in _UNRESOLVED_ACTOR_KEYWORDS) or "미상" in text


def format_event_metrics(raw: Any) -> list[str]:
    """`event_tuple.extracted_metrics`를 사람이 읽는 문자열로 바꾼다. 비정형 항목은 버린다."""
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        if isinstance(item, dict):
            value = str(item.get("value") or "").strip()
            if _is_blank(value):
                continue
            kind = str(item.get("type") or "").strip()
            out.append(f"{value} · {_METRIC_KIND_KO.get(kind, kind)}" if kind else value)
        else:
            value = str(item or "").strip()
            if not _is_blank(value):
                out.append(value)
    return out


def load_canonical_refinement(path: Path = CANONICAL_PATH) -> dict[str, Any]:
    """전처리 세밀화(행위자·ISO-8601 시점·정량 수치)의 실제 커버리지를 클러스터 단위로 집계한다."""
    data = _read_json(path)
    signals = _signals_of(data)
    who_resolved = when_iso = metric_clusters = metric_values = 0
    for signal in signals:
        tuple_ = signal.get("event_tuple") or {}
        if not _actor_unresolved(str(tuple_.get("who") or "")):
            who_resolved += 1
        if _is_iso8601(str(tuple_.get("when") or "")):
            when_iso += 1
        metrics = format_event_metrics(tuple_.get("extracted_metrics"))
        if metrics:
            metric_clusters += 1
            metric_values += len(metrics)

    total = len(signals)

    def pct(part: int) -> float:
        return round(part / total * 100, 1) if total else 0.0

    return {
        "available": bool(data),
        "file_name": path.name,
        "generated_at": str(data.get("generated_at") or ""),
        "purity_mode": str(data.get("purity_mode") or ""),
        "cluster_count": total,
        "tuple_count": sum(1 for s in signals if s.get("event_tuple")),
        "who_resolved": who_resolved,
        "who_unresolved": total - who_resolved,
        "who_resolved_pct": pct(who_resolved),
        "when_iso": when_iso,
        "when_iso_pct": pct(when_iso),
        "metric_clusters": metric_clusters,
        "metric_values": metric_values,
        "metric_cluster_pct": pct(metric_clusters),
    }


def build_event_tuple_evidence(
    limit: int = 12, path: Path = CANONICAL_HIGH_PURITY_PATH
) -> list[dict[str, Any]]:
    """High-Purity 클러스터의 5W1H 튜플 근거 행.

    값이 없으면 빈 문자열로 둔다 — 결측을 "확인 필요"로 바꾸는 책임은 렌더러에 있다.
    """
    rows: list[dict[str, Any]] = []
    for signal in _signals_of(_read_json(path)):
        tuple_ = signal.get("event_tuple") or {}
        when = str(tuple_.get("when") or "")
        who = str(tuple_.get("who") or "")
        rows.append({
            "title": str(signal.get("canonical_title") or signal.get("representative_title") or ""),
            "who": who,
            "who_unresolved": _actor_unresolved(who),
            "action": str(tuple_.get("action") or ""),
            "target": str(tuple_.get("target") or ""),
            "where": str(tuple_.get("where") or ""),
            "when": when,
            "when_normalized": _is_iso8601(when),
            "metrics": format_event_metrics(tuple_.get("extracted_metrics")),
            "threat_severity": str(tuple_.get("threat_severity") or ""),
            "supply_chain_tags": [str(t) for t in (signal.get("supply_chain_tags") or []) if t],
            "chokepoints": [str(c) for c in (signal.get("chokepoints") or []) if c],
            "verification_state": str(signal.get("verification_state") or ""),
            "purity_tier": str(signal.get("purity_tier") or ""),
            "cluster_size": int(signal.get("cluster_size") or 0),
            "unique_sources_count": int(signal.get("unique_sources_count") or 0),
            "primary_language": str(signal.get("primary_language") or ""),
            "is_cross_lingual": bool(signal.get("is_cross_lingual")),
            "url": str(signal.get("url") or ""),
        })
    # 정량 수치를 확보한 클러스터를 우선하되, 근거 두께(출처 수 → 기사 수)를 2·3순위로 본다.
    rows.sort(key=lambda r: (bool(r["metrics"]), r["unique_sources_count"], r["cluster_size"]),
              reverse=True)
    return rows[:limit]


def build_integrated_region_rows() -> list[dict[str, Any]]:
    """Merge signal_gap_analysis.json and multi_judge_audit_latest.json by region."""
    sg = load_signal_gap()
    audit = load_multi_judge_audit()
    audit_by_region = {r.get("region"): r for r in audit.get("results", []) if r.get("region")}

    regions = list(sg.keys()) or list(audit_by_region.keys())
    rows: list[dict[str, Any]] = []
    for reg in regions:
        s_item = sg.get(reg, {})
        a_item = audit_by_region.get(reg, {})
        tev1 = a_item.get("tev1", {})
        gemma = a_item.get("gemma2", {})
        critic = a_item.get("deepseek_r1", {})
        presiding = a_item.get("presiding_judge", {})
        nim = a_item.get("nim_escalation", {})
        gov = a_item.get("governance", {})

        rows.append({
            "region": reg,
            "alert_level_ko": s_item.get("alert_level") or a_item.get("formula_alert_ko") or "-",
            "formula_alert_en": a_item.get("formula_alert_en") or "-",
            "risk_signal_score": s_item.get("risk_signal_score", a_item.get("risk_signal_score", 0.0)),
            "signal_gap_score": s_item.get("signal_gap_score", 0.0),
            "evidence_coverage": s_item.get("evidence_coverage", 0.0),
            "source_diversity": s_item.get("source_diversity", 0),
            "tev1_verdict": tev1.get("stage_verdict") or tev1.get("status") or "-",
            "gemma2_verdict": gemma.get("worst_verdict") or gemma.get("status") or "-",
            "critic_model": critic.get("model_id") or "-",
            "critic_verdict": critic.get("inference_verdict") or critic.get("status") or "-",
            "critic_note": critic.get("note") or "",
            "presiding_model": presiding.get("model_id") or "-",
            "presiding_decision": presiding.get("recommended_decision") or presiding.get("status") or "-",
            "presiding_dispute": presiding.get("key_dispute") or "",
            "presiding_rationale": presiding.get("ruling_rationale") or "",
            "nim_model": nim.get("model_id") or "-",
            "nim_status": nim.get("status") or "-",
            "nim_fact": nim.get("fact_verdict") or "-",
            "nim_inference": nim.get("inference_verdict") or "-",
            "nim_leap": nim.get("leap_type") or "-",
            "nim_note": nim.get("note") or nim.get("error") or "",
            "triggers": gov.get("triggers", []),
            "needs_human_review": bool(gov.get("needs_human_review", False)),
            "narrative": s_item.get("narrative_differences") or s_item.get("narrative_differences_en") or "",
            "evidence_phrases": s_item.get("evidence_phrases") or [],
        })
    return rows


def _feature_center(geometry: dict[str, Any]) -> tuple[float, float] | None:
    """Return (lon, lat) center for Point or Polygon GeoJSON geometry."""
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if not coords:
        return None
    if gtype == "Point" and len(coords) >= 2:
        return float(coords[0]), float(coords[1])
    if gtype == "Polygon" and coords and coords[0]:
        ring = coords[0]
        lons = [float(p[0]) for p in ring if len(p) >= 2]
        lats = [float(p[1]) for p in ring if len(p) >= 2]
        if lons and lats:
            return round(sum(lons) / len(lons), 4), round(sum(lats) / len(lats), 4)
    return None


def load_spatial_overlay() -> dict[str, Any]:
    """Load GeoPandas spatial risk overlay outputs for dashboard visualization.

    보조 지표 전용 로더: 공간 노출도(spatial_exposure_level)는 시각화·해석 보조 신호이며
    결정론적 경보 산식(calculate_alert_assessment)에 절대 연결하지 않는다.
    """
    summary = _read_json(SPATIAL_SUMMARY_PATH)
    assets_geo = _read_json(SPATIAL_ASSETS_PATH)
    signals_geo = _read_json(SPATIAL_SIGNALS_PATH)

    asset_features = assets_geo.get("features") if isinstance(assets_geo.get("features"), list) else []
    signal_features = signals_geo.get("features") if isinstance(signals_geo.get("features"), list) else []

    asset_rows: list[dict[str, Any]] = []
    for feat in asset_features:
        props = feat.get("properties") or {}
        geom = feat.get("geometry") or {}
        center = _feature_center(geom)
        asset_rows.append({
            "asset_id": str(props.get("asset_id") or ""),
            "name": str(props.get("name") or ""),
            "asset_type": str(props.get("asset_type") or ""),
            "sector": str(props.get("sector") or ""),
            "region": str(props.get("region") or ""),
            "overlapping_signals": int(float(props.get("overlapping_signals") or 0)),
            "tier1_overlapping": int(float(props.get("tier1_overlapping") or 0)),
            "nearest_signal_km": round(float(props.get("nearest_signal_km") or 0.0), 1),
            "spatial_exposure_level": str(props.get("spatial_exposure_level") or "NONE"),
            "geometry_type": str(geom.get("type") or ""),
            "lon": center[0] if center else 0.0,
            "lat": center[1] if center else 0.0,
        })

    asset_rows.sort(key=lambda r: (-r["overlapping_signals"], r["nearest_signal_km"], r["asset_id"]))

    # Aggregate geocoded signals by coordinate + place_name so overlapping points render cleanly
    cluster_map: dict[tuple[str, float, float], dict[str, Any]] = {}
    for feat in signal_features:
        props = feat.get("properties") or {}
        geom = feat.get("geometry") or {}
        center = _feature_center(geom)
        if not center:
            continue
        lon, lat = round(center[0], 4), round(center[1], 4)
        place = str(props.get("place_name") or "Unknown")
        key = (place, lon, lat)
        if key not in cluster_map:
            cluster_map[key] = {
                "place_name": place,
                "lon": lon,
                "lat": lat,
                "geo_method": str(props.get("geo_method") or ""),
                "signal_count": 0,
                "tier1_count": 0,
                "tier2_count": 0,
                "tier3_count": 0,
                "sample_titles": [],
            }
        bucket = cluster_map[key]
        bucket["signal_count"] += 1
        tier = str(props.get("purity_tier") or "")
        if tier == "TIER_1_CORROBORATED":
            bucket["tier1_count"] += 1
        elif tier == "TIER_2_VERIFIED_ENTITY":
            bucket["tier2_count"] += 1
        else:
            bucket["tier3_count"] += 1
        title = str(props.get("title") or "").strip()
        if title and len(bucket["sample_titles"]) < 4 and title not in bucket["sample_titles"]:
            bucket["sample_titles"].append(title[:110])

    signal_clusters = sorted(
        cluster_map.values(),
        key=lambda c: (-c["tier1_count"], -c["signal_count"], c["place_name"]),
    )

    available = bool(asset_features)
    return {
        "available": available,
        "generated_at": str(summary.get("generated_at") or ""),
        "geopandas_version": str(summary.get("geopandas_version") or ""),
        "crs_input": str(summary.get("crs_input") or "EPSG:4326"),
        "crs_metric_analysis": str(summary.get("crs_metric_analysis") or "EPSG:6933"),
        "buffer_km": float(summary.get("buffer_km") or 300.0),
        "total_canonical_signals": int(summary.get("total_canonical_signals") or 0),
        "geocoded_signals": int(summary.get("geocoded_signals") or len(signal_features)),
        "assets_geojson": assets_geo if available else {"type": "FeatureCollection", "features": []},
        "signals_geojson": signals_geo if signal_features else {"type": "FeatureCollection", "features": []},
        "asset_rows": asset_rows,
        "signal_clusters": signal_clusters,
    }
