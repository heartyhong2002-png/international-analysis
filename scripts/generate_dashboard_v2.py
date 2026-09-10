"""
generate_dashboard_v2.py — MySQL 연동 대시보드 (프로토타입)
================================================================

⚠️ 이 파일은 "컨트롤타워" 세션이 만든 프로토타입입니다. 실제 MySQL DB에
연결해서 진짜 데이터로 작동하는 것까지는 확인했지만(테스트 DB로 end-to-end
검증 완료), 스타일링/차트 품질/필터링 같은 건 최소한으로만 해놨습니다.
이어받는 세션에서 다듬어주세요.

예전 generate_dashboard.py와의 결정적 차이:
  - 예전 버전: self.issues_data에 "Sample data for demonstration"이라는
    주석과 함께 완전히 하드코딩된 가짜 데이터만 그렸음 (실제 수집 데이터를
    전혀 안 읽었음)
  - 이 버전: build_database.py가 적재한 실제 MySQL 데이터를 쿼리해서 그림.
    데이터가 없으면 "데이터 없음"이라고 정직하게 표시함 (가짜 숫자로
    채우지 않음).

프로토타입이라 일부러 단순하게 남겨둔 것 (이어받는 세션이 다듬을 부분):
  - 차트가 순수 CSS 가로 막대(bar)뿐 — 진짜 인터랙티브 차트(hover, 시계열
    추이 등)는 없음. dataviz 스킬이나 Chart.js 등으로 업그레이드 가능.
  - collected_date별 시계열 추이(트렌드 라인)는 아직 없음 — 최신 스냅샷만 보여줌.
  - 대륙/지역별 그룹핑은 안 함 — 이슈를 그냥 intensity 순으로만 나열.
  - 반응형/모바일 레이아웃 최소한만 고려함.

사용법:
    python scripts/generate_dashboard_v2.py
    → output/dashboard/dashboard_{날짜}.html 생성 (더블클릭으로 브라우저에서 열림)
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

_SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = _SCRIPT_DIR.parent / "output" / "dashboard"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "international_analysis")


def get_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
    )


def fetch_dashboard_data(conn):
    """대시보드에 필요한 데이터를 실제 DB에서 쿼리해서 가져옵니다."""
    cur = conn.cursor(dictionary=True)

    # 최신 수집일 기준 이슈별 intensity + 정부 발표 매칭 건수 (LEFT JOIN)
    cur.execute("""
        SELECT s.issue, s.intensity, s.article_count,
               COALESCE(g.matched_count, 0) AS gov_matches
        FROM issue_summary s
        LEFT JOIN (
            SELECT issue, COUNT(*) AS matched_count
            FROM issue_gov_match
            GROUP BY issue
        ) g ON g.issue = s.issue
        WHERE s.collected_date = (SELECT MAX(collected_date) FROM issue_summary)
        ORDER BY s.intensity DESC
    """)
    issues = cur.fetchall()

    cur.execute("SELECT COUNT(*) AS total FROM gov_announcements")
    total_announcements = cur.fetchone()["total"]

    cur.execute("SELECT MAX(collected_date) AS latest FROM issue_summary")
    latest_date = cur.fetchone()["latest"]

    cur.execute("""
        SELECT source, COUNT(*) AS cnt FROM gov_announcements
        GROUP BY source ORDER BY cnt DESC LIMIT 5
    """)
    top_sources = cur.fetchall()

    cur.close()
    return {
        "issues": issues,
        "total_announcements": total_announcements,
        "latest_date": latest_date,
        "top_sources": top_sources,
    }


def render_html(data):
    issues = data["issues"]
    max_intensity = max([i["intensity"] or 0 for i in issues], default=1) or 1

    if not issues:
        issue_rows = '<tr><td colspan="4" class="empty">아직 수집된 데이터가 없습니다. run_pipeline.py를 먼저 실행하세요.</td></tr>'
        bars = "<p class='empty'>데이터 없음</p>"
    else:
        issue_rows = "\n".join(
            f"""<tr>
                <td>{i['issue']}</td>
                <td>{i['intensity']:.1f}</td>
                <td>{i['article_count']:.0f}</td>
                <td>{i['gov_matches']}{'  🔴' if (i['intensity'] or 0) > 50 and i['gov_matches'] == 0 else ''}</td>
            </tr>"""
            for i in issues
        )
        bars = "\n".join(
            f"""<div class="bar-row">
                <span class="bar-label">{i['issue']}</span>
                <div class="bar-track"><div class="bar-fill" style="width:{(i['intensity'] or 0) / max_intensity * 100:.1f}%"></div></div>
                <span class="bar-value">{i['intensity']:.1f}</span>
            </div>"""
            for i in issues[:10]
        )

    source_rows = "\n".join(
        f"<tr><td>{s['source']}</td><td>{s['cnt']}</td></tr>" for s in data["top_sources"]
    ) or '<tr><td colspan="2" class="empty">데이터 없음</td></tr>'

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>국제정세 분석 대시보드 (프로토타입)</title>
<style>
  :root {{
    --bg: #0f1420; --card: #1a2133; --text: #e8ecf4; --muted: #8b93a7;
    --accent: #4f8cff; --danger: #ff6b6b; --border: #2a3348;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family: -apple-system, "Segoe UI", "Malgun Gothic", sans-serif;
          background: var(--bg); color: var(--text); padding: 32px 24px; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  .subtitle {{ color: var(--muted); font-size: 13px; margin-bottom: 24px; }}
  .proto-badge {{ display:inline-block; background:#3a2f10; color:#ffcf5c; font-size:11px;
                  padding: 2px 8px; border-radius: 4px; margin-left: 8px; vertical-align: middle; }}
  .kpi-row {{ display: flex; gap: 16px; margin-bottom: 28px; flex-wrap: wrap; }}
  .kpi-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px;
               padding: 16px 20px; min-width: 160px; flex: 1; }}
  .kpi-card .value {{ font-size: 28px; font-weight: 700; }}
  .kpi-card .label {{ color: var(--muted); font-size: 12px; margin-top: 4px; }}
  .section {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px;
              padding: 20px; margin-bottom: 20px; }}
  .section h2 {{ font-size: 15px; margin: 0 0 16px; color: var(--text); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--border); }}
  th {{ color: var(--muted); font-weight: 600; font-size: 11px; text-transform: uppercase; }}
  .empty {{ color: var(--muted); text-align: center; padding: 20px; }}
  .bar-row {{ display: flex; align-items: center; gap: 10px; margin-bottom: 10px; font-size: 13px; }}
  .bar-label {{ width: 160px; flex-shrink: 0; color: var(--muted); }}
  .bar-track {{ flex: 1; background: #10151f; border-radius: 4px; height: 14px; overflow: hidden; }}
  .bar-fill {{ background: var(--accent); height: 100%; border-radius: 4px; }}
  .bar-value {{ width: 44px; text-align: right; }}
  footer {{ color: var(--muted); font-size: 11px; margin-top: 24px; }}
</style>
</head>
<body>
  <h1>국제정세 분석 대시보드 <span class="proto-badge">PROTOTYPE</span></h1>
  <div class="subtitle">최신 수집일: {data['latest_date'] or '없음'} · 생성 시각: {generated_at}</div>

  <div class="kpi-row">
    <div class="kpi-card"><div class="value">{len(issues)}</div><div class="label">추적 중인 이슈 수</div></div>
    <div class="kpi-card"><div class="value">{data['total_announcements']}</div><div class="label">누적 정부 발표 건수</div></div>
    <div class="kpi-card"><div class="value">{issues[0]['issue'] if issues else '-'}</div><div class="label">최고 관심도 이슈</div></div>
  </div>

  <div class="section">
    <h2>이슈별 관심도 (Wikipedia 기반 intensity)</h2>
    {bars}
  </div>

  <div class="section">
    <h2>이슈별 상세 — 대중 관심 vs 정부 공식 반응</h2>
    <table>
      <tr><th>이슈</th><th>Intensity</th><th>기사 수</th><th>정부 발표 매칭</th></tr>
      {issue_rows}
    </table>
    <p style="color:var(--muted); font-size:12px; margin-top:10px;">🔴 = 대중 관심은 높은데(intensity&gt;50) 정부 공식 발표가 아직 없는 이슈</p>
  </div>

  <div class="section">
    <h2>정부 발표 소스 Top 5</h2>
    <table>
      <tr><th>소스</th><th>건수</th></tr>
      {source_rows}
    </table>
  </div>

  <footer>MySQL DB 'international_analysis'에서 실시간 쿼리한 실제 데이터입니다 (하드코딩 아님). run_pipeline.py 실행 후 새로고침하면 갱신됩니다.</footer>
</body>
</html>"""


def main():
    print("=" * 60)
    print("📊 대시보드 생성 (프로토타입 — MySQL 실데이터 연동)")
    print("=" * 60)
    try:
        conn = get_connection()
    except mysql.connector.Error as e:
        print(f"✗ MySQL 접속 실패: {e}")
        sys.exit(1)

    data = fetch_dashboard_data(conn)
    conn.close()

    html = render_html(data)
    out_path = OUTPUT_DIR / f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"✓ 생성 완료: {out_path}")
    print(f"  이슈 {len(data['issues'])}건, 정부 발표 {data['total_announcements']}건 반영됨")


if __name__ == "__main__":
    main()
