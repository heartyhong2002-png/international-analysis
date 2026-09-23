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
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

load_dotenv()

_SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = _SCRIPT_DIR.parent / "output" / "dashboard"
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



def fetch_signal_gap_data():
    try:
        with open("data/signal_gap/signal_gap_analysis.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        signal_gap_data = fetch_signal_gap_data()
    financial_proxy = fetch_financial_proxy()
    telegram_osint = fetch_telegram_osint()

    return {
        "signal_gap_data": signal_gap_data,
        "financial_proxy": financial_proxy,
        "telegram_osint": telegram_osint,}

def fetch_financial_proxy():
    proxies = []
    try:
        with open("data/signal_gap/financial_proxy_latest.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                proxies.append(row)
    except:
        pass
    return proxies

def fetch_telegram_osint():
    try:
        with open("data/signal_gap/middle_east_risk_analysis.txt", "r", encoding="utf-8") as f:
            content = f.read()
            return content
    except:
        return "데이터를 불러올 수 없습니다."


def get_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
    )


def fetch_warning_snapshot(cur):
    """Fetch the approved early-warning presentation contract, if available.

    Alert Level is never inferred here from article counts, tone, or public
    interest.  The DB/analysis track owns the assessment; without its snapshot
    the generated page must state that confirmation is required.
    """
    snapshot_query = os.getenv("EARLY_WARNING_SNAPSHOT_QUERY")
    if not snapshot_query:
        return [], False
    try:
        cur.execute(snapshot_query)
        return cur.fetchall(), True
    except mysql.connector.Error:
        return [], False


def fetch_all_dashboard_data(conn):
    """MySQL DB의 정규화 테이블 및 분석 뷰에서 데이터를 통합 집계합니다."""
    cur = conn.cursor(dictionary=True)
    warning_snapshot, warning_snapshot_available = fetch_warning_snapshot(cur)

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

    return {
        "signal_gap_data": signal_gap_data,
        "financial_proxy": financial_proxy,
        "telegram_osint": telegram_osint,
        "risk_matrix": risk_matrix,
        "framing_data": framing_data,
        "audit_data": audit_data,
        "gov_sources": gov_sources,
        "total_gov": total_gov,
        "total_articles": total_articles,
        "recent_feed": recent_feed,
        "warning_snapshot": warning_snapshot,
        "warning_snapshot_available": warning_snapshot_available,
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

    # Create Signal Gap and Financial Proxy Cards
    sg_html = ""
    for region, details in sg_data.items():
        score = details.get("discrepancy_score", 0)
        color_cls = "tag-danger" if score >= 80 else ("tag-amber" if score >= 50 else "tag-info")
        sg_html += f"""
        <div style="background: rgba(0,0,0,0.25); padding: 14px; border-radius: 8px; margin-bottom: 10px; border-left: 3px solid {'#ef4444' if score>=80 else '#f59e0b'};">
            <div style="font-size: 14px; font-weight: 700;">{html.escape(region)} 신호 괴리율 <span class="kpi-tag {color_cls}">{score}점</span></div>
            <div style="font-size: 12px; color: var(--text-muted); margin-top: 5px;">{html.escape(details.get("narrative_differences", ""))}</div>
        </div>
        """

    fp_html = ""
    for item in fp_data:
        change = float(item.get("Monthly_Change_Percent", 0))
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

    new_section_html = f"""
  <section class="charts-grid">
    <div class="chart-card">
      <div class="chart-header">
        <div>
          <div class="chart-title">📡 텔레그램 OSINT 조기경보 (근거 추적 박스)</div>
          <div class="chart-subtitle">실시간 블랙스완 징후 탐지 및 다중 LLM 릴레이 분석 결과</div>
        </div>
      </div>
      <div style="overflow-y: auto; max-height: 350px; font-size: 13px; line-height: 1.6;">
        <div style="background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); padding: 15px; border-radius: 8px;">
          <div style="display:inline-block; background:#ef4444; color:white; padding:2px 8px; border-radius:4px; font-weight:bold; font-size:11px; margin-bottom:10px;">Critical</div>
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
"""
    
    # We replace the Alert counts part to include the OSINT
    alert_counts = {"Critical": 1, "Warning": 0, "Watch": 0, "Normal": 0, "확인 필요": 0}
    alert_counts["Warning"] += sum(1 for region, details in sg_data.items() if details.get("discrepancy_score", 0) >= 80)
    alert_counts["Watch"] += sum(1 for item in fp_data if float(item.get("Monthly_Change_Percent", 0)) < -5)

    # Alert Level is presentation-only data from the approved snapshot.
    # alert_counts is already defined above
    warning_rows = []
    if warning_snapshot_available:
        for item in warning_snapshot:
            level = str(item.get("alert_level") or "확인 필요").title()
            normalized = level if level in alert_counts else "확인 필요"
            alert_counts[normalized] += 1
            warning_rows.append(f"""
              <article class="warning-item">
                <div class="warning-head"><strong>{html.escape(str(item.get('issue') or '미지정 이슈'))}</strong><span class="badge badge-{'red' if normalized == 'Warning' else 'amber' if normalized == 'Watch' else 'blue'}">{html.escape(normalized)}</span></div>
                <p><b>위험 신호:</b> {html.escape(str(item.get('risk_signal_summary') or '확인 필요'))}</p>
                <p><b>신호 괴리:</b> {html.escape(str(item.get('signal_gap_summary') or '확인 필요'))}</p>
                <p class="text-muted"><b>근거 범위:</b> {html.escape(str(item.get('evidence_coverage') or '확인 필요'))} · <b>검증 상태:</b> {html.escape(str(item.get('validation_status') or '확인 필요'))}</p>
              </article>""")
    else:
        alert_counts["확인 필요"] = total_issues
        warning_rows.append("""
          <article class="warning-item warning-pending">
            <div class="warning-head"><strong>경보 산출 스냅샷 미연결</strong><span class="badge badge-amber">확인 필요</span></div>
            <p>수집·논조 데이터는 표시되지만, 승인된 Alert Level과 검증 상태가 없어 경보를 확정해 표시하지 않습니다.</p>
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
    except mysql.connector.Error as e:
        print(f"✗ MySQL 접속 실패: {e}")
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
