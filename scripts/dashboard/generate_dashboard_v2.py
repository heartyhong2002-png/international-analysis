"""
generate_dashboard_v2.py — 인터랙티브 국제정세 분석 대시보드 (독립형 HTML)
==========================================================================

웹 서버(Node.js/React/FastAPI 등) 배포 없이, 파이썬 스크립트 실행 한 번으로
Chart.js 기반의 고품질 단일 HTML 대시보드를 생성합니다.

주요 시각화 및 지표:
  1. 지정학적 리스크 매트릭스 (Geopolitical Risk Radar - 산점도/버블 차트)
     - X축: 대중 관심도 (Wikipedia Intensity 0~100)
     - Y축: 정부 공식 대응 건수 (Government Matches)
     - 외교적 사각지대(Critical Gap) 자동 하이라이팅
  2. 미디어 프레이밍 & 톤 분석 (Stacked Bar Chart)
     - 이슈별 우호적(Positive) / 중립적(Neutral) / 비판적(Critical) 논조 비율
  3. 정부 발표 데이터 소스 비중 (Doughnut Chart)
     - 한국 외교부, 미국 국무부, 영국 FCDO, 독일 외교부, IRNA 등
  4. ADR-001 인간 검수(HITL) 품질 감사 카드
     - 모델 정확도(60.0%), 검수 커버리지, 과잉비판 오판 지표
  5. 실시간 검색 & 탭 필터링 인텔리전스 피드 테이블
     - 자바스크립트 기반 즉시 검색 (이슈, 기사 제목, 출처)
     - 원문 링크 및 LLM 판단 근거 즉시 확인

사용법:
    python scripts/generate_dashboard_v2.py
    python scripts/generate_dashboard_v2.py --open   # 생성 즉시 브라우저에서 자동 실행
"""

import argparse
import html
import json
import csv
import os
import sys
import webbrowser
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

_DB_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "db"
if str(_DB_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_DB_SCRIPTS_DIR))
from db_conn import get_connection as get_unified_connection  # noqa: E402

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

load_dotenv()

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
from prototype_data import (  # noqa: E402
    CANONICAL_HIGH_PURITY_PATH,
    CANONICAL_PATH,
    build_event_tuple_evidence,
    build_integrated_region_rows,
    load_canonical_refinement,
    load_canonical_summary,
    load_spatial_overlay,
)

PROJECT_ROOT = _SCRIPT_DIR.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "dashboard"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "international_analysis")


def custom_json_serializer(obj):
    """Decimal 및 date/datetime 객체를 JSON 직렬화 가능하도록 변환."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")



def safe_float(val, default=0.0):
    try:
        if val is None or str(val).strip() == "":
            return default
        return float(val)
    except (ValueError, TypeError):
        return default


def fetch_signal_gap_data():
    try:
        with open("data/signal_gap/signal_gap_analysis.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def fetch_financial_proxy():
    proxies = []
    try:
        with open("data/signal_gap/financial_proxy_latest.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                proxies.append(row)
    except Exception:
        pass
    return proxies

def fetch_telegram_osint():
    try:
        with open("data/signal_gap/middle_east_risk_analysis.txt", "r", encoding="utf-8") as f:
            content = f.read()
            return content
    except:
        return "데이터를 불러올 수 없습니다."


def fetch_google_trends_data():
    try:
        with open("data/google_trends/trends_summary.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def fetch_local_opinions_data():
    try:
        with open("data/local_opinions/local_opinions_summary.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def fetch_cross_verification_data(conn=None):
    file_data = {}
    try:
        with open("data/event_cross_verification/verification_latest.json", "r", encoding="utf-8") as f:
            file_data = json.load(f)
    except Exception:
        file_data = {}

    if conn:
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT
                    event_id, event_title, geo_country, event_date,
                    verification_state, alert_candidate_level,
                    distinct_channel_count, matched_channels,
                    confidence_assessment, source_url, is_partial_probe,
                    observed_at, verified_at, total_evidence_items
                FROM v_cross_verified_events_summary
                ORDER BY priority_rank ASC, distinct_channel_count DESC;
            """)
            db_rows = cur.fetchall()
            cur.close()
            if db_rows:
                evidence_map = {ev.get("event_id"): ev.get("corroboration_evidence", []) for ev in file_data.get("verified_events", [])}
                merged_events = []
                for r in db_rows:
                    m_channels = [c.strip() for c in (r.get("matched_channels") or "").split(",") if c.strip()]
                    merged_events.append({
                        "event_id": r["event_id"],
                        "event_title": r["event_title"],
                        "geo_country": r["geo_country"],
                        "event_date": str(r["event_date"]) if r["event_date"] else "",
                        "verification_state": r["verification_state"],
                        "alert_candidate_level": r["alert_candidate_level"],
                        "distinct_channel_count": r["distinct_channel_count"],
                        "matched_channels": m_channels,
                        "confidence_assessment": r["confidence_assessment"],
                        "source_url": r["source_url"],
                        "is_partial_probe": bool(r["is_partial_probe"]),
                        "observed_at": str(r["observed_at"]) if r["observed_at"] else "",
                        "verified_at": str(r["verified_at"]) if r["verified_at"] else "",
                        "corroboration_evidence": evidence_map.get(r["event_id"], [])
                    })
                file_data["verified_events"] = merged_events
                file_data["source_database_view"] = "v_cross_verified_events_summary"
        except Exception:
            pass

    return file_data


def get_connection():
    return get_unified_connection()


def fetch_warning_snapshot(cur):
    """Fetch the official dashboard alert view, if available.

    Alert Level is never inferred here from article counts, tone, or public
    interest.  The DB/analysis track owns the assessment; without its snapshot
    the generated page must state that confirmation is required.
    """
    try:
        cur.execute("""
            SELECT issue_key AS issue,
                   COALESCE(alert_level, 'NO_ALERT') AS alert_level,
                   COALESCE(decision_rationale, '확인 필요') AS risk_signal_summary,
                   COALESCE(signal_gap_summary, '확인 필요') AS signal_gap_summary,
                   evidence_coverage_pct AS evidence_coverage,
                   evidence_count,
                   CASE WHEN requires_human_review THEN 'human_review_required'
                        WHEN alert_event_id IS NULL THEN 'no_alert_event'
                        ELSE COALESCE(alert_status, '확인 필요') END AS validation_status,
                   CASE WHEN requires_human_review THEN '확인 필요'
                        ELSE '자동 검수 대기' END AS human_review_status,
                   COALESCE(triggered_at, scored_at) AS assessed_at
            FROM v_dashboard_current_alerts
            ORDER BY assessed_at DESC, issue_key ASC
        """)
        rows = cur.fetchall()
        return rows, bool(rows), "official_view_with_rows" if rows else "official_view_empty"
    except Exception:
        return [], False, "official_view_unavailable"


