import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

_DB_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "db"
if str(_DB_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_DB_SCRIPTS_DIR))
from db_conn import get_connection as get_unified_connection, read_sql_df  # noqa: E402

try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ModuleNotFoundError:
    px = None
    go = None
    HAS_PLOTLY = False

try:
    import pydeck as pdk
    HAS_PYDECK = True
except ModuleNotFoundError:
    pdk = None
    HAS_PYDECK = False

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parents[1]
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from prototype_data import (  # noqa: E402
    CANONICAL_HIGH_PURITY_PATH,
    CANONICAL_PATH,
    build_event_tuple_evidence,
    build_integrated_region_rows,
    load_canonical_refinement,
    load_canonical_summary,
    load_multi_judge_audit,
    load_spatial_overlay,
)

load_dotenv()

st.set_page_config(
    page_title="글로벌 조기경보 통합 프로토타입 | Signal Gap",
    page_icon="🚨",
    layout="wide",
)


@st.cache_resource
def init_connection():
    return get_unified_connection()


def _run_prototype_script(args: list[str], label: str) -> None:
    with st.spinner(f"{label} 실행 중..."):
        proc = subprocess.run(
            [sys.executable, *args],
            cwd=str(_PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    if proc.returncode == 0:
        st.sidebar.success(f"{label} 완료")
        st.cache_data.clear()
        st.rerun()
    else:
        st.sidebar.error(f"{label} 실패 (code={proc.returncode})")
        if proc.stderr:
            st.sidebar.code(proc.stderr[-600:])


# --- SIDEBAR: PROTOTYPE CONTROLS ---
st.sidebar.header("⚡ 통합 프로토타입 제어판")
st.sidebar.caption("수집된 최신 신호를 기준으로 전처리·검증단·대시보드를 즉시 갱신합니다.")
if st.sidebar.button("🔄 빠른 프로토타입 새로고침", use_container_width=True):
    _run_prototype_script(["scripts/run_pipeline.py", "--prototype-refresh"], "빠른 프로토타입 새로고침")
if st.sidebar.button("🛡️ 검증단 재실행 (로컬 3심제)", use_container_width=True):
    _run_prototype_script(["scripts/validation/run_multi_judge_audit.py"], "로컬 3심제 검증단")
if st.sidebar.button("🌐 정적 HTML 대시보드 재생성", use_container_width=True):
    _run_prototype_script(["scripts/dashboard/generate_dashboard_v2.py"], "HTML 대시보드 재생성")
if st.sidebar.button("🗺️ GIS 공간 중첩 재실행", use_container_width=True):
    _run_prototype_script(["scripts/analysis/spatial_risk_overlay.py"], "GIS 공간 리스크 중첩")

canonical_info = load_canonical_summary()
if canonical_info.get("available"):
    st.sidebar.info(f"전처리 클러스터: {canonical_info['cluster_count']}건")

spatial_sidebar = load_spatial_overlay()
if spatial_sidebar.get("available"):
    st.sidebar.info(
        f"GIS 지오코딩: {spatial_sidebar['geocoded_signals']}/{spatial_sidebar['total_canonical_signals']}건 "
        f"({int(spatial_sidebar['buffer_km'])}km)"
    )

# --- HEADER ---
st.title("🚨 글로벌 조기경보 통합 프로토타입 (Early-Warning Control Tower)")
st.markdown(
    "**End-to-End 통합 뷰:** 전처리(5W1H) → 3-Tier 경보 산식 → 로컬 3심제(`tev1`·`Gemma2`·`Nemotron-3-Nano`) → `550B Ultra` 2차 감사 → GIS 공간 중첩 → MySQL 시계열 지표를 한 화면에서 확인합니다."
)

# --- TAB LAYOUT ---
tab_integrated, tab_spatial, tab_mysql = st.tabs(
    ["🛡️ 통합 경보 · 검증단 관제", "🗺️ GIS 공간 리스크 지도", "📊 MySQL 시계열 괴리 지표"]
)

with tab_integrated:
    rows = build_integrated_region_rows()
    audit_meta = load_multi_judge_audit()

    if not rows:
        st.warning("아직 `signal_gap_analysis.json` 또는 `multi_judge_audit_latest.json` 산출물이 없습니다.")
    else:
        warning_cnt = sum(1 for r in rows if r["formula_alert_en"] in {"WARNING", "CRITICAL"})
        review_cnt = sum(1 for r in rows if r["needs_human_review"])
        nim_ok_cnt = sum(1 for r in rows if r["nim_status"] == "ok")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("감시 권역", f"{len(rows)} 개")
        c2.metric("⚠️ 경보/고경보 권역", f"{warning_cnt} 건")
        c3.metric("👤 사람 검수 대기 (T1~T8)", f"{review_cnt} 건")
        c4.metric("🧠 550B Ultra 감사 완료", f"{nim_ok_cnt} 건")

        table_df = pd.DataFrame([
            {
                "권역": r["region"],
                "공식 경보": f"{r['alert_level_ko']} ({r['formula_alert_en']})",
                "리스크 점수": r["risk_signal_score"],
                "tev1": r["tev1_verdict"],
                "Gemma2": r["gemma2_verdict"],
                "Nemotron-3-Nano": r["critic_verdict"],
                "Mistral 재판관": r["presiding_decision"],
                "550B Ultra (NIM)": (
                    f"{r['nim_fact']} / {r['nim_inference']}"
                    if r["nim_status"] == "ok"
                    else r["nim_status"]
                ),
                "트리거": ", ".join(r["triggers"]) or "-",
            }
            for r in rows
        ])
        st.dataframe(table_df, use_container_width=True, hide_index=True)

        if audit_meta.get("generated_at"):
            st.caption(f"최근 멀티저지 감사 시각: {audit_meta['generated_at']}")

        st.subheader("🔎 권역별 근거 · 2차 감사 상세")
        selected_region = st.selectbox("상세 확인할 권역 선택", [r["region"] for r in rows])
        sel = next(r for r in rows if r["region"] == selected_region)

        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("**요약 브리핑 (`signal_gap_analysis`)**")
            st.write(sel["narrative"] or "요약 없음")
            st.markdown("**핵심 근거 구문**")
            for idx, ev in enumerate(sel["evidence_phrases"], 1):
                st.markdown(f"- `E-{idx:02d}` {ev}")
        with col_r:
            st.markdown(f"**로컬 비평가 메모 (`{sel['critic_model']}`)**")
            st.info(sel["critic_note"] or "메모 없음")
            st.markdown(f"**재판관 판결 (`{sel['presiding_model']}` · `{sel['presiding_decision']}`)**")
            if sel["presiding_rationale"] or sel["presiding_dispute"]:
                st.write(f"**핵심 쟁점:** {sel['presiding_dispute'] or '-'}")
                st.caption(sel["presiding_rationale"])
            else:
                st.caption("재판관 판결 없음")
            st.markdown(f"**550B Ultra 2차 감사 (`{sel['nim_model']}` · `{sel['nim_status']}`)**")
            if sel["nim_status"] == "ok":
                st.warning(
                    f"사실: `{sel['nim_fact']}` | 추론: `{sel['nim_inference']}` | 비약: `{sel['nim_leap']}`\n\n"
                    f"{sel['nim_note']}"
                )
            elif sel["nim_note"]:
                st.error(sel["nim_note"])
            else:
                st.caption("NIM 2차 감사 미실행 (`--nim-escalate` 필요)")

    # --- 5W1H 이벤트 튜플 · 정량 근거 (전처리 세밀화 반영, 표시 전용) ---
    st.divider()
    st.subheader("🧬 5W1H 이벤트 튜플 · 정량 근거")
    st.caption(
        "`event_tuple`의 행위자(who)·시점(when)·정량 수치(extracted_metrics)는 전처리 추출 스냅샷입니다. "
        "경보를 확정하는 근거가 아니며 Risk Signal Score·Alert Level 산식에는 사용되지 않습니다. "
        "근거가 없는 항목은 경보로 승격하지 않고 '확인 필요'로 표시합니다."
    )
    std_ref = load_canonical_refinement(CANONICAL_PATH)
    high_ref = load_canonical_refinement(CANONICAL_HIGH_PURITY_PATH)
    if not high_ref.get("available"):
        st.warning(
            "High-Purity 전처리 산출물이 없습니다 — 전처리 세션에서 "
            "`canonical_signals_high_purity_latest.json`을 생성한 뒤 새로고침하세요."
        )

    def _shown(info: dict, text: str) -> str:
        return text if info.get("available") else "확인 필요"

    t1, t2, t3, t4 = st.columns(4)
    t1.metric("High-Purity 클러스터", _shown(high_ref, f"{high_ref['cluster_count']} 건"),
              f"Standard {std_ref['cluster_count']} 건" if std_ref.get("available") else None)
    t2.metric("행위자(who) 확인", _shown(high_ref, f"{high_ref['who_resolved_pct']}%"),
              f"미상 {high_ref['who_unresolved']}건" if high_ref.get("available") else None)
    t3.metric("when ISO-8601 정제", _shown(high_ref, f"{high_ref['when_iso_pct']}%"),
              f"{high_ref['when_iso']}/{high_ref['cluster_count']}건 정규화" if high_ref.get("available") else None)
    t4.metric("정량 수치 확보", _shown(high_ref, f"{high_ref['metric_values']} 건"),
              f"{high_ref['metric_clusters']}개 클러스터" if high_ref.get("available") else None)

    evidence_rows = build_event_tuple_evidence(limit=20)
    if evidence_rows:
        st.dataframe(
            pd.DataFrame([
                {
                    "이벤트": r["title"][:90],
                    "행위자(who)": "확인 필요" if r["who_unresolved"] else (r["who"] or "확인 필요"),
                    "행위": r["action"] or "확인 필요",
                    "대상": r["target"] or "확인 필요",
                    "시점(when)": (r["when"] or "확인 필요") + ("" if r["when_normalized"] or not r["when"] else " (원문 표기)"),
                    "정량 수치(extracted_metrics)": " · ".join(r["metrics"]) or "정량 수치 확인 필요",
                    "검증 상태": r["verification_state"] or "확인 필요",
                    "전처리 심각도": r["threat_severity"] or "확인 필요",
                    "출처": r["unique_sources_count"],
                    "언어": r["primary_language"] + (" · cross-lingual" if r["is_cross_lingual"] else ""),
                }
                for r in evidence_rows
            ]),
            use_container_width=True,
            hide_index=True,
        )
        st.caption("전처리 심각도는 문구 규칙 기반 잠정 판정입니다. `UNVERIFIED` 행은 원문 링크 확인 후 검토 후보로만 다룹니다.")
    else:
        st.info("표시할 이벤트 튜플 근거가 없습니다 — '확인 필요' 상태입니다.")

with tab_spatial:
    spatial = load_spatial_overlay()
    st.subheader("🗺️ GIS · 공급망 공간 리스크 중첩 지도 (5대 해협 · 6대 반도체/희토류 거점)")
    st.caption(
        "GeoPandas (`EPSG:4326 → EPSG:6933` 등적 미터 투영) 기반 300km 버퍼 중첩(`gpd.sjoin`) 및 최단거리 산출 결과입니다. "
        "**공간 노출도(`spatial_exposure_level`)는 보조 지표**이며 결정론적 경보 산식(`calculate_alert_assessment`)에는 반영되지 않습니다."
    )

    if not spatial.get("available"):
        st.warning(
            "공간 중첩 산출물이 없습니다. 사이드바의 **'🗺️ GIS 공간 중첩 재실행'** 버튼 또는 "
            "`python scripts/analysis/spatial_risk_overlay.py`를 실행하세요."
        )
    else:
        asset_rows = spatial["asset_rows"]
        signal_clusters = spatial["signal_clusters"]
        buffer_km = spatial["buffer_km"]
        high_cnt = sum(1 for a in asset_rows if a["spatial_exposure_level"] == "HIGH")
        total_overlap = sum(a["overlapping_signals"] for a in asset_rows)
        total_t1 = sum(a["tier1_overlapping"] for a in asset_rows)
        geo_pct = (
            round(spatial["geocoded_signals"] / spatial["total_canonical_signals"] * 100, 1)
            if spatial["total_canonical_signals"]
            else 0.0
        )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric(
            "지오코딩 신호",
            f"{spatial['geocoded_signals']} / {spatial['total_canonical_signals']} 건",
            f"커버리지 {geo_pct}%",
        )
        m2.metric("HIGH 노출 자산 (보조)", f"{high_cnt} / {len(asset_rows)} 개")
        m3.metric(f"{int(buffer_km)}km 버퍼 중첩", f"{total_overlap} 건", f"Tier-1 중첩 {total_t1}건")
        m4.metric(
            "GIS 투영좌표계",
            spatial["crs_metric_analysis"],
            f"GeoPandas {spatial['geopandas_version'] or '-'}",
        )

        # Interactive focus & layer controls
        focus_options = {"🌍 전체 글로벌 뷰": (24.0, 55.0, 1.6)}
        for a in asset_rows:
            zoom_v = 4.6 if a["asset_type"] == "maritime_chokepoint" else 5.5
            focus_options[f"{a['name']} [{a['spatial_exposure_level']}]"] = (a["lat"], a["lon"], zoom_v)

        ctrl_col1, ctrl_col2 = st.columns([1.4, 2.2])
        with ctrl_col1:
            selected_focus = st.selectbox("지도 포커스 이동", list(focus_options.keys()))
        with ctrl_col2:
            st.markdown("<div style='height:26px;'></div>", unsafe_allow_html=True)
            lc1, lc2, lc3, lc4 = st.columns(4)
            show_chokepoints = lc1.checkbox("⚓ 해협 폴리곤", value=True)
            show_hubs = lc2.checkbox("🔬 반도체 거점", value=True)
            show_buffers = lc3.checkbox(f"⭕ {int(buffer_km)}km 반경", value=True)
            show_signals = lc4.checkbox("📡 OSINT 신호", value=True)

        view_lat, view_lon, view_zoom = focus_options[selected_focus]

        def _exposure_rgba(lvl: str, alpha: int = 160) -> list[int]:
            if lvl == "HIGH":
                return [239, 68, 68, alpha]
            if lvl == "MODERATE":
                return [245, 158, 11, alpha]
            if lvl == "LOW":
                return [56, 189, 248, alpha]
            return [148, 163, 184, alpha]

        if HAS_PYDECK:
            layers = []

            # 1) 5대 해협 폴리곤 (GeoJsonLayer)
            if show_chokepoints:
                poly_features = []
                for feat in spatial["assets_geojson"].get("features", []):
                    if (feat.get("geometry") or {}).get("type") != "Polygon":
                        continue
                    props = dict(feat.get("properties") or {})
                    lvl = str(props.get("spatial_exposure_level") or "NONE")
                    props["fill_rgba"] = _exposure_rgba(lvl, 105 if lvl == "HIGH" else 70)
                    props["line_rgba"] = _exposure_rgba(lvl, 230)
                    props["tooltip_title"] = f"⚓ {props.get('name', '-')}"
                    props["tooltip_detail"] = (
                        f"노출도(보조): {lvl} | 중첩: {int(float(props.get('overlapping_signals') or 0))}건 "
                        f"(T1: {int(float(props.get('tier1_overlapping') or 0))}건) | "
                        f"최단거리: {float(props.get('nearest_signal_km') or 0.0):.1f} km"
                    )
                    poly_features.append({
                        "type": "Feature",
                        "properties": props,
                        "geometry": feat["geometry"],
                    })
                if poly_features:
                    layers.append(
                        pdk.Layer(
                            "GeoJsonLayer",
                            data={"type": "FeatureCollection", "features": poly_features},
                            pickable=True,
                            stroked=True,
                            filled=True,
                            get_fill_color="properties.fill_rgba",
                            get_line_color="properties.line_rgba",
                            line_width_min_pixels=2,
                        )
                    )

            # 2) 300km 영향 반경 (ScatterplotLayer in meters)
            if show_buffers and signal_clusters:
                buf_df = pd.DataFrame([
                    {
                        "lon": c["lon"],
                        "lat": c["lat"],
                        "radius_m": int(buffer_km * 1000),
                        "fill_rgba": [244, 63, 94, 28] if c["tier1_count"] > 0 else [56, 189, 248, 18],
                        "line_rgba": [244, 63, 94, 150] if c["tier1_count"] > 0 else [56, 189, 248, 110],
                        "tooltip_title": f"⭕ {int(buffer_km)}km 영향 반경 · {c['place_name']}",
                        "tooltip_detail": f"지오코딩 신호 {c['signal_count']}건 (Tier-1: {c['tier1_count']}건)",
                    }
                    for c in signal_clusters
                ])
                layers.append(
                    pdk.Layer(
                        "ScatterplotLayer",
                        data=buf_df,
                        get_position="[lon, lat]",
                        get_radius="radius_m",
                        radius_units="meters",
                        get_fill_color="fill_rgba",
                        get_line_color="line_rgba",
                        stroked=True,
                        filled=True,
                        line_width_min_pixels=1,
                        pickable=False,
                    )
                )

            # 3) OSINT 신호 클러스터 (ScatterplotLayer in pixels)
            if show_signals and signal_clusters:
                sig_df = pd.DataFrame([
                    {
                        "lon": c["lon"],
                        "lat": c["lat"],
                        "radius_px": max(5, min(16, 4 + (c["signal_count"] ** 0.5) * 1.9)),
                        "fill_rgba": [244, 63, 94, 210] if c["tier1_count"] > 0 else [56, 189, 248, 195],
                        "tooltip_title": f"📡 {c['place_name']} ({c['signal_count']}건)",
                        "tooltip_detail": (
                            f"Tier-1: {c['tier1_count']} / Tier-2: {c['tier2_count']} ({c['geo_method']})"
                            + (f"<br/>• {c['sample_titles'][0]}" if c["sample_titles"] else "")
                        ),
                    }
                    for c in signal_clusters
                ])
                layers.append(
                    pdk.Layer(
                        "ScatterplotLayer",
                        data=sig_df,
                        get_position="[lon, lat]",
                        get_radius="radius_px",
                        radius_units="pixels",
                        get_fill_color="fill_rgba",
                        get_line_color=[255, 255, 255, 220],
                        stroked=True,
                        line_width_min_pixels=1,
                        pickable=True,
                    )
                )

            # 4) 6대 반도체·희토류 거점 (ScatterplotLayer in pixels, 최상단)
            if show_hubs:
                hub_rows = [a for a in asset_rows if a["geometry_type"] == "Point"]
                if hub_rows:
                    hub_df = pd.DataFrame([
                        {
                            "lon": a["lon"],
                            "lat": a["lat"],
                            "radius_px": 10 if a["spatial_exposure_level"] == "HIGH" else 8,
                            "fill_rgba": _exposure_rgba(a["spatial_exposure_level"], 235),
                            "tooltip_title": f"🔬 {a['name']}",
                            "tooltip_detail": (
                                f"노출도(보조): {a['spatial_exposure_level']} | "
                                f"중첩: {a['overlapping_signals']}건 (T1: {a['tier1_overlapping']}건) | "
                                f"최단거리: {a['nearest_signal_km']:.1f} km"
                            ),
                        }
                        for a in hub_rows
                    ])
                    layers.append(
                        pdk.Layer(
                            "ScatterplotLayer",
                            data=hub_df,
                            get_position="[lon, lat]",
                            get_radius="radius_px",
                            radius_units="pixels",
                            get_fill_color="fill_rgba",
                            get_line_color=[248, 250, 252, 255],
                            stroked=True,
                            line_width_min_pixels=2,
                            pickable=True,
                        )
                    )

            deck = pdk.Deck(
                map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
                initial_view_state=pdk.ViewState(
                    latitude=view_lat,
                    longitude=view_lon,
                    zoom=view_zoom,
                    pitch=0,
                ),
                layers=layers,
                tooltip={
                    "html": "<b>{tooltip_title}</b><br/>{tooltip_detail}",
                    "style": {
                        "backgroundColor": "#0f172a",
                        "color": "#f8fafc",
                        "border": "1px solid #334155",
                        "fontSize": "12px",
                    },
                },
            )
            st.pydeck_chart(deck, use_container_width=True, height=500)
        else:
            st.info("`pydeck` 패키지가 없어 기본 포인트 지도로 대체 표시합니다.")
            fallback_df = pd.DataFrame([{"lat": a["lat"], "lon": a["lon"]} for a in asset_rows])
            st.map(fallback_df)

        st.subheader("📋 공급망 자산별 공간 노출도 (보조 지표)")
        st.dataframe(
            pd.DataFrame([
                {
                    "자산 ID": a["asset_id"],
                    "자산명": a["name"],
                    "지형 유형": a["asset_type"],
                    "섹터": a["sector"],
                    "공간 노출도 (보조)": a["spatial_exposure_level"],
                    f"{int(buffer_km)}km 중첩": a["overlapping_signals"],
                    "Tier-1 중첩": a["tier1_overlapping"],
                    "최단 거리 (km)": a["nearest_signal_km"],
                }
                for a in asset_rows
            ]),
            use_container_width=True,
            hide_index=True,
        )

        with st.expander(f"📡 지오코딩 OSINT 신호 클러스터 상세 ({len(signal_clusters)}개 좌표)"):
            st.dataframe(
                pd.DataFrame([
                    {
                        "지명": c["place_name"],
                        "지오코딩 방식": c["geo_method"],
                        "전체 신호": c["signal_count"],
                        "Tier-1": c["tier1_count"],
                        "Tier-2": c["tier2_count"],
                        "위도": c["lat"],
                        "경도": c["lon"],
                        "대표 헤드라인": c["sample_titles"][0] if c["sample_titles"] else "-",
                    }
                    for c in signal_clusters
                ]),
                use_container_width=True,
                hide_index=True,
            )

with tab_mysql:
    try:
        conn = init_connection()
        st.caption(f"연결된 DB 백엔드: **{getattr(conn, 'backend', 'unknown').upper()}**")
        attention_df = read_sql_df("SELECT * FROM v_signal_attention_gap ORDER BY analysis_date DESC", conn)
        attention_df["analysis_date"] = pd.to_datetime(attention_df["analysis_date"])
        tone_df = read_sql_df("SELECT * FROM v_signal_tone_gap ORDER BY analysis_date DESC, signal_tone_gap_score DESC", conn)
        tone_df["analysis_date"] = pd.to_datetime(tone_df["analysis_date"])
    except Exception as e:
        st.error(f"DB 연결 또는 뷰 조회 실패: {e}")
        attention_df = pd.DataFrame()
        tone_df = pd.DataFrame()

    st.subheader("📊 1. 정보량 괴리율 (Signal Attention Gap)")
    if not attention_df.empty:
        if HAS_PLOTLY:
            fig_vol = go.Figure()
            fig_vol.add_trace(go.Scatter(x=attention_df["analysis_date"], y=attention_df["total_official_signals"], mode="lines+markers", name="정부 공식 발표 (Official)"))
            fig_vol.add_trace(go.Scatter(x=attention_df["analysis_date"], y=attention_df["total_independent_signals"], mode="lines+markers", name="민간/독립 언론 (Independent)"))
            fig_vol.update_layout(title="시계열 정보량 추이", xaxis_title="날짜", yaxis_title="시그널 수집량", hovermode="x unified")
            st.plotly_chart(fig_vol, use_container_width=True)
        else:
            vol_df = attention_df.set_index("analysis_date")[["total_official_signals", "total_independent_signals"]]
            st.line_chart(vol_df)

        alert_df = attention_df[attention_df["gap_status"] != "NORMAL"]
        if not alert_df.empty:
            st.dataframe(alert_df[["analysis_date", "total_official_signals", "total_independent_signals", "signal_gap_score", "gap_status"]], use_container_width=True)
        else:
            st.success("현재 발령된 정보량 괴리 주의보가 없습니다.")
    else:
        st.info("정보량 괴리 데이터가 없습니다.")

    st.divider()
    st.subheader("🌡️ 2. 논조 온도차 (Signal Tone Gap)")
    if not tone_df.empty:
        latest_tones = tone_df[tone_df["analysis_date"] == tone_df["analysis_date"].max()]
        if not latest_tones.empty:
            if HAS_PLOTLY:
                fig_tone = px.bar(
                    latest_tones,
                    x="issue_ids",
                    y=["avg_gov_tone", "avg_indep_tone"],
                    barmode="group",
                    title=f"이슈별 논조 온도차 (기준일: {tone_df['analysis_date'].max().strftime('%Y-%m-%d')})",
                    labels={"value": "논조 점수 (1=우호, -1=비판)", "variable": "출처", "issue_ids": "글로벌 이슈"},
                )
                st.plotly_chart(fig_tone, use_container_width=True)
            else:
                tone_chart_df = latest_tones.set_index("issue_ids")[["avg_gov_tone", "avg_indep_tone"]]
                st.bar_chart(tone_chart_df)
            tone_alerts = latest_tones[latest_tones["tone_gap_status"] != "NORMAL"]
            if not tone_alerts.empty:
                st.dataframe(tone_alerts[["issue_ids", "avg_gov_tone", "avg_indep_tone", "signal_tone_gap_score", "tone_gap_status"]], use_container_width=True)
            else:
                st.success("현재 논조가 크게 충돌하는 이슈가 없습니다.")
    else:
        st.info("논조 괴리 데이터가 없습니다.")
