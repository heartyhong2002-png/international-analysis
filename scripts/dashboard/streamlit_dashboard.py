import os
import subprocess
import sys
from pathlib import Path

import mysql.connector
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ModuleNotFoundError:
    px = None
    go = None
    HAS_PLOTLY = False

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
)

load_dotenv()

st.set_page_config(
    page_title="글로벌 조기경보 통합 프로토타입 | Signal Gap",
    page_icon="🚨",
    layout="wide",
)


@st.cache_resource
def init_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "international_analysis"),
    )


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

canonical_info = load_canonical_summary()
if canonical_info.get("available"):
    st.sidebar.info(f"전처리 클러스터: {canonical_info['cluster_count']}건")

# --- HEADER ---
st.title("🚨 글로벌 조기경보 통합 프로토타입 (Early-Warning Control Tower)")
st.markdown(
    "**End-to-End 통합 뷰:** 전처리(5W1H) → 3-Tier 경보 산식 → 로컬 3심제(`tev1`·`Gemma2`·`Nemotron-3-Nano`) → `550B Ultra` 2차 감사 → MySQL 시계열 지표를 한 화면에서 확인합니다."
)

# --- TAB LAYOUT ---
tab_integrated, tab_mysql = st.tabs(["🛡️ 통합 경보 · 검증단 관제", "📊 MySQL 시계열 괴리 지표"])

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

with tab_mysql:
    try:
        conn = init_connection()
        attention_df = pd.read_sql("SELECT * FROM v_signal_attention_gap ORDER BY analysis_date DESC", conn)
        attention_df["analysis_date"] = pd.to_datetime(attention_df["analysis_date"])
        tone_df = pd.read_sql("SELECT * FROM v_signal_tone_gap ORDER BY analysis_date DESC, signal_tone_gap_score DESC", conn)
        tone_df["analysis_date"] = pd.to_datetime(tone_df["analysis_date"])
    except Exception as e:
        st.error(f"MySQL 연결 또는 뷰 조회 실패: {e}")
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