def fetch_all_dashboard_data(conn):
    """MySQL DB의 정규화 테이블 및 분석 뷰에서 데이터를 통합 집계합니다."""
    cur = conn.cursor(dictionary=True)
    warning_snapshot, warning_snapshot_available, warning_snapshot_status = fetch_warning_snapshot(cur)

    # 1. 지정학적 리스크 매트릭스 뷰
    cur.execute("""
        SELECT issue, public_intensity, wiki_total_pageviews, wiki_daily_avg_pageviews,
               total_gov_matches, official_statement_count, state_media_news_count,
               diplomatic_status, attention_gap_rank, data_as_of
        FROM v_issue_geopolitical_risk_matrix
        ORDER BY attention_gap_rank ASC
    """)
    risk_matrix = cur.fetchall()

    # 2. 미디어 프레이밍 & 톤 분석 뷰
    cur.execute("""
        SELECT issue, source_type, outlet_bias, total_articles,
               positive_count, neutral_count, critical_count,
               positive_pct, neutral_pct, critical_pct
        FROM v_issue_media_framing_summary
        ORDER BY total_articles DESC
    """)
    framing_data = cur.fetchall()

    # 3. ADR-001 인간 검수 감사 뷰
    cur.execute("""
        SELECT language, source_type, total_samples, llm_classified_count,
               human_reviewed_count, review_coverage_pct, agreement_count,
               disagreement_count, model_accuracy_pct, llm_over_critical_count,
               llm_under_critical_count
        FROM v_human_in_the_loop_audit
    """)
    audit_data = cur.fetchall()

    # 4. 정부 발표 출처별 통계
    cur.execute("""
        SELECT source, COUNT(*) AS cnt
        FROM gov_announcements
        GROUP BY source
        ORDER BY cnt DESC
    """)
    gov_sources = cur.fetchall()

    # 5. 전체 누적 카운트 (KPI용)
    cur.execute("SELECT COUNT(*) AS total FROM gov_announcements")
    total_gov = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) AS total FROM tone_review_log")
    total_articles = cur.fetchone()["total"]

    # 6. 최신 인텔리전스 피드 (LLM 분류 및 검수 기사 목록 Top 50)
    # PHASE2_THINKTANK_REDDIT_HANDOFF.md 작업 2 반영: [전문가 분석(Think Tank)] 기사를
    # 최우선 노출하도록 정렬 1순위에 source_type='expert_analysis' 추가.
    # ⚠️ 이 클라우드 세션에는 MySQL 접속이 없어 이 쿼리를 실제 DB로 실행 검증하지
    # 못했습니다. `tone_review_log`에 expert_analysis 행이 실제로 들어오는지는
    # build_database.py(①SQL 트랙 소유, 이 파일에서 직접 건드리지 않음)의
    # load_tone_review_logs()/load_expert_analysis_extractions() 구현에 달려 있습니다
    # — 만약 expert_analysis가 별도 테이블(expert_analysis_extractions)로만 적재되고
    # tone_review_log에는 전혀 없다면 이 ORDER BY 변경은 안전하게 아무 효과가 없습니다
    # (에러는 안 남). 로컬에서 대시보드를 열어 "전문가 분석" 필터 탭에 실제로 뭔가
    # 잡히는지 확인 권장 — 안 잡히면 ①SQL 트랙과 조율해서 두 테이블을 UNION하는
    # 추가 작업이 필요합니다.
    cur.execute("""
        SELECT article_id, language, issue_ids, continent, source_type,
               outlet_bias, title, link, llm_label, llm_evidence_quote,
               human_label, correction_note, reviewed_at, collected_at
        FROM tone_review_log
        ORDER BY (source_type = 'expert_analysis') DESC,
                 (llm_label IS NOT NULL AND llm_label != '') DESC, id DESC
        LIMIT 60
    """)
    recent_feed = cur.fetchall()

    cur.close()

    signal_gap_data = fetch_signal_gap_data()
    financial_proxy = fetch_financial_proxy()
    telegram_osint = fetch_telegram_osint()
    google_trends_data = fetch_google_trends_data()
    local_opinions_data = fetch_local_opinions_data()
    cross_verification_data = fetch_cross_verification_data(conn)

    return {
        "signal_gap_data": signal_gap_data,
        "integrated_regions": build_integrated_region_rows(),
        "canonical_summary": load_canonical_summary(),
        "canonical_refinement": {
            "standard": load_canonical_refinement(CANONICAL_PATH),
            "high_purity": load_canonical_refinement(CANONICAL_HIGH_PURITY_PATH),
        },
        "event_tuple_evidence": build_event_tuple_evidence(limit=12),
        "spatial_overlay": load_spatial_overlay(),
        "financial_proxy": financial_proxy,
        "telegram_osint": telegram_osint,
        "google_trends_data": google_trends_data,
        "local_opinions_data": local_opinions_data,
        "cross_verification_data": cross_verification_data,
        "risk_matrix": risk_matrix,
        "framing_data": framing_data,
        "audit_data": audit_data,
        "gov_sources": gov_sources,
        "total_gov": total_gov,
        "total_articles": total_articles,
        "recent_feed": recent_feed,
        "warning_snapshot": warning_snapshot,
        "warning_snapshot_available": warning_snapshot_available,
        "warning_snapshot_status": warning_snapshot_status,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def generate_dashboard_html(data):
    matrix = data["risk_matrix"]
    framing = data["framing_data"]
    audit = data["audit_data"]
    gov_sources = data["gov_sources"]
    feed = data["recent_feed"]
    warning_snapshot = data["warning_snapshot"]
    warning_snapshot_available = data["warning_snapshot_available"]
    warning_snapshot_status = data.get("warning_snapshot_status", "official_view_unavailable")

    # KPI 계산
    total_issues = len(matrix)

    critical_gap_count = sum(1 for m in matrix if "CRITICAL_GAP" in str(m.get("diplomatic_status", "")))
    
    # HITL 종합 일치율 계산
    total_reviewed = sum(a.get("human_reviewed_count") or 0 for a in audit)
    total_agreed = sum(a.get("agreement_count") or 0 for a in audit)
    hitl_accuracy = (total_agreed / total_reviewed * 100) if total_reviewed > 0 else 0.0

    
    # NEW: Telegram OSINT, Signal Gap, and Financial Proxies integration
    sg_data = data.get("signal_gap_data", {})
    fp_data = data.get("financial_proxy", [])
    tg_osint = data.get("telegram_osint", "")

    # Format Telegram OSINT
    tg_osint_html = ""
    for line in tg_osint.split("\n"):
        if not line.strip(): continue
        if line.startswith("["):
            tg_osint_html += f"<h4>{html.escape(line)}</h4>"
        else:
            tg_osint_html += f"<p>{html.escape(line)}</p>"

    integrated_rows = data.get("integrated_regions", [])
    integrated_table_rows = ""
    for r in integrated_rows:
        triggers_txt = ", ".join(r.get("triggers") or []) or "-"
        nim_txt = (
            f"{r['nim_fact']} / {r['nim_inference']}"
            if r.get("nim_status") == "ok"
            else (r.get("nim_status") or "-")
        )
        badge_cls = "tag-danger" if r.get("needs_human_review") else "tag-success"
        integrated_table_rows += f"""
        <tr>
          <td><strong>{html.escape(str(r.get('region', '-')))}</strong></td>
          <td><span class="kpi-tag {badge_cls}">{html.escape(str(r.get('alert_level_ko', '-')))} ({html.escape(str(r.get('formula_alert_en', '-')))})</span></td>
          <td>{safe_float(r.get('risk_signal_score', 0.0)):.1f}</td>
          <td>{html.escape(str(r.get('tev1_verdict', '-')))}</td>
          <td>{html.escape(str(r.get('gemma2_verdict', '-')))}</td>
          <td>{html.escape(str(r.get('critic_verdict', '-')))}</td>
          <td>{html.escape(str(r.get('presiding_decision', '-')))}</td>
          <td>{html.escape(nim_txt)}</td>
          <td>{html.escape(triggers_txt)}</td>
        </tr>
        """
    if not integrated_table_rows:
        integrated_table_rows = '<tr><td colspan="9" style="text-align:center;color:var(--text-muted);">통합 검증 데이터가 없습니다.</td></tr>'

    # 전처리 세밀화(2026-11-20) 산출물 소비: event_tuple의 who / when / extracted_metrics 커버리지.
    # 표시 전용 — Risk Signal Score·Alert Level 산식에는 절대 연결하지 않는다.
    refine = data.get("canonical_refinement", {})
    std_ref = refine.get("standard") or {}
    high_ref = refine.get("high_purity") or {}

    def _refine_value(info: dict, key: str, suffix: str = "") -> str:
        if not info.get("available"):
            return "확인 필요"
        return f"{info.get(key, 0)}{suffix}"

    def _preprocess_stamp(info: dict) -> str:
        raw = str(info.get("generated_at") or "")
        if not raw:
            return "확인 필요"
        try:
            moment = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=timezone.utc)
            return moment.astimezone(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M") + " KST"
        except ValueError:
            return raw

    cluster_badge = (
        f"전처리 클러스터 Standard {std_ref.get('cluster_count', 0)}건 · "
        f"High-Purity {high_ref.get('cluster_count', 0)}건"
        if std_ref.get("available") else "전처리 대기"
    )

    refine_tiles_html = f"""
        <div class="refine-tile">
          <div class="refine-label">5W1H 이벤트 튜플</div>
          <div class="refine-value">{_refine_value(high_ref, 'cluster_count', ' 건')}</div>
          <div class="refine-sub">High-Purity · Standard {_refine_value(std_ref, 'cluster_count', '건')}<br>전처리 생성 {_preprocess_stamp(high_ref or std_ref)}</div>
        </div>
        <div class="refine-tile">
          <div class="refine-label">행위자(who) 확인</div>
          <div class="refine-value">{_refine_value(high_ref, 'who_resolved_pct', '%')}</div>
          <div class="refine-sub">High 미상 {high_ref.get('who_unresolved', 0)}건 · Standard {_refine_value(std_ref, 'who_resolved_pct', '%')} 확인<br>미확정 행은 '확인 필요'로 표시</div>
        </div>
        <div class="refine-tile">
          <div class="refine-label">when ISO-8601 정제</div>
          <div class="refine-value">{_refine_value(high_ref, 'when_iso_pct', '%')}</div>
          <div class="refine-sub">High {high_ref.get('when_iso', 0)}/{high_ref.get('cluster_count', 0)}건 정규화<br>Standard {_refine_value(std_ref, 'when_iso_pct', '%')} (미정제는 원문 표기 유지)</div>
        </div>
        <div class="refine-tile">
          <div class="refine-label">정량 수치 (extracted_metrics)</div>
          <div class="refine-value">{_refine_value(high_ref, 'metric_values', ' 건')}</div>
          <div class="refine-sub">High {high_ref.get('metric_clusters', 0)}개 클러스터에서 확보<br>Standard {std_ref.get('metric_clusters', 0)}개 클러스터 · {_refine_value(std_ref, 'metric_values', '건')}</div>
        </div>
    """

    evidence_rows = data.get("event_tuple_evidence", [])
    event_tuple_rows_html = ""
    for r in evidence_rows:
        title_txt = html.escape(str(r.get("title") or "확인 필요"))
        link = str(r.get("url") or "")
        title_cell = (
            f'<a href="{html.escape(link, quote=True)}" target="_blank" rel="noopener noreferrer">{title_txt}</a>'
            if link.startswith("http") else title_txt
        )
        who_txt = "확인 필요" if r.get("who_unresolved") else html.escape(str(r.get("who") or "확인 필요"))
        when_raw = str(r.get("when") or "")
        if not when_raw:
            when_cell = "확인 필요"
        elif r.get("when_normalized"):
            when_cell = f'<span style="color:#6ee7b7;">{html.escape(when_raw)}</span>'
        else:
            when_cell = f'{html.escape(when_raw)} <span class="kpi-tag tag-amber" style="font-size:9px;">원문 표기</span>'

        metrics = r.get("metrics") or []
        if metrics:
            more = f' <span style="color:var(--text-muted);">+{len(metrics) - 4}건</span>' if len(metrics) > 4 else ""
            metrics_cell = " · ".join(html.escape(m) for m in metrics[:4]) + more
        else:
            metrics_cell = '<span style="color:var(--text-muted);">정량 수치 확인 필요</span>'

        severity = str(r.get("threat_severity") or "")
        sev_cls = "tag-danger" if "CRITICAL" in severity else ("tag-amber" if severity.startswith("HIGH") else "tag-info")
        sev_cell = f'<span class="kpi-tag {sev_cls}" style="font-size:10px;">{html.escape(severity)}</span>' if severity else "확인 필요"
        vstate = str(r.get("verification_state") or "")
        vstate_cell = f'<span class="kpi-tag tag-info" style="font-size:10px;">{html.escape(vstate)}</span>' if vstate else "확인 필요"
        lang_txt = html.escape(str(r.get("primary_language") or "-"))
        if r.get("is_cross_lingual"):
            lang_txt += " · cross-lingual"
        evidence = f"출처 {r.get('unique_sources_count', 0)}개 · 기사 {r.get('cluster_size', 0)}건<br><span style='color:var(--text-muted);font-size:11px;'>{lang_txt}</span>"

        event_tuple_rows_html += f"""
        <tr style="border-bottom: 1px solid rgba(255,255,255,0.07);">
          <td style="padding: 9px 8px; max-width: 320px;"><strong>{title_cell}</strong></td>
          <td style="padding: 9px 8px;">{who_txt}</td>
          <td style="padding: 9px 8px; font-size: 12px;">{html.escape(str(r.get('action') or '확인 필요'))}<br><span style="color:var(--text-muted);">→ {html.escape(str(r.get('target') or '확인 필요'))}</span></td>
          <td style="padding: 9px 8px; font-size: 11px; color: var(--text-muted);">{html.escape(str(r.get('where') or '확인 필요'))}</td>
          <td style="padding: 9px 8px; font-size: 11px;">{when_cell}</td>
          <td style="padding: 9px 8px; font-size: 12px;">{metrics_cell}</td>
          <td style="padding: 9px 8px;">{vstate_cell}<br>{sev_cell}</td>
          <td style="padding: 9px 8px; font-size: 11px;">{evidence}</td>
        </tr>
        """
    if not event_tuple_rows_html:
        event_tuple_rows_html = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:18px;">High-Purity 전처리 산출물이 없습니다. 전처리 세션을 실행해 <code>canonical_signals_high_purity_latest.json</code>을 생성하세요.</td></tr>'
    evidence_metric_hits = sum(1 for r in evidence_rows if r.get("metrics"))

    # GIS Spatial Risk Overlay (보조 지표 전용 — 결정론적 경보 산식 calculate_alert_assessment 미반영)
    spatial = data.get("spatial_overlay") or {}
    spatial_available = bool(spatial.get("available"))
    spatial_assets = spatial.get("asset_rows") or []
    spatial_clusters = spatial.get("signal_clusters") or []
    spatial_buffer_km = safe_float(spatial.get("buffer_km"), 300.0)
    spatial_total_sig = int(spatial.get("total_canonical_signals") or 0)
    spatial_geo_sig = int(spatial.get("geocoded_signals") or 0)
    spatial_geo_pct = round((spatial_geo_sig / spatial_total_sig * 100.0), 1) if spatial_total_sig else 0.0
    spatial_high_cnt = sum(1 for a in spatial_assets if a.get("spatial_exposure_level") == "HIGH")
    spatial_high_choke = sum(
        1 for a in spatial_assets
        if a.get("spatial_exposure_level") == "HIGH" and a.get("asset_type") == "maritime_chokepoint"
    )
    spatial_high_hub = spatial_high_cnt - spatial_high_choke
    spatial_total_overlap = sum(int(a.get("overlapping_signals") or 0) for a in spatial_assets)
    spatial_total_tier1 = sum(int(a.get("tier1_overlapping") or 0) for a in spatial_assets)
    spatial_crs_label = str(spatial.get("crs_metric_analysis") or "EPSG:6933")
    spatial_gpd_ver = str(spatial.get("geopandas_version") or "-")
    spatial_stamp = _preprocess_stamp({"generated_at": spatial.get("generated_at", "")})

    spatial_tiles_html = f"""
        <div class="refine-tile">
          <div class="refine-label">지오코딩 신호 커버리지</div>
          <div class="refine-value">{f"{spatial_geo_sig} / {spatial_total_sig}건" if spatial_available else "확인 필요"}</div>
          <div class="refine-sub">{f"커버리지 {spatial_geo_pct}% · {len(spatial_clusters)}개 좌표 클러스터" if spatial_available else "spatial_risk_overlay.py 실행 필요"}<br>산출 시각 {spatial_stamp}</div>
        </div>
        <div class="refine-tile">
          <div class="refine-label">HIGH 노출 공급망 자산</div>
          <div class="refine-value" style="color: var(--accent-red);">{f"{spatial_high_cnt} / {len(spatial_assets)}개" if spatial_available else "확인 필요"}</div>
          <div class="refine-sub">해협 {spatial_high_choke}곳 · 반도체/희토류 거점 {spatial_high_hub}곳<br>보조 지표 (공식 경보 단계 미변경)</div>
        </div>
        <div class="refine-tile">
          <div class="refine-label">{int(spatial_buffer_km)}km 버퍼 중첩 (sjoin)</div>
          <div class="refine-value">{f"{spatial_total_overlap}건" if spatial_available else "확인 필요"}</div>
          <div class="refine-sub">Tier-1 교차검증 신호 중첩 {spatial_total_tier1}건<br>중복 자산 반경 교차 합계</div>
        </div>
        <div class="refine-tile">
          <div class="refine-label">GIS 투영좌표계 · 엔진</div>
          <div class="refine-value" style="font-size:19px;">{html.escape(spatial_crs_label)}</div>
          <div class="refine-sub">WGS84(EPSG:4326) → 등적 미터 투영<br>GeoPandas {html.escape(spatial_gpd_ver)} · 반경 {int(spatial_buffer_km)}km</div>
        </div>
    """

    spatial_asset_rows_html = ""
    for a in spatial_assets:
        lvl = str(a.get("spatial_exposure_level") or "NONE")
        lvl_cls = (
            "tag-danger" if lvl == "HIGH"
            else ("tag-amber" if lvl == "MODERATE" else ("tag-info" if lvl == "LOW" else "badge-gray"))
        )
        atype = str(a.get("asset_type") or "")
        if atype == "maritime_chokepoint":
            type_lbl = "⚓ 해협 (Polygon)"
        elif atype == "critical_minerals_hub":
            type_lbl = "⛏️ 희토류 거점 (Point)"
        else:
            type_lbl = "🔬 반도체 거점 (Point)"
        zoom_lvl = 5 if atype == "maritime_chokepoint" else 6
        lat_v = safe_float(a.get("lat"), 0.0)
        lon_v = safe_float(a.get("lon"), 0.0)
        spatial_asset_rows_html += f"""
        <tr style="border-bottom: 1px solid rgba(255,255,255,0.07);">
          <td style="padding: 9px 8px;"><strong>{html.escape(str(a.get('name') or '-'))}</strong><br><span style="font-size:11px;color:var(--text-muted);">{html.escape(str(a.get('asset_id') or ''))} · {html.escape(str(a.get('sector') or ''))}</span></td>
          <td style="padding: 9px 8px; font-size: 12px;">{type_lbl}</td>
          <td style="padding: 9px 8px;"><span class="kpi-tag {lvl_cls}">{html.escape(lvl)}</span></td>
          <td style="padding: 9px 8px; font-weight: 700;">{int(a.get('overlapping_signals') or 0)}건</td>
          <td style="padding: 9px 8px; color: {'#f87171' if int(a.get('tier1_overlapping') or 0) > 0 else 'var(--text-muted)'}; font-weight: 600;">{int(a.get('tier1_overlapping') or 0)}건</td>
          <td style="padding: 9px 8px; font-family: 'JetBrains Mono', monospace; font-size: 12px;">{safe_float(a.get('nearest_signal_km'), 0.0):.1f} km</td>
          <td style="padding: 9px 8px;"><button type="button" class="pill-btn" style="padding:4px 10px;font-size:11px;" onclick="focusSpatialAsset({lat_v}, {lon_v}, {zoom_lvl})">이동</button></td>
        </tr>
        """
    if not spatial_asset_rows_html:
        spatial_asset_rows_html = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:18px;">공간 중첩 산출물이 없습니다. <code>scripts/analysis/spatial_risk_overlay.py</code>를 먼저 실행하세요.</td></tr>'

    spatial_assets_json = json.dumps(
        spatial.get("assets_geojson") or {"type": "FeatureCollection", "features": []},
        ensure_ascii=False,
        default=custom_json_serializer,
    )
    spatial_clusters_json = json.dumps(
        spatial_clusters,
        ensure_ascii=False,
        default=custom_json_serializer,
    )

    # Create Signal Gap and Financial Proxy Cards
    sg_html = ""
    for region, details in sg_data.items():
        raw_score = details.get("discrepancy_score")
        if raw_score is None:
            raw_score = details.get("risk_signal_score")
        score = float(raw_score) if raw_score is not None else 0.0
        color_cls = "tag-danger" if score >= 80 else ("tag-amber" if score >= 50 else "tag-info")
        sg_html += f"""
        <div style="background: rgba(0,0,0,0.25); padding: 14px; border-radius: 8px; margin-bottom: 10px; border-left: 3px solid {'#ef4444' if score>=80 else '#f59e0b'};">
            <div style="font-size: 14px; font-weight: 700;">{html.escape(region)} 신호 괴리율 <span class="kpi-tag {color_cls}">{f"{int(score)}점" if raw_score is not None else "신호 대기"}</span></div>
            <div style="font-size: 12px; color: var(--text-muted); margin-top: 5px;">{html.escape(details.get("narrative_differences", ""))}</div>
        </div>
        """

    fp_html = ""
    for item in fp_data:
        change = safe_float(item.get("Monthly_Change_Percent"), 0.0)
        color_cls = "tag-danger" if change < -5 else ("tag-info" if change > 0 else "tag-success")
        fp_html += f"""
        <div style="background: rgba(0,0,0,0.25); padding: 14px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between;">
            <div>
                <div style="font-size: 14px; font-weight: 700;">{html.escape(item.get('Asset_Name', ''))} ({html.escape(item.get('Ticker', ''))})</div>
                <div style="font-size: 12px; color: var(--text-muted); margin-top: 3px;">신호: {html.escape(item.get('Risk_Signal', ''))}</div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 18px; font-weight: 700;">{html.escape(str(item.get('Price_Latest', '')))}</div>
                <div class="kpi-tag {color_cls}">{change}%</div>
            </div>
        </div>
        """

    # NEW: Google Trends & Local Opinions (PTT, Pincong, Bluesky, Google News, Telegram)
    gt_data = data.get("google_trends_data", {})
    lo_data = data.get("local_opinions_data", {})

    # Trends Cards
    gt_by_country = gt_data.get("by_country", {})
    gt_cards_html = ""
    for cc, cinfo in gt_by_country.items():
        cname = cinfo.get("country_name", cc)
        surge_cnt = cinfo.get("surge", 0)
        tot_cnt = cinfo.get("total", 0)
        badge_cls = "tag-danger" if surge_cnt >= 2 else ("tag-amber" if surge_cnt == 1 else "tag-success")
        
        top_kws = ""
        for kw_item in cinfo.get("top_keywords", [])[:3]:
            top_kws += f"""<div style="font-size:12px; margin-top:5px; display:flex; justify-content:space-between; align-items:center;">
                <span>• {html.escape(kw_item['keyword'])}</span>
                <span class="kpi-tag tag-danger" style="font-size:10px;">x{kw_item['surge_ratio']} 급등</span>
            </div>"""
        
        if not top_kws:
            top_kws = '<div style="font-size:12px; color:var(--text-muted); margin-top:4px;">검색어 급등 징후 없음 (안정)</div>'

        gt_cards_html += f"""
        <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--border); border-radius: 8px; padding: 12px; margin-bottom: 10px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <strong style="font-size:13px;">[{cc}] {html.escape(cname)}</strong>
            <span class="kpi-tag {badge_cls}">급등 {surge_cnt}/{tot_cnt}개</span>
          </div>
          {top_kws}
        </div>
        """

    if not gt_cards_html:
        gt_cards_html = '<div style="font-size:12px; color:var(--text-muted); padding:10px;">구글 트렌드 데이터 준비 중입니다.</div>'

    # Local Opinions Cards - balance across platforms
    lo_items = []
    try:
        with open("data/local_opinions/local_opinions_latest.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            grouped = {}
            for r in reader:
                p_key = r.get("source_platform", "").split("_")[0]
                grouped.setdefault(p_key, []).append(r)
            for p_key, rows in grouped.items():
                lo_items.extend(rows[:2])
    except Exception:
        lo_items = lo_data.get("featured_signals", [])[:10]

    lo_rows_html = ""
    for item in lo_items:
        plat = item.get("source_platform", "Web")
        reg = item.get("country_or_region", "GLOBAL")
        title = item.get("title_or_text", "")
        url = item.get("url", "#")
        theme = item.get("risk_theme", "")
        author = item.get("author", "")
        
        plat_color = "#38bdf8" if "PTT" in plat else ("#f59e0b" if "Pincong" in plat else ("#818cf8" if "Bluesky" in plat else ("#10b981" if "Telegram" in plat else "#ec4899")))
        
        lo_rows_html += f"""
        <div style="padding: 10px; border-bottom: 1px solid var(--border); font-size: 12px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <span style="font-weight:700; color:{plat_color}; background:rgba(255,255,255,0.06); padding:2px 7px; border-radius:4px; font-size:11px;">{html.escape(plat)}</span>
            <span style="color:var(--text-muted); font-size:11px;">[{html.escape(reg)}] {html.escape(author)}</span>
          </div>
          <div style="margin: 4px 0;">
            <a href="{html.escape(url)}" target="_blank" rel="noopener noreferrer" style="color:var(--text-main); text-decoration:none; font-weight:600; line-height:1.4;">
              {html.escape(title[:120])}{'...' if len(title)>120 else ''}
            </a>
          </div>
          <div style="color:var(--text-muted); font-size:11px;">🔍 {html.escape(theme)}</div>
        </div>
        """

    if not lo_rows_html:
        lo_rows_html = '<div style="font-size:12px; color:var(--text-muted); padding:10px;">온라인 정보환경 신호 데이터 준비 중입니다.</div>'

    # NEW: Cross-Verification Events (GDELT Cloud + Maritime + Freight + Local Opinion + Telegram)
    cv_data = data.get("cross_verification_data", {})
    cv_events = cv_data.get("verified_events", [])
    coverage_meta = cv_data.get("data_coverage", {})
    is_partial_cov = coverage_meta.get("is_partial_collection", True)
    single_source_forbidden = cv_data.get("cross_verification_contract", {}).get("single_source_elevate_forbidden", True)
    summary_counts = cv_data.get("summary_counts", {})
    state_counts_text = ", ".join([f"{k}: {v}건" for k, v in summary_counts.get("by_verification_state", {}).items()]) or "집계 대기"

    cv_cards_html = ""
    for ev in cv_events:
        eid = ev.get("event_id", "")
        title = ev.get("event_title", "")
        country = ev.get("geo_country", "")
        edate = ev.get("event_date", "")
        obs_at = ev.get("observed_at", "")[:19].replace("T", " ")
        vstate = ev.get("verification_state", "UNVERIFIED")
        alevel = ev.get("alert_candidate_level", "NORMAL")
        mchannels = ev.get("matched_channels", [])
        ch_count = ev.get("distinct_channel_count", 0)
        surl = ev.get("source_url", "#")
        conf_text = ev.get("confidence_assessment", "")

        # State & Alert badges
        state_badge_cls = "tag-success" if vstate == "CROSS_VERIFIED" else ("tag-amber" if vstate == "PARTIALLY_CONFIRMED" else "tag-info")
        alert_badge_cls = "tag-danger" if alevel == "WARNING" else ("tag-amber" if alevel == "WATCH" else "tag-success")

        # Channel tags
        ch_tags = ""
        channel_names = {
            "maritime_chokepoint": "⚓ 해협·항만",
            "freight_market": "🚢 운임·에너지",
            "local_public_opinion": "🌐 온라인 정보환경",
            "telegram_osint_public": "📡 공개 Telegram 주장"
        }
        for ch in mchannels:
            lbl = channel_names.get(ch, ch)
            ch_tags += f'<span style="background:rgba(255,255,255,0.06); padding:2px 6px; border-radius:4px; font-size:10px; margin-right:4px;">{lbl}</span>'
        if not ch_tags:
            ch_tags = '<span style="color:var(--text-muted); font-size:10px;">교차 센서 미결합 (단일 탐지)</span>'

        # Evidences list
        ev_items = ""
        for item in ev.get("corroboration_evidence", [])[:2]:
            ev_items += f'<div style="font-size:11px; color:var(--text-muted); margin-top:3px; line-height:1.4;">• [{html.escape(item.get("channel",""))}] {html.escape(item.get("note",""))}</div>'

        cv_cards_html += f"""
        <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--border); border-radius: 8px; padding: 12px; margin-bottom: 10px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <div style="display:flex; gap:6px; align-items:center;">
              <span class="kpi-tag {alert_badge_cls}">{html.escape(alevel)}</span>
              <span class="kpi-tag {state_badge_cls}">{html.escape(vstate)}</span>
              <strong style="font-size:13px; margin-left:4px;">[{html.escape(country)}] {html.escape(title[:70])}{'...' if len(title)>70 else ''}</strong>
            </div>
            <span style="font-size:11px; color:var(--text-muted);">관측: {obs_at}</span>
          </div>
          <div style="margin: 4px 0 6px 0;">
            <a href="{html.escape(surl)}" target="_blank" rel="noopener noreferrer" style="font-size:12px; color:var(--text-main); text-decoration:none;">
              🔗 원문/사건 출처 확인 (ID: {html.escape(eid)})
            </a>
          </div>
          <div style="display:flex; align-items:center; margin-bottom:4px;">
            <span style="font-size:11px; font-weight:600; margin-right:6px;">결합 센서 ({ch_count}계통):</span>
            {ch_tags}
          </div>
          <div style="background:rgba(0,0,0,0.15); padding:6px 8px; border-radius:4px;">
            <div style="font-size:11px; font-weight:600; color:#38bdf8;">신뢰도: {html.escape(conf_text)}</div>
            {ev_items}
          </div>
        </div>
        """

    if not cv_cards_html:
        cv_cards_html = '<div style="font-size:12px; color:var(--text-muted); padding:10px;">교차검증 데이터가 없습니다.</div>'

    # Figma Balanced Watchboard: five equally weighted monitoring axes.
    # These cards summarize observed coverage only; they never derive Alert Level.
    cv_state_counts = summary_counts.get("by_verification_state", {})
    cv_total = len(cv_events)
    cross_state = "CROSS_VERIFIED" if cv_state_counts.get("CROSS_VERIFIED", 0) else "확인 필요"
    fro_item = next((x for x in fp_data if str(x.get("Ticker", "")).upper() == "FRO"), {})
    fro_change = fro_item.get("Monthly_Change_Percent")
    axis_cards = [
        ("AIS", "MARITIME", "해협·항만·선박 우회", f"{cv_total}건 후보", cross_state, "해협 + AIS 프록시"),
        ("MKT", "ENERGY", "유가·LNG·전쟁보험료", f"FRO {fro_change}%" if fro_change not in (None, "") else "시장 지표 확인 필요", "확인 필요", "에너지·보험료·탱커"),
        ("OSINT", "INFORMATION", "GDELT·언론·온라인 정보환경", f"{len(feed)}건 원문 피드", "부분 커버리지", "GDELT + 공개 채널"),
        ("FLOW", "FINANCE / TRADE", "운임·금융·무역 프록시", f"{len(fp_data)}개 시장 지표", "확인 필요", "운임·선사·원자재"),
        ("SIG", "STATE / ACTOR", "정부·군·행위자 공식 입장", f"{len(gov_sources)}개 공식 출처", "주장·입장 분리", "공식 발표 + 공개 주장"),
    ]
    axis_cards_html = "".join(f"""
      <article class="axis-card">
        <div class="axis-kicker">{html.escape(kicker)}</div>
        <h3>{html.escape(title)}</h3>
        <p class="axis-subtitle">{html.escape(subtitle)}</p>
        <span class="axis-status">{html.escape(status)}</span>
        <div class="axis-metric">{html.escape(metric)}</div>
        <p class="axis-sensors">{html.escape(sensors)}</p>
      </article>""" for kicker, title, subtitle, metric, status, sensors in axis_cards)

    new_section_html = f"""
  <section class="axis-section">
    <div class="axis-section-head">
      <div>
        <div class="section-eyebrow">SUPPLY CHAIN / GEOPOLITICAL RISK</div>
        <h2>Balanced Watchboard</h2>
        <p>Five monitoring axes · evidence-first early warning</p>
      </div>
      <div class="axis-live">● LIVE · {data['generated_at']} KST</div>
    </div>
    <div class="axis-banner"><span>▲ ELEVATED SUPPLY-CHAIN RISK / IMMEDIATE REVIEW REQUIRED</span><strong>NO SINGLE-SOURCE ESCALATION</strong></div>
    <div class="axis-grid">{axis_cards_html}</div>
  </section>

  <section class="charts-grid">
    <div class="chart-card">
      <div class="chart-header">
        <div>
          <div class="chart-title">📡 공개 Telegram · 온라인 정보환경 신호</div>
          <div class="chart-subtitle">국민 여론이 아닌 공개 채널 주장·표현입니다. Alert Level을 단독으로 확정하지 않습니다.</div>
        </div>
      </div>
      <div style="overflow-y: auto; max-height: 350px; font-size: 13px; line-height: 1.6;">
        <div style="background: rgba(56,189,248,0.08); border: 1px solid rgba(56,189,248,0.25); padding: 15px; border-radius: 8px;">
          <div style="display:inline-block; background:rgba(56,189,248,0.2); color:#bae6fd; padding:2px 8px; border-radius:4px; font-weight:bold; font-size:11px; margin-bottom:10px;">검토 후보 · 확인 필요</div>
          {tg_osint_html}
        </div>
      </div>
    </div>

    <div class="chart-card" style="display: flex; flex-direction: column; gap: 15px;">
      <div>
        <div class="chart-title" style="margin-bottom:10px;">📉 신호 괴리율 (Signal Gap Radar)</div>
        {sg_html}
      </div>
      <div>
        <div class="chart-title" style="margin-bottom:10px;">💰 금융 대체 지표 (Financial Proxies)</div>
        {fp_html}
      </div>
    </div>
  </section>

  <!-- Integrated Early-Warning + Multi-Judge Prototype Section -->
  <section class="chart-card" style="margin-bottom: 28px;">
    <div class="chart-header">
      <div>
        <div class="chart-title">🛡️ 통합 조기경보 · §10.4 멀티저지 직교 검증단 (프로토타입 통합 뷰)</div>
        <div class="chart-subtitle">전처리 → 3-Tier 경보 산식 → 로컬 3심제(tev1 · Gemma2 · Nemotron-3-Nano) → 550B Ultra 2차 감사 ({html.escape(cluster_badge)})</div>
      </div>
    </div>
    <div style="overflow-x: auto;">
      <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
        <thead>
          <tr style="border-bottom: 1px solid rgba(255,255,255,0.12); text-align: left;">
            <th style="padding: 8px;">권역</th>
            <th style="padding: 8px;">공식 경보</th>
            <th style="padding: 8px;">리스크 점수</th>
            <th style="padding: 8px;">tev1</th>
            <th style="padding: 8px;">Gemma2</th>
            <th style="padding: 8px;">Nemotron-3-Nano</th>
            <th style="padding: 8px;">Mistral 재판관</th>
            <th style="padding: 8px;">550B Ultra (NIM)</th>
            <th style="padding: 8px;">검수 트리거</th>
          </tr>
        </thead>
        <tbody>
          {integrated_table_rows}
        </tbody>
      </table>
    </div>
  </section>

  <!-- 5W1H Event-Tuple Quantitative Evidence Section (preprocessing fine-grained output) -->
  <section class="chart-card" style="margin-bottom: 28px;">
    <div class="chart-header">
      <div>
        <div class="chart-title">🧬 5W1H 이벤트 튜플 · 정량 근거 (전처리 세밀화 반영)</div>
        <div class="chart-subtitle"><code>event_tuple</code>의 행위자(who)·시점(when)·정량 수치(extracted_metrics)는 전처리 추출 스냅샷입니다. 경보 확정 근거가 아니며, Risk Signal Score와 Alert Level 산식에는 사용되지 않습니다.</div>
      </div>
      <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
        <span class="kpi-tag tag-info" style="font-size:11px;">📦 High-Purity {html.escape(str(high_ref.get('file_name', '확인 필요')))}</span>
        <span class="kpi-tag tag-amber" style="font-size:11px;">🔎 근거 없는 항목은 '확인 필요'</span>
      </div>
    </div>
    <div class="refine-grid">{refine_tiles_html}</div>
    <div style="overflow-x: auto;">
      <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
        <thead>
          <tr style="border-bottom: 1px solid rgba(255,255,255,0.12); text-align: left;">
            <th style="padding: 8px;">이벤트 (원문 링크)</th>
            <th style="padding: 8px;">행위자 (who)</th>
            <th style="padding: 8px;">행위 · 대상</th>
            <th style="padding: 8px;">장소 (where)</th>
            <th style="padding: 8px;">시점 (when)</th>
            <th style="padding: 8px;">정량 수치 (extracted_metrics)</th>
            <th style="padding: 8px;">검증 상태 · 전처리 심각도</th>
            <th style="padding: 8px;">근거 두께</th>
          </tr>
        </thead>
        <tbody>
          {event_tuple_rows_html}
        </tbody>
      </table>
    </div>
    <p style="font-size: 11px; color: var(--text-muted); margin-top: 12px; line-height: 1.6;">
      위 표는 High-Purity 클러스터 {html.escape(str(high_ref.get('cluster_count', 0)))}건 중 정량 수치를 확보한 {evidence_metric_hits}건을 포함해 근거 두께 순으로 표시한 것입니다.
      <b>전처리 심각도</b>는 문구 규칙 기반 잠정 판정이고 <code>verification_state</code>가 <code>UNVERIFIED</code>인 행이 대부분이므로, 사람이 원문 링크를 확인한 뒤 검토 후보로만 다뤄야 합니다.
    </p>
  </section>

  <!-- GIS Spatial Risk Overlay Section (Auxiliary Indicator Only) -->
  <section class="chart-card" style="margin-bottom: 28px;">
    <div class="chart-header" style="flex-wrap: wrap; gap: 10px;">
      <div>
        <div class="chart-title">🗺️ GIS · 공급망 공간 리스크 중첩 지도 (5대 해협 · 6대 반도체/희토류 거점)</div>
        <div class="chart-subtitle"><code>EPSG:4326 → {html.escape(spatial_crs_label)}</code> 등적 미터 투영 기반 {int(spatial_buffer_km)}km 버퍼 중첩(<code>gpd.sjoin</code>) 및 최단거리 산출 결과입니다. <b>공간 노출도는 보조 지표</b>이며 결정론적 경보 산식(<code>calculate_alert_assessment</code>)에는 반영되지 않습니다.</div>
      </div>
      <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
        <span class="kpi-tag tag-info" style="font-size:11px;">🌐 GeoPandas {html.escape(spatial_gpd_ver)} · {int(spatial_buffer_km)}km 버퍼</span>
        <span class="kpi-tag tag-amber" style="font-size:11px;">🛡️ 보조 지표 (공식 경보 산식 미연결)</span>
      </div>
    </div>
    <div class="refine-grid">{spatial_tiles_html}</div>
    <div class="spatial-toolbar">
      <button type="button" class="pill-btn active" onclick="focusSpatialAsset(24, 55, 2, this)">🌍 전체 글로벌 뷰</button>
      <button type="button" class="pill-btn" onclick="focusSpatialAsset(21.5, 38.0, 5, this)">⚓ 홍해·수에즈</button>
      <button type="button" class="pill-btn" onclick="focusSpatialAsset(23.8, 120.2, 6, this)">🔬 대만 해협·TSMC</button>
      <button type="button" class="pill-btn" onclick="focusSpatialAsset(26.35, 56.35, 6, this)">⛽ 호르무즈</button>
      <button type="button" class="pill-btn" onclick="focusSpatialAsset(37.04, 127.06, 6, this)">🇰🇷 한국 반도체</button>
      <button type="button" class="pill-btn" onclick="focusSpatialAsset(33.45, -112.07, 5, this)">🇺🇸 애리조나 팹</button>
      <button type="button" class="pill-btn" onclick="focusSpatialAsset(51.41, 5.41, 5, this)">🇳🇱 ASML EUV</button>
      <button type="button" class="pill-btn" onclick="focusSpatialAsset(9.1, -79.75, 6, this)">🚢 파나마 운하</button>
      <button type="button" class="pill-btn" onclick="focusSpatialAsset(3.25, 102.0, 6, this)">⚓ 말라카 해협</button>
    </div>
    <div id="spatialRiskMap" class="spatial-map-canvas"></div>
    <div class="spatial-legend-bar">
      <span><i class="legend-swatch" style="background:rgba(239,68,68,0.45);border:1.5px solid #ef4444;"></i> HIGH 노출 해협/거점</span>
      <span><i class="legend-swatch" style="background:rgba(245,158,11,0.4);border:1.5px solid #f59e0b;"></i> MODERATE 노출</span>
      <span><i class="legend-swatch" style="background:rgba(56,189,248,0.35);border:1.5px solid #38bdf8;"></i> LOW 노출</span>
      <span><i class="legend-swatch" style="background:rgba(148,163,184,0.25);border:1.5px solid #94a3b8;"></i> NONE (반경 외)</span>
      <span><i class="legend-swatch legend-circle" style="border:1.5px dashed #38bdf8;background:rgba(56,189,248,0.12);"></i> {int(spatial_buffer_km)}km 영향 반경</span>
      <span><i class="legend-swatch legend-circle" style="background:#f43f5e;border:1.5px solid #fff;"></i> Tier-1 포함 신호 클러스터</span>
      <span style="margin-left:auto;color:var(--text-muted);">우측 상단 레이어 컨트롤로 해협·거점·반경·신호 토글 가능</span>
    </div>
    <div style="overflow-x: auto; margin-top: 16px;">
      <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
        <thead>
          <tr style="border-bottom: 1px solid rgba(255,255,255,0.12); text-align: left;">
            <th style="padding: 8px;">공급망 자산 (ID · 섹터)</th>
            <th style="padding: 8px;">지형 유형</th>
            <th style="padding: 8px;">공간 노출도 (보조)</th>
            <th style="padding: 8px;">{int(spatial_buffer_km)}km 중첩 신호</th>
            <th style="padding: 8px;">Tier-1 중첩</th>
            <th style="padding: 8px;">최단 신호 거리</th>
            <th style="padding: 8px;">포커스</th>
          </tr>
        </thead>
        <tbody>
          {spatial_asset_rows_html}
        </tbody>
      </table>
    </div>
  </section>

  <!-- Google Trends & 5 Local Opinion Sensors Section -->
  <section class="charts-grid" style="margin-bottom: 28px;">
    <div class="chart-card">
      <div class="chart-header">
        <div>
          <div class="chart-title">🔍 구글 트렌드 검색량 급등 신호 (Google Trends Surge Radar)</div>
          <div class="chart-subtitle">국민 여론이 아닌 온라인 검색 행동 신호입니다. 검색량만으로 Alert Level을 확정하지 않습니다.</div>
        </div>
      </div>
      <div style="overflow-y: auto; max-height: 380px;">
        {gt_cards_html}
      </div>
    </div>

    <div class="chart-card">
      <div class="chart-header">
        <div>
          <div class="chart-title">🌐 공개 포럼·SNS 정보환경 신호 (Local Forums & SNS)</div>
          <div class="chart-subtitle">대만 PTT, 중국 핀충(品葱), Bluesky, 구글 로컬 뉴스, 공개 Telegram — 국민 전체 여론이 아닌 온라인 표현 신호</div>
        </div>
      </div>
      <div style="overflow-y: auto; max-height: 380px;">
        {lo_rows_html}
      </div>
    </div>
  </section>

  <!-- Multi-Sensor Cross-Verification Engine Section -->
  <section class="charts-grid" style="margin-bottom: 28px;">
    <div class="chart-card" style="grid-column: 1 / -1;">
      <div class="chart-header" style="flex-wrap: wrap; gap: 8px;">
        <div>
          <div class="chart-title">⚖️ 다중 계통 교차검증 레이더 (Multi-Channel Cross-Verification Engine)</div>
          <div class="chart-subtitle">GDELT 사건 + 해협/항만 인프라 + 해상운임/에너지 시장 + 온라인 정보환경 + 공개 Telegram 주장 간 시계열 교차검증 ({state_counts_text})</div>
        </div>
        <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
          <span class="kpi-tag tag-amber" style="font-size:11px;">⚠️ 부분 수집 1페이지 예산 프로브 ({'complete=false' if is_partial_cov else 'complete=true'})</span>
          <span class="kpi-tag tag-info" style="font-size:11px;">🔒 단일 출처 경보 상승 금지: {'엄격 준수 (Active)' if single_source_forbidden else '비활성'}</span>
        </div>
      </div>
      <div style="overflow-y: auto; max-height: 480px;">
        {cv_cards_html}
      </div>
    </div>
  </section>
"""
    
    # Alert Level is read only from v_dashboard_current_alerts.
    alert_counts = {"Critical": 0, "Warning": 0, "Watch": 0, "Normal": 0, "확인 필요": 0}
    warning_rows = []
    if warning_snapshot_available:
        for item in warning_snapshot:
            raw_level = str(item.get("alert_level") or "확인 필요")
            level = "Normal" if raw_level.upper() == "NO_ALERT" else raw_level.title()
            normalized = level if level in alert_counts else "확인 필요"
            alert_counts[normalized] += 1
            warning_rows.append(f"""
              <article class="warning-item">
                <div class="warning-head"><strong>{html.escape(str(item.get('issue') or '미지정 이슈'))}</strong><span class="badge badge-{'red' if normalized in ('Warning', 'Critical') else 'amber' if normalized == 'Watch' else 'blue'}">{html.escape(normalized)}</span></div>
                <p><b>위험 신호:</b> {html.escape(str(item.get('risk_signal_summary') or '확인 필요'))}</p>
                <p><b>신호 괴리:</b> {html.escape(str(item.get('signal_gap_summary') or '확인 필요'))}</p>
                <p class="text-muted"><b>근거 범위:</b> {html.escape(str(item.get('evidence_coverage') or '확인 필요'))} · <b>검증 상태:</b> {html.escape(str(item.get('validation_status') or '확인 필요'))}</p>
              </article>""")
    else:
        alert_counts["확인 필요"] = total_issues
        if warning_snapshot_status == "official_view_empty":
            warning_rows.append("""
          <article class="warning-item warning-pending">
            <div class="warning-head"><strong>공식 경보 뷰 연결됨 · 최신 산출 스냅샷 없음</strong><span class="badge badge-amber">확인 필요</span></div>
            <p>MySQL 공식 뷰 <code>v_dashboard_current_alerts</code>는 연결됐지만, 완료된 점수 실행과 경보 이벤트가 아직 없어 Alert Level을 표시하지 않습니다.</p>
            <p class="text-muted">DB/분석 담당이 공식 scoring run과 사람 검토 상태를 적재한 뒤 다시 생성해야 합니다.</p>
          </article>""")
        else:
            warning_rows.append("""
          <article class="warning-item warning-pending">
            <div class="warning-head"><strong>공식 경보 뷰 미연결</strong><span class="badge badge-amber">확인 필요</span></div>
            <p>수집·논조 데이터는 표시되지만, 공식 Alert Level 뷰를 읽지 못해 경보를 확정해 표시하지 않습니다.</p>
          </article>""")
    warning_cards_html = "\n".join(warning_rows)

    # Chart 1: 지정학적 리스크 산점도/버블 데이터 가공
    bubble_datasets = []
    for item in matrix:
        intensity = float(item["public_intensity"] or 0)
        gov_matches = int(item["total_gov_matches"] or 0)
        pageviews = float(item["wiki_total_pageviews"] or 1000)
        radius = max(6, min(24, int((pageviews ** 0.5) / 18)))
        status = str(item.get("diplomatic_status", ""))
        
        is_gap = "CRITICAL_GAP" in status
        color = "rgba(239, 68, 68, 0.85)" if is_gap else ("rgba(16, 185, 129, 0.85)" if gov_matches > 5 else "rgba(56, 189, 248, 0.75)")
        border = "#fca5a5" if is_gap else ("#6ee7b7" if gov_matches > 5 else "#bae6fd")

        bubble_datasets.append({
            "label": item["issue"],
            "data": [{"x": intensity, "y": gov_matches, "r": radius, "issue": item["issue"], "views": int(pageviews), "status": status}],
            "backgroundColor": color,
            "borderColor": border,
            "borderWidth": 1.5,
        })

    # Chart 2: 미디어 톤 분석 데이터 가공 (상위 8개 이슈 집계)
    tone_agg = {}
    for f in framing:
        iss = f["issue"]
        if not iss:
            continue
        if iss not in tone_agg:
            tone_agg[iss] = {"pos": 0, "neu": 0, "crit": 0, "total": 0}
        tone_agg[iss]["pos"] += int(f.get("positive_count") or 0)
        tone_agg[iss]["neu"] += int(f.get("neutral_count") or 0)
        tone_agg[iss]["crit"] += int(f.get("critical_count") or 0)
        tone_agg[iss]["total"] += int(f.get("total_articles") or 0)

    # 정렬: 기사 많은 순 상위 7개
    sorted_issues = sorted(tone_agg.items(), key=lambda x: x[1]["total"], reverse=True)[:7]
    tone_labels = [s[0] for s in sorted_issues]
    tone_pos = [s[1]["pos"] for s in sorted_issues]
    tone_neu = [s[1]["neu"] for s in sorted_issues]
    tone_crit = [s[1]["crit"] for s in sorted_issues]

    # Chart 3: 정부 발표 출처 도넛 데이터
    source_labels = [s["source"] for s in gov_sources[:6]]
    source_values = [int(s["cnt"]) for s in gov_sources[:6]]

    # JSON 데이터 주입
    bubble_json = json.dumps(bubble_datasets, default=custom_json_serializer)
    tone_labels_json = json.dumps(tone_labels, default=custom_json_serializer)
    tone_pos_json = json.dumps(tone_pos, default=custom_json_serializer)
    tone_neu_json = json.dumps(tone_neu, default=custom_json_serializer)
    tone_crit_json = json.dumps(tone_crit, default=custom_json_serializer)
    source_labels_json = json.dumps(source_labels, default=custom_json_serializer)
    source_values_json = json.dumps(source_values, default=custom_json_serializer)

    # HTML 테이블 행 생성
    table_rows = []
    for item in feed:
        llm_label = (item.get("llm_label") or "").strip()
        human_label = (item.get("human_label") or "").strip()

        # 라벨 배지 클래스
        badge_cls = "badge-gray"
        display_label = llm_label or "미분류"
        if llm_label == "비판적":
            badge_cls = "badge-red"
        elif llm_label == "우호적":
            badge_cls = "badge-green"
        elif llm_label == "중립적":
            badge_cls = "badge-blue"

        human_tag = f'<span class="badge badge-purple" title="검수완료">{human_label}</span>' if human_label else '<span class="text-muted text-xs">미검수</span>'

        evidence = item.get("llm_evidence_quote") or ""
        evidence_html = f'<div class="evidence-quote" title="{evidence}">💡 {evidence[:65]}...</div>' if evidence else ""

        title = item.get("title") or "제목 없음"
        link = item.get("link") or "#"
        source = item.get("source_type") or "news"
        issue = item.get("issue_ids") or "일반"
        issue_clean = issue.strip("[]'\" ") if issue else "미지정"

        # PHASE2_THINKTANK_REDDIT_HANDOFF.md: expert_analysis(싱크탱크)는 일반
        # badge-source 대신 별도 골드 뱃지로 시각적으로 최우선 강조.
        if source == "expert_analysis":
            source_badge = '<span class="badge badge-thinktank">🧠 전문가 분석 (Think Tank)</span>'
        else:
            source_badge = f'<span class="badge badge-source">{source}</span>'

        table_rows.append(f"""
        <tr class="feed-row" data-issue="{issue_clean}" data-source="{source}" data-tone="{display_label}">
            <td class="font-mono text-xs text-muted">{item.get('article_id', '')[:8]}</td>
            <td><span class="badge badge-outline">{issue_clean}</span></td>
            <td>
                <a href="{link}" target="_blank" class="headline-link">{title}</a>
                {evidence_html}
            </td>
            <td>{source_badge}</td>
            <td><span class="badge {badge_cls}">{display_label}</span></td>
            <td>{human_tag}</td>
        </tr>
        """)
    feed_tbody = "\n".join(table_rows)

    # 템플릿 렌더링
    html_output = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>국제정세 인텔리전스 레이더 (Geopolitical Radar Dashboard)</title>
<!-- Google Fonts & Chart.js -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin="" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
<style>
  :root {{
    --bg-main: #0a0e17;
    --bg-card: #111827;
    --bg-card-hover: #162033;
    --border: rgba(255, 255, 255, 0.08);
    --border-strong: rgba(255, 255, 255, 0.15);
    --text-main: #f8fafc;
    --text-muted: #94a3b8;
    --accent-cyan: #38bdf8;
    --accent-blue: #3b82f6;
    --accent-indigo: #6366f1;
    --accent-green: #10b981;
    --accent-red: #ef4444;
    --accent-amber: #f59e0b;
    --accent-purple: #a855f7;
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    background-color: var(--bg-main);
    color: var(--text-main);
    min-height: 100vh;
    padding: 24px 32px 60px;
    background-image: radial-gradient(circle at 10% 10%, rgba(56, 189, 248, 0.04) 0%, transparent 40%),
                      radial-gradient(circle at 90% 90%, rgba(99, 102, 241, 0.04) 0%, transparent 40%);
  }}

  /* Top Navigation Bar */
  .top-nav {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 24px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 28px;
    flex-wrap: wrap;
    gap: 16px;
  }}
  .brand-area {{ display: flex; align-items: center; gap: 14px; }}
  .brand-icon {{
    width: 42px; height: 42px;
    background: linear-gradient(135deg, var(--accent-cyan), var(--accent-indigo));
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; box-shadow: 0 0 20px rgba(56, 189, 248, 0.3);
  }}
  .brand-title {{ font-size: 20px; font-weight: 800; letter-spacing: -0.5px; }}
  .brand-sub {{ font-size: 12px; color: var(--text-muted); margin-top: 2px; }}

  .status-badges {{ display: flex; gap: 10px; align-items: center; }}
  .live-pill {{
    display: flex; align-items: center; gap: 6px;
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.3);
    color: var(--accent-green);
    padding: 6px 14px; border-radius: 20px;
    font-size: 12px; font-weight: 600;
  }}
  .live-dot {{
    width: 8px; height: 8px; border-radius: 50%;
    background-color: var(--accent-green);
    box-shadow: 0 0 10px var(--accent-green);
    animation: pulse 2s infinite;
  }}
  @keyframes pulse {{
    0% {{ opacity: 0.4; }}
    50% {{ opacity: 1; }}
    100% {{ opacity: 0.4; }}
  }}
  .time-badge {{
    font-size: 12px; color: var(--text-muted);
    background: var(--bg-card); padding: 6px 12px;
    border-radius: 8px; border: 1px solid var(--border);
    font-family: 'JetBrains Mono', monospace;
  }}

  /* Executive KPI Cards Grid */
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 16px;
    margin-bottom: 28px;
  }}
  .warning-overview {{ margin: 0 0 28px; }}
  .warning-overview h2 {{ font-size: 18px; margin-bottom: 6px; }}
  .warning-overview > p {{ color: var(--text-muted); font-size: 13px; margin-bottom: 14px; }}
  .warning-list {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(290px, 1fr)); gap: 12px; }}
  .warning-item {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 16px; }}
  .warning-pending {{ border-left: 3px solid var(--accent-amber); }}
  .warning-head {{ display:flex; justify-content:space-between; gap:10px; align-items:center; margin-bottom:10px; }}
  .warning-item p {{ font-size: 12px; line-height: 1.55; margin: 5px 0; }}
  .axis-section {{ background: #06090f; border: 1px solid #1f2b3b; border-radius: 16px; padding: 22px; margin-bottom: 28px; }}
  .axis-section-head {{ display:flex; justify-content:space-between; align-items:flex-start; gap:16px; margin-bottom:12px; }}
  .section-eyebrow {{ color:#29c7d1; font-size:11px; font-weight:700; letter-spacing:.08em; }}
  .axis-section h2 {{ color:#edf2fa; font-size:25px; margin:5px 0; }}
  .axis-section-head p {{ color:#8c9eb8; font-size:13px; margin:0; }}
  .axis-live {{ background:#121a29; border:1px solid #243045; border-radius:10px; color:#4dc785; font-size:11px; font-weight:700; padding:12px 15px; white-space:nowrap; }}
  .axis-banner {{ display:flex; justify-content:space-between; gap:12px; background:#4d0b11; border:1px solid #d11f26; border-radius:5px; color:#ffc7c7; font-size:10px; font-weight:700; padding:7px 12px; margin-bottom:14px; }}
  .axis-banner strong {{ color:#ffb8b8; }}
  .axis-grid {{ display:grid; grid-template-columns:repeat(5, minmax(0, 1fr)); gap:10px; }}
  .axis-card {{ background:#111725; border:1px solid #212e40; border-radius:13px; min-height:190px; padding:15px; }}
  .axis-kicker {{ color:#8c9eb8; font-size:10px; font-weight:700; letter-spacing:.06em; }}
  .axis-card h3 {{ color:#edf2fa; font-size:14px; margin:14px 0 4px; }}
  .axis-subtitle {{ color:#8c9eb8; font-size:11px; min-height:28px; margin:0 0 12px; }}
  .axis-status {{ background:#31220d; border-radius:10px; color:#f5a840; display:inline-block; font-size:9px; font-weight:700; padding:5px 8px; }}
  .axis-metric {{ color:#edf2fa; font-size:22px; font-weight:700; margin-top:16px; }}
  .axis-sensors {{ border-top:1px solid #293347; color:#29c7d1; font-size:10px; margin:14px 0 0; padding-top:10px; }}
  @media (max-width: 1100px) {{ .axis-grid {{ grid-template-columns:repeat(2, minmax(0, 1fr)); }} }}
  @media (max-width: 620px) {{ .axis-section-head, .axis-banner {{ flex-direction:column; }} .axis-grid {{ grid-template-columns:1fr; }} }}
  .kpi-card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 20px;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s, border-color 0.2s;
  }}
  .kpi-card:hover {{
    transform: translateY(-2px);
    border-color: var(--border-strong);
  }}
  .kpi-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
  .kpi-label {{ font-size: 13px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}
  .kpi-icon {{ font-size: 18px; opacity: 0.8; }}
  .kpi-value {{ font-size: 32px; font-weight: 800; letter-spacing: -1px; }}
  .kpi-desc {{ font-size: 12px; color: var(--text-muted); margin-top: 6px; display: flex; align-items: center; gap: 6px; }}
  .kpi-tag {{ padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; }}
  .tag-danger {{ background: rgba(239, 68, 68, 0.15); color: var(--accent-red); }}
  .tag-success {{ background: rgba(16, 185, 129, 0.15); color: var(--accent-green); }}
  .tag-info {{ background: rgba(56, 189, 248, 0.15); color: var(--accent-cyan); }}
  .tag-amber {{ background: rgba(245, 158, 11, 0.15); color: var(--accent-amber); }}
  .refine-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(215px, 1fr)); gap: 12px; margin-bottom: 18px; }}
  .refine-tile {{ background: rgba(0, 0, 0, 0.25); border: 1px solid var(--border); border-radius: 8px; padding: 13px 15px; }}
  .refine-label {{ font-size: 11px; color: var(--text-muted); font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; }}
  .refine-value {{ font-size: 22px; font-weight: 800; margin-top: 6px; color: var(--accent-cyan); }}
  .refine-sub {{ font-size: 11px; color: var(--text-muted); margin-top: 6px; line-height: 1.55; }}

  /* GIS Spatial Map Styles */
  .spatial-toolbar {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }}
  .spatial-map-canvas {{
    width: 100%; height: 470px; border-radius: 10px;
    border: 1px solid var(--border-strong); background: #070b14;
    z-index: 1;
  }}
  .spatial-legend-bar {{
    display: flex; flex-wrap: wrap; gap: 14px; align-items: center;
    margin-top: 10px; padding: 8px 12px; border-radius: 8px;
    background: rgba(0, 0, 0, 0.25); border: 1px solid var(--border);
    font-size: 11px; color: var(--text-main);
  }}
  .legend-swatch {{
    display: inline-block; width: 12px; height: 12px; border-radius: 3px;
    vertical-align: middle; margin-right: 5px;
  }}
  .legend-circle {{ border-radius: 50%; }}
  .leaflet-popup-content-wrapper, .leaflet-popup-tip {{
    background: #0f172a; color: #f8fafc; border: 1px solid rgba(148, 163, 184, 0.35);
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.55);
  }}
  .leaflet-popup-content {{ font-family: 'Plus Jakarta Sans', sans-serif; font-size: 12px; line-height: 1.5; }}
  .leaflet-control-layers {{
    background: rgba(15, 23, 42, 0.92) !important; color: #f8fafc !important;
    border: 1px solid rgba(148, 163, 184, 0.3) !important; border-radius: 8px !important;
  }}
  .leaflet-container a {{ color: #38bdf8; }}

  /* Chart Layout Grid */
  .charts-grid {{
    display: grid;
    grid-template-columns: 2fr 1.2fr;
    gap: 20px;
    margin-bottom: 28px;
  }}
  @media (max-width: 1024px) {{
    .charts-grid {{ grid-template-columns: 1fr; }}
  }}
  .chart-card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 24px;
    display: flex; flex-direction: column;
  }}
  .chart-header {{
    display: flex; justify-content: space-between; align-items: flex-start;
    margin-bottom: 20px;
  }}
  .chart-title {{ font-size: 16px; font-weight: 700; display: flex; align-items: center; gap: 8px; }}
  .chart-subtitle {{ font-size: 12px; color: var(--text-muted); margin-top: 4px; }}
  .chart-canvas-box {{ position: relative; flex: 1; min-height: 280px; }}

  /* Lower Charts Grid */
  .secondary-charts {{
    display: grid;
    grid-template-columns: 1.2fr 1fr;
    gap: 20px;
    margin-bottom: 28px;
  }}
  @media (max-width: 900px) {{
    .secondary-charts {{ grid-template-columns: 1fr; }}
  }}

  /* Intelligence Feed Table Section */
  .feed-section {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 24px;
  }}
  .feed-toolbar {{
    display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 14px; margin-bottom: 20px;
  }}
  .search-input {{
    background: var(--bg-main);
    border: 1px solid var(--border);
    color: var(--text-main);
    padding: 10px 16px; border-radius: 8px;
    font-size: 13px; width: 280px;
    outline: none; transition: border-color 0.2s;
  }}
  .search-input:focus {{ border-color: var(--accent-cyan); }}

  .filter-pills {{ display: flex; gap: 8px; }}
  .pill-btn {{
    background: var(--bg-main);
    border: 1px solid var(--border);
    color: var(--text-muted);
    padding: 8px 14px; border-radius: 8px;
    font-size: 12px; font-weight: 600; cursor: pointer;
    transition: all 0.2s;
  }}
  .pill-btn.active, .pill-btn:hover {{
    background: rgba(56, 189, 248, 0.12);
    border-color: var(--accent-cyan);
    color: var(--accent-cyan);
  }}

  /* Table Styles */
  .table-container {{
    width: 100%; overflow-x: auto;
  }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }}
  th {{
    color: var(--text-muted); font-weight: 600; font-size: 11px;
    text-transform: uppercase; letter-spacing: 0.5px;
    padding: 12px 14px; border-bottom: 1px solid var(--border);
    background: rgba(0, 0, 0, 0.2);
  }}
  td {{
    padding: 14px; border-bottom: 1px solid var(--border);
    vertical-align: middle;
  }}
  tr.feed-row:hover {{ background-color: var(--bg-card-hover); }}

  .headline-link {{
    color: var(--text-main); text-decoration: none; font-weight: 600;
    transition: color 0.2s; line-height: 1.4; display: inline-block;
  }}
  .headline-link:hover {{ color: var(--accent-cyan); text-decoration: underline; }}
  .evidence-quote {{
    font-size: 11px; color: var(--text-muted);
    background: rgba(0, 0, 0, 0.25);
    padding: 4px 8px; border-radius: 4px; margin-top: 6px;
    border-left: 2px solid var(--accent-amber);
    display: inline-block;
  }}

  /* Badges */
  .badge {{
    display: inline-block; padding: 3px 8px; border-radius: 4px;
    font-size: 11px; font-weight: 700; white-space: nowrap;
  }}
  .badge-outline {{ background: transparent; border: 1px solid var(--border); color: var(--text-muted); }}
  .badge-source {{ background: rgba(99, 102, 241, 0.15); color: #a5b4fc; }}
  .badge-red {{ background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }}
  .badge-green {{ background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }}
  .badge-blue {{ background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }}
  .badge-gray {{ background: rgba(148, 163, 184, 0.12); color: #94a3b8; }}
  .badge-purple {{ background: rgba(168, 85, 247, 0.15); color: #c084fc; }}
  .badge-thinktank {{
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.18), rgba(245, 158, 11, 0.08));
    color: var(--accent-amber);
    border: 1px solid rgba(245, 158, 11, 0.4);
    font-weight: 800;
  }}

  /* Footer */
  .footer {{
    margin-top: 40px; text-align: center; font-size: 12px; color: var(--text-muted);
    padding-top: 20px; border-top: 1px solid var(--border);
  }}
</style>
</head>
<body>

  <!-- Top Navigation -->
  <header class="top-nav">
    <div class="brand-area">
      <div class="brand-icon">🌐</div>
      <div>
        <div class="brand-title">GEOPOLITICAL EARLY-WARNING DASHBOARD</div>
        <div class="brand-sub">관측 신호 기반 조기경보 · 위험 신호, 근거 출처, 검증 상태를 함께 확인</div>
      </div>
    </div>
    <div class="status-badges">
      <div class="live-pill"><span class="live-dot"></span> EARLY-WARNING SNAPSHOT</div>
      <div class="time-badge">생성: {data['generated_at']}</div>
    </div>
  </header>

  <!-- KPI Scorecards -->
  <section class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-header">
        <span class="kpi-label">추적 중인 글로벌 이슈</span>
        <span class="kpi-icon">🎯</span>
      </div>
      <div class="kpi-value" style="color: var(--accent-cyan);">{total_issues}개</div>
      <div class="kpi-desc">전 세계 6대륙 21개 핵심 지정학 갈등</div>
    </div>

    <div class="kpi-card">
      <div class="kpi-header">
        <span class="kpi-label">Critical / Warning 단계</span>
        <span class="kpi-icon">⚠️</span>
      </div>
      <div class="kpi-value" style="color: var(--accent-red);">{alert_counts['Critical']}건</div>
      <div class="kpi-desc"><span class="kpi-tag tag-danger">경보</span> 검증 가능한 근거와 함께 제시되는 주의 이슈</div>
    </div>

    <div class="kpi-card">
      <div class="kpi-header">
        <span class="kpi-label">Watch 단계</span>
        <span class="kpi-icon">🏛️</span>
      </div>
      <div class="kpi-value" style="color: var(--accent-indigo);">{alert_counts['Watch']}건</div>
      <div class="kpi-desc">위험 신호를 관찰 중이며 추가 확인이 필요한 이슈</div>
    </div>

    <div class="kpi-card">
      <div class="kpi-header">
        <span class="kpi-label">사람 검수 일치율</span>
        <span class="kpi-icon">🧠</span>
      </div>
      <div class="kpi-value" style="color: var(--accent-green);">{hitl_accuracy:.1f}%</div>
      <div class="kpi-desc"><span class="kpi-tag tag-success">HITL</span> LLM 1차 라벨 vs 인간 2차 교차검증</div>
    </div>
  </section>

  <section class="warning-overview">
    <h2>🚨 이슈별 조기경보 현황</h2>
    <p>Alert Level은 확정적 사건 전망이 아니라 관측된 위험 신호와 근거 범위를 바탕으로 한 현재의 주의 수준입니다.</p>
    <div class="warning-list">{warning_cards_html}</div>
  </section>

  {new_section_html}

  <!-- Main Charts Grid -->
  <section class="charts-grid">
    <!-- Chart 1: Geopolitical Risk Radar -->
    <div class="chart-card">
      <div class="chart-header">
        <div>
          <div class="chart-title">📍 보조 관측 신호 (대중 관심도 vs 정부 공식 대응)</div>
          <div class="chart-subtitle">Alert Level 산식이 아닌 수집·관측 현황입니다. 원 크기 = 위키백과 검색량</div>
        </div>
      </div>
      <div class="chart-canvas-box">
        <canvas id="riskBubbleChart"></canvas>
      </div>
    </div>

    <!-- Chart 2: Media Framing Analysis -->
    <div class="chart-card">
      <div class="chart-header">
        <div>
          <div class="chart-title">📊 위험 신호 보조 근거: 미디어 프레이밍</div>
          <div class="chart-subtitle">LLM 1차 논조 분류이며, 단독으로 경보 단계를 결정하지 않습니다.</div>
        </div>
      </div>
      <div class="chart-canvas-box">
        <canvas id="toneBarChart"></canvas>
      </div>
    </div>
  </section>

  <!-- Secondary Charts Grid -->
  <section class="secondary-charts">
    <!-- Chart 3: Gov Announcement Sources -->
    <div class="chart-card">
      <div class="chart-header">
        <div>
          <div class="chart-title">🏛️ 정부 공식 발표 수집 출처 비중</div>
          <div class="chart-subtitle">공식 외교 보도자료 및 국영 매체 채널 분포</div>
        </div>
      </div>
      <div class="chart-canvas-box" style="max-height: 250px;">
        <canvas id="sourceDoughnutChart"></canvas>
      </div>
    </div>

    <!-- Chart 4: HITL Audit Summary -->
    <div class="chart-card">
      <div class="chart-header">
        <div>
          <div class="chart-title">🛡️ 검증 상태: 사람 표본 검수</div>
          <div class="chart-subtitle">경보 품질을 확인하는 검수 현황이며, 예측 정확도가 아닙니다.</div>
        </div>
      </div>
      <div style="display: flex; flex-direction: column; justify-content: space-around; height: 100%; padding: 10px 0;">
        <div style="background: rgba(0,0,0,0.25); padding: 14px; border-radius: 8px; border-left: 3px solid var(--accent-cyan);">
          <div style="font-size: 12px; color: var(--text-muted);">모델-인간 일치율</div>
          <div style="font-size: 22px; font-weight: 700; color: var(--accent-cyan);">{hitl_accuracy:.1f}% ({total_agreed}건 일치 / {total_reviewed}건 검수)</div>
        </div>
        <div style="background: rgba(0,0,0,0.25); padding: 14px; border-radius: 8px; border-left: 3px solid var(--accent-amber);">
          <div style="font-size: 12px; color: var(--text-muted);">근거 품질 확인</div>
          <div style="font-size: 18px; font-weight: 700; color: var(--accent-amber);">경보별 근거·출처·과도한 해석 여부를 표본 검수</div>
          <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">근거가 부족한 경우에는 경보 확정 대신 ‘확인 필요’로 표시합니다.</div>
        </div>
        <div style="background: rgba(0,0,0,0.25); padding: 14px; border-radius: 8px; border-left: 3px solid var(--accent-purple);">
          <div style="font-size: 12px; color: var(--text-muted);">백테스트·오탐·미탐 기록</div>
          <div style="font-size: 13px; color: #e2e8f0; margin-top: 2px;">과거 사례의 Watch/Warning 포착 여부와 오탐·미탐 후보를 별도 기록합니다.</div>
        </div>
      </div>
    </div>
  </section>

  <!-- Live Intelligence Feed Table -->
  <section class="feed-section">
    <div class="feed-toolbar">
      <div>
        <div style="font-size: 16px; font-weight: 700;">📡 근거 출처 및 위험 신호 피드</div>
        <div style="font-size: 12px; color: var(--text-muted);">경보 판단에 사용될 수 있는 원문·LLM 추출 근거입니다. 개별 항목은 경보 확정이 아닙니다.</div>
      </div>
      <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
        <input type="text" id="feedSearch" class="search-input" placeholder="이슈명, 기사 제목 검색...">
        <div class="filter-pills">
          <button class="pill-btn active" onclick="filterTable('all', this)">전체</button>
          <button class="pill-btn" onclick="filterTable('비판적', this)">비판적 톤</button>
          <button class="pill-btn" onclick="filterTable('중립적', this)">중립적 톤</button>
          <button class="pill-btn" onclick="filterTable('expert_analysis', this)">전문가 분석</button>
        </div>
      </div>
    </div>

    <div class="table-container">
      <table id="feedTable">
        <thead>
          <tr>
            <th style="width: 70px;">ID</th>
            <th style="width: 150px;">이슈</th>
            <th>기사 제목 & 추출 근거</th>
            <th style="width: 100px;">출처</th>
            <th style="width: 85px;">LLM 라벨</th>
            <th style="width: 85px;">인간 검수</th>
          </tr>
        </thead>
        <tbody>
          {feed_tbody}
        </tbody>
      </table>
    </div>
  </section>

  <footer class="footer">
    국제정세·공급망 리스크 조기경보 시스템 · 관측 신호, 근거 출처, 사람 검수 및 검증 상태를 함께 제시
  </footer>

  <!-- Chart.js Initialization Script -->
  <script>
    // 1. 지정학적 리스크 레이더 (Bubble / Scatter Chart)
    const bubbleData = {bubble_json};
    const ctxBubble = document.getElementById('riskBubbleChart').getContext('2d');
    new Chart(ctxBubble, {{
      type: 'bubble',
      data: {{ datasets: bubbleData }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ display: false }},
          tooltip: {{
            callbacks: {{
              label: function(ctx) {{
                const d = ctx.raw;
                return `${{d.issue}}: 대중관심 ${{d.x}}점 / 정부발표 ${{d.y}}건 (검색량: ${{d.views.toLocaleString()}}회)`;
              }},
              afterLabel: function(ctx) {{
                return `상태: ${{ctx.raw.status}}`;
              }}
            }}
          }}
        }},
        scales: {{
          x: {{
            title: {{ display: true, text: '대중 관심도 지수 (Wikipedia Intensity, 0~100)', color: '#94a3b8' }},
            grid: {{ color: 'rgba(255, 255, 255, 0.05)' }},
            ticks: {{ color: '#94a3b8' }},
            min: 0, max: 105
          }},
          y: {{
            title: {{ display: true, text: '정부 공식 발표 매칭 건수', color: '#94a3b8' }},
            grid: {{ color: 'rgba(255, 255, 255, 0.05)' }},
            ticks: {{ color: '#94a3b8' }},
            min: 0
          }}
        }}
      }}
    }});

    // 2. 미디어 프레이밍 수평 누적 막대 차트
    const ctxTone = document.getElementById('toneBarChart').getContext('2d');
    new Chart(ctxTone, {{
      type: 'bar',
      data: {{
        labels: {tone_labels_json},
        datasets: [
          {{ label: '우호적 (Positive)', data: {tone_pos_json}, backgroundColor: '#10b981' }},
          {{ label: '중립적 (Neutral)', data: {tone_neu_json}, backgroundColor: '#64748b' }},
          {{ label: '비판적 (Critical)', data: {tone_crit_json}, backgroundColor: '#ef4444' }}
        ]
      }},
      options: {{
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ position: 'top', labels: {{ color: '#94a3b8', boxWidth: 12 }} }}
        }},
        scales: {{
          x: {{ stacked: true, grid: {{ color: 'rgba(255, 255, 255, 0.05)' }}, ticks: {{ color: '#94a3b8' }} }},
          y: {{ stacked: true, grid: {{ display: false }}, ticks: {{ color: '#f8fafc', font: {{ weight: 600 }} }} }}
        }}
      }}
    }});

    // 3. 정부 발표 소스 도넛 차트
    const ctxSource = document.getElementById('sourceDoughnutChart').getContext('2d');
    new Chart(ctxSource, {{
      type: 'doughnut',
      data: {{
        labels: {source_labels_json},
        datasets: [{{
          data: {source_values_json},
          backgroundColor: ['#38bdf8', '#818cf8', '#34d399', '#f59e0b', '#ec4899', '#94a3b8'],
          borderColor: '#111827', borderWidth: 2
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ position: 'right', labels: {{ color: '#94a3b8', font: {{ size: 11 }} }} }}
        }}
      }}
    }});

    // 실시간 피드 필터링 & 검색
    let activeFilter = 'all';
    function filterTable(filter, btn) {{
      activeFilter = filter;
      document.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
      if (btn) btn.classList.add('active');
      applyTableFilters();
    }}

    document.getElementById('feedSearch').addEventListener('input', applyTableFilters);

    function applyTableFilters() {{
      const query = document.getElementById('feedSearch').value.toLowerCase();
      const rows = document.querySelectorAll('#feedTable tbody tr.feed-row');

      rows.forEach(row => {{
        const text = row.innerText.toLowerCase();
        const tone = row.getAttribute('data-tone');
        const source = row.getAttribute('data-source');

        const matchesQuery = text.includes(query);
        let matchesFilter = true;
        if (activeFilter === '비판적' || activeFilter === '중립적' || activeFilter === '우호적') {{
          matchesFilter = (tone === activeFilter);
        }} else if (activeFilter === 'expert_analysis') {{
          matchesFilter = (source === 'expert_analysis');
        }}

        if (matchesQuery && matchesFilter) {{
          row.style.display = '';
        }} else {{
          row.style.display = 'none';
        }}
      }});
    }}

    // 4. GIS 공간 리스크 중첩 지도 (Leaflet Interactive Map)
    let spatialMapInstance = null;
    function focusSpatialAsset(lat, lon, zoom, btn) {{
      if (btn) {{
        document.querySelectorAll('.spatial-toolbar .pill-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      }}
      if (spatialMapInstance) {{
        spatialMapInstance.flyTo([lat, lon], zoom, {{ duration: 0.9 }});
      }}
    }}

    (function initSpatialRiskMap() {{
      const mapEl = document.getElementById('spatialRiskMap');
      if (!mapEl) return;
      if (typeof L === 'undefined') {{
        mapEl.innerHTML = '<div style="padding:24px;color:#94a3b8;font-size:13px;">Leaflet 지도 라이브러리를 불러오지 못했습니다 (오프라인 환경). 하단 공간 노출도 표를 참고하세요.</div>';
        return;
      }}

      const assetsGeo = {spatial_assets_json};
      const signalClusters = {spatial_clusters_json};
      const bufferMeters = {spatial_buffer_km} * 1000;

      const exposureColor = (lvl) => {{
        if (lvl === 'HIGH') return '#ef4444';
        if (lvl === 'MODERATE') return '#f59e0b';
        if (lvl === 'LOW') return '#38bdf8';
        return '#94a3b8';
      }};

      const map = L.map('spatialRiskMap', {{
        center: [24, 55],
        zoom: 2,
        minZoom: 2,
        maxZoom: 12,
        worldCopyJump: true,
      }});
      spatialMapInstance = map;

      L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
        attribution: '&copy; OpenStreetMap &copy; CARTO',
        subdomains: 'abcd',
        maxZoom: 19,
      }}).addTo(map);

      const chokepointLayer = L.layerGroup().addTo(map);
      const hubLayer = L.layerGroup().addTo(map);
      const bufferLayer = L.layerGroup().addTo(map);
      const signalLayer = L.layerGroup().addTo(map);

      const escapeHtml = (str) => String(str || '').replace(/[&<>"']/g, m => ({{
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
      }}[m]));

      // 1) 해협 Polygon & 반도체/희토류 거점 Point
      (assetsGeo.features || []).forEach(feat => {{
        const p = feat.properties || {{}};
        const g = feat.geometry || {{}};
        const lvl = p.spatial_exposure_level || 'NONE';
        const col = exposureColor(lvl);
        const popupHtml = `
          <div style="min-width:210px;">
            <div style="font-weight:800;font-size:13px;margin-bottom:4px;">${{escapeHtml(p.name)}}</div>
            <div style="color:#94a3b8;font-size:11px;margin-bottom:6px;">${{escapeHtml(p.asset_id)}} · ${{escapeHtml(p.sector)}}</div>
            <div><b>공간 노출도 (보조):</b> <span style="color:${{col}};font-weight:700;">${{escapeHtml(lvl)}}</span></div>
            <div><b>300km 중첩 신호:</b> ${{Math.round(p.overlapping_signals || 0)}}건 (Tier-1: ${{Math.round(p.tier1_overlapping || 0)}}건)</div>
            <div><b>최단 신호 거리:</b> ${{Number(p.nearest_signal_km || 0).toFixed(1)}} km</div>
          </div>
        `;

        if (g.type === 'Polygon') {{
          L.geoJSON(feat, {{
            style: {{
              color: col,
              weight: 2.2,
              fillColor: col,
              fillOpacity: lvl === 'HIGH' ? 0.34 : 0.2,
              dashArray: lvl === 'NONE' ? '4 4' : null,
            }}
          }}).bindPopup(popupHtml).bindTooltip(`${{p.name}} [${{lvl}}]`, {{ sticky: true }}).addTo(chokepointLayer);
        }} else if (g.type === 'Point' && Array.isArray(g.coordinates)) {{
          const [lon, lat] = g.coordinates;
          const marker = L.circleMarker([lat, lon], {{
            radius: lvl === 'HIGH' ? 9 : 7,
            color: '#f8fafc',
            weight: 2,
            fillColor: col,
            fillOpacity: 0.92,
          }}).bindPopup(popupHtml).bindTooltip(`${{p.name}} [${{lvl}}]`, {{ direction: 'top' }});
          marker.addTo(hubLayer);
        }}
      }});

      // 2) 300km 영향 반경 & OSINT 신호 클러스터
      signalClusters.forEach(c => {{
        const hasT1 = (c.tier1_count || 0) > 0;
        const ringColor = hasT1 ? '#f43f5e' : '#38bdf8';

        // 300km metric buffer ring
        L.circle([c.lat, c.lon], {{
          radius: bufferMeters,
          color: ringColor,
          weight: 1.2,
          dashArray: '5 5',
          fillColor: ringColor,
          fillOpacity: hasT1 ? 0.08 : 0.04,
          interactive: false,
        }}).addTo(bufferLayer);

        // Signal cluster marker
        const r = Math.max(5, Math.min(16, 4 + Math.sqrt(c.signal_count || 1) * 1.9));
        const samples = (c.sample_titles || []).map(t => `<li style="margin-top:3px;">${{escapeHtml(t)}}</li>`).join('');
        const sigPopup = `
          <div style="max-width:290px;">
            <div style="font-weight:800;font-size:13px;color:#38bdf8;">📍 ${{escapeHtml(c.place_name)}}</div>
            <div style="font-size:11px;color:#94a3b8;margin:3px 0 6px;">방식: ${{escapeHtml(c.geo_method)}} · 좌표 (${{c.lat}}, ${{c.lon}})</div>
            <div><b>지오코딩 신호:</b> ${{c.signal_count}}건 (Tier-1: <span style="color:#f87171;font-weight:700;">${{c.tier1_count}}</span> / Tier-2: ${{c.tier2_count}})</div>
            ${{samples ? `<ul style="margin:6px 0 0 14px;padding:0;font-size:11px;color:#cbd5e1;">${{samples}}</ul>` : ''}}
          </div>
        `;
        L.circleMarker([c.lat, c.lon], {{
          radius: r,
          color: '#ffffff',
          weight: 1.2,
          fillColor: hasT1 ? '#f43f5e' : '#38bdf8',
          fillOpacity: 0.78,
        }}).bindPopup(sigPopup).bindTooltip(`${{c.place_name}} (${{c.signal_count}}건)`, {{ direction: 'top' }}).addTo(signalLayer);
      }});

      L.control.layers(null, {{
        '⚓ 5대 해협 폴리곤': chokepointLayer,
        '🔬 반도체·희토류 거점': hubLayer,
        '⭕ 300km 영향 반경': bufferLayer,
        '📡 OSINT 신호 클러스터': signalLayer,
      }}, {{ collapsed: false }}).addTo(map);
    }})();
  </script>
</body>
</html>"""
    return html_output


def main():
    parser = argparse.ArgumentParser(description="인터랙티브 국제정세 분석 단일 HTML 대시보드 생성")
    parser.add_argument("--open", action="store_true", help="생성 완료 후 브라우저에서 자동 열기")
    args = parser.parse_args()

    print("=" * 65)
    print("🌐 Generating Interactive Geopolitical Intelligence Dashboard")
    print("=" * 65)

    try:
        conn = get_connection()
        print(f"✓ DB 연결 완료 ({getattr(conn, 'backend', 'unknown').upper()})")
    except Exception as e:
        print(f"✗ DB 접속 실패: {e}")
        sys.exit(1)

    data = fetch_all_dashboard_data(conn)
    conn.close()

    html_content = generate_dashboard_html(data)

    # 1. 타임스탬프 파일
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dated_file = OUTPUT_DIR / f"dashboard_{timestamp}.html"
    dated_file.write_text(html_content, encoding="utf-8")

    # 2. 항상 최신본으로 접근 가능한 index.html 및 dashboard_latest.html
    latest_file = OUTPUT_DIR / "dashboard_latest.html"
    latest_file.write_text(html_content, encoding="utf-8")

    index_file = OUTPUT_DIR / "index.html"
    index_file.write_text(html_content, encoding="utf-8")

    print(f"✓ 대시보드 생성 완료:")
    print(f"   • 타임스탬프 보관본: {dated_file}")
    print(f"   • 최신본 (더블클릭 실행용): {latest_file}")
    print(f"   • 웹 루트용 (index.html):   {index_file}")
    print(f"✓ 반영된 데이터: 이슈 {len(data['risk_matrix'])}개, 정부발표 {data['total_gov']}건, 기사로그 {data['total_articles']}건")

    if args.open:
        print("\n🚀 기본 브라우저에서 대시보드를 엽니다...")
        webbrowser.open(latest_file.as_uri())


if __name__ == "__main__":
    main()
