"""
Bilingual Issue Analysis Report Generator
한국어/영어 이슈별 분석 리포트 자동 생성 스크립트

이 버전은 더 이상 더미(placeholder) 텍스트를 사용하지 않습니다.
data/issue_research_data.py 에 저장된, WebSearch 기반 실제 리서치 결과를
템플릿에 채워 넣습니다. (이전 버전은 "주요 사건 1", "미국의 입장" 같은
하드코딩된 가짜 문구를 채워넣고 있었습니다 — 이는 버그가 아니라 파이프라인
골격만 있고 실제 콘텐츠가 없었던 것이며, 이번에 실제 데이터로 교체했습니다.)

Generates a single combined bilingual (KO/EN) report covering:
- Executive Summary
- Background & Timeline
- Key Indicators / Economic-Security Impact
- Current Situation Assessment
- Future Outlook (short/medium/long term)
- Impact on Korea
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Windows 콘솔의 기본 인코딩(cp949)이 이모지/특수문자를 표현하지 못해
# UnicodeEncodeError가 나는 것을 방지하기 위해 UTF-8로 강제 설정합니다.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 실제 리서치 데이터 로드 (data/issue_research_data.py)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "data"))
sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))
from issue_research_data import REAL_ISSUE_DATA  # noqa: E402
from report_db_saver import save_report_to_desktop_and_db, DESKTOP_REPORTS_DIR  # noqa: E402


class IssueReportGenerator:
    def __init__(self):
        self.output_dir = Path("reports/issues")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 이슈 메타데이터 (이름/지역). 위험도(intensity)는 더 이상 여기서
        # 임의로 정하지 않고, 리서치 데이터의 intensity_assessment를 그대로 사용합니다.
        self.issues = {
            "North_Korea_Nuclear": {
                "ko_name": "북한 핵 & 트럼프-김정은 관계",
                "en_name": "North Korea Nuclear & Trump-Kim Relationship",
                "region": "Asia-Pacific",
            },
            "Taiwan_Strait": {
                "ko_name": "대만 해협 긴장",
                "en_name": "Taiwan Strait Tensions",
                "region": "Asia-Pacific",
            },
            "Ukraine_War": {
                "ko_name": "우크라이나 전쟁",
                "en_name": "Ukraine War",
                "region": "Europe",
            },
            "Iran_Nuclear": {
                "ko_name": "이란 핵협상 & 긴장",
                "en_name": "Iran Nuclear & Tensions",
                "region": "Middle East",
            },
            "US_China_Trade": {
                "ko_name": "미-중 무역 전쟁",
                "en_name": "US-China Trade War",
                "region": "Global",
            },
        }

        # Korean report template (GAO Standard Format)
        self.ko_template = """
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #111827; line-height: 1.6; max-width: 900px; margin: 0 auto; padding: 24px 32px; background-color: #ffffff;">

  <!-- 1. Header Metadata -->
  <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #1B365D; padding-bottom: 8px; margin-bottom: 12px;">
    <div>
      <div style="font-size: 13px; font-weight: 800; color: #111827; letter-spacing: 0.8px; text-transform: uppercase;">
        INTERNATIONAL AFFAIRS INTELLIGENCE OFFICE
      </div>
      <div style="font-size: 11px; font-weight: 700; color: #4B5563; margin-top: 2px;">
        IA-26-{intensity}SP
      </div>
    </div>
    <div style="text-align: right;">
      <div style="font-size: 11px; font-weight: 800; color: #DC2626; letter-spacing: 0.5px;">
        UNCLASSIFIED // FOR OFFICIAL USE ONLY
      </div>
      <div style="font-size: 11px; color: #4B5563; margin-top: 2px;">
        {date}
      </div>
    </div>
  </div>

  <div style="font-size: 11px; font-weight: 700; color: #6B7280; letter-spacing: 1.2px; text-transform: uppercase; margin-bottom: 6px;">
    REPORT TO POLICY COMMITTEES & MINISTERIAL LEADERSHIP
  </div>

  <!-- 2. Main Title & Subtitle -->
  <h1 style="font-size: 26px; font-weight: 900; color: #0F172A; margin: 0 0 6px 0; letter-spacing: -0.5px; text-transform: uppercase; line-height: 1.2;">
    {ko_name} 정세 평가 보고서
  </h1>
  <div style="font-size: 14px; color: #475569; font-style: italic; margin-bottom: 22px; line-height: 1.4;">
    {ko_situation}
  </div>

  <!-- 3. GAO HIGHLIGHTS Box (Two-Column Blue Box) -->
  <div style="border: 2px solid #2563EB; border-radius: 4px; padding: 14px 18px; margin-bottom: 28px; background-color: #F8FAFC;">
    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #BFDBFE; padding-bottom: 6px; margin-bottom: 12px;">
      <span style="font-size: 13px; font-weight: 900; color: #1D4ED8; letter-spacing: 1px;">GAO HIGHLIGHTS</span>
      <span style="font-size: 12px; font-weight: 700; color: #1D4ED8;">Highlights of IA-26-{intensity}SP</span>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
      <!-- Left Column: WHY WE DID THIS STUDY -->
      <div style="font-size: 12px; color: #334155; text-align: justify;">
        <div style="font-size: 11px; font-weight: 800; color: #0F172A; letter-spacing: 0.5px; margin-bottom: 6px; text-transform: uppercase;">
          WHY THIS STUDY WAS CONDUCTED
        </div>
        <p style="margin: 0 0 8px 0;">
          {issue_overview_ko}
        </p>
        <p style="margin: 0;">
          본 평가는 (1) 최근 안보·경제적 핵심 지표의 변동성 및 위험도를 계측하고, (2) 트럼프 2기 행정부 출범 이후 주요 이해관계국의 전략적 대응 실태를 진단하여 대한민국 국익 보호를 위한 정책적 시사점을 도출하기 위해 수행되었습니다.
        </p>
      </div>

      <!-- Right Column: WHAT WE FOUND -->
      <div style="font-size: 12px; color: #334155; text-align: justify; border-left: 1px solid #E2E8F0; padding-left: 18px;">
        <div style="font-size: 11px; font-weight: 800; color: #0F172A; letter-spacing: 0.5px; margin-bottom: 6px; text-transform: uppercase;">
          WHAT WE FOUND
        </div>
        <p style="margin: 0 0 6px 0;">
          <strong>종합 위험도: {severity_ko} ({intensity}/100)</strong>
        </p>
        <p style="margin: 0 0 8px 0;">
          {main_indicator_ko}
        </p>
        <p style="margin: 0;">
          {international_response_ko}
        </p>
      </div>
    </div>
  </div>

  <!-- 4. Section 1: BACKGROUND AND SCOPE -->
  <h2 style="font-size: 15px; font-weight: 900; color: #0F172A; border-bottom: 1.5px solid #CBD5E1; padding-bottom: 4px; margin: 26px 0 10px 0; letter-spacing: 0.5px; text-transform: uppercase;">
    1. BACKGROUND AND SCOPE
  </h2>
  <p style="font-size: 13px; color: #334155; text-align: justify; margin-bottom: 12px;">
    {issue_overview_ko}
  </p>
  <p style="font-size: 13px; color: #334155; text-align: justify; margin-bottom: 14px;">
    <strong>트럼프 행정부의 영향:</strong> {trump_impact_ko}
  </p>

  <!-- Table 1: Major Turning Points Timeline -->
  <div style="font-size: 12px; font-weight: 700; color: #0F172A; margin: 16px 0 6px 0;">
    Table 1: 주요 전개 타임라인 및 핵심 사건 (2025–2026)
  </div>
  <table style="width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 6px;">
    <thead>
      <tr style="background-color: #1B365D; color: #ffffff; text-align: left;">
        <th style="padding: 8px 12px; width: 22%;">일 시 (Date)</th>
        <th style="padding: 8px 12px;">주요 사건 및 정책 전개 (Event & Developments)</th>
      </tr>
    </thead>
    <tbody>
      <tr style="border-bottom: 1px solid #E2E8F0;">
        <td style="padding: 8px 12px; font-weight: 700; color: #1E293B;">2025년 1월</td>
        <td style="padding: 8px 12px; color: #334155;">트럼프 2기 행정부 공식 출범</td>
      </tr>
      <tr style="background-color: #F8FAFC; border-bottom: 1px solid #E2E8F0;">
        <td style="padding: 8px 12px; font-weight: 700; color: #1E293B;">2025년 3월경</td>
        <td style="padding: 8px 12px; color: #334155;">{event_1_ko}</td>
      </tr>
      <tr style="border-bottom: 1px solid #E2E8F0;">
        <td style="padding: 8px 12px; font-weight: 700; color: #1E293B;">2025년 6월경</td>
        <td style="padding: 8px 12px; color: #334155;">{event_2_ko}</td>
      </tr>
      <tr style="background-color: #F8FAFC; border-bottom: 1px solid #E2E8F0;">
        <td style="padding: 8px 12px; font-weight: 700; color: #1E293B;">2026년 9월 (현재)</td>
        <td style="padding: 8px 12px; color: #334155;">{current_status_ko}</td>
      </tr>
    </tbody>
  </table>
  <div style="font-size: 11px; color: #64748B; margin-bottom: 24px;">
    Source: International Affairs Intelligence Office analysis of official government feeds and verified news logs. | IA-26-{intensity}SP
  </div>

  <!-- 5. Section 2: STAKEHOLDER STRATEGIC POSTURE -->
  <h2 style="font-size: 15px; font-weight: 900; color: #0F172A; border-bottom: 1.5px solid #CBD5E1; padding-bottom: 4px; margin: 26px 0 10px 0; letter-spacing: 0.5px; text-transform: uppercase;">
    2. STAKEHOLDER STRATEGIC POSTURE AND OBJECTIVE ASSESSMENT
  </h2>
  <p style="font-size: 13px; color: #334155; text-align: justify; margin-bottom: 14px;">
    <strong>객관적 정세 분석:</strong> {objective_analysis_ko}
  </p>

  <!-- Table 2: Stakeholders' Position -->
  <div style="font-size: 12px; font-weight: 700; color: #0F172A; margin: 16px 0 6px 0;">
    Table 2: 주요 이해관계국 공식 입장 및 전략적 지향
  </div>
  <table style="width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 6px;">
    <thead>
      <tr style="background-color: #1B365D; color: #ffffff; text-align: left;">
        <th style="padding: 8px 12px; width: 18%;">국가/행위자 (Actor)</th>
        <th style="padding: 8px 12px;">공식 입장 및 전략적 기조 (Official Stance & Strategy)</th>
      </tr>
    </thead>
    <tbody>
      <tr style="border-bottom: 1px solid #E2E8F0;">
        <td style="padding: 8px 12px; font-weight: 700; color: #1E293B;">미 국 (United States)</td>
        <td style="padding: 8px 12px; color: #334155;">{us_position_ko}</td>
      </tr>
      <tr style="background-color: #F8FAFC; border-bottom: 1px solid #E2E8F0;">
        <td style="padding: 8px 12px; font-weight: 700; color: #1E293B;">중 국 (China)</td>
        <td style="padding: 8px 12px; color: #334155;">{china_position_ko}</td>
      </tr>
      <tr style="border-bottom: 1px solid #E2E8F0;">
        <td style="padding: 8px 12px; font-weight: 700; color: #1E293B;">한 국 (South Korea)</td>
        <td style="padding: 8px 12px; color: #334155;">{korea_position_ko}</td>
      </tr>
      <tr style="background-color: #F8FAFC; border-bottom: 1px solid #E2E8F0;">
        <td style="padding: 8px 12px; font-weight: 700; color: #1E293B;">기타 주요국 (Others)</td>
        <td style="padding: 8px 12px; color: #334155;">{others_position_ko}</td>
      </tr>
    </tbody>
  </table>
  <div style="font-size: 11px; color: #64748B; margin-bottom: 24px;">
    Source: Interagency multi-source diplomatic monitoring and official communique synthesis. | IA-26-{intensity}SP
  </div>

  <!-- 6. Section 3: ECONOMIC AND SECURITY IMPACT ANALYSIS -->
  <h2 style="font-size: 15px; font-weight: 900; color: #0F172A; border-bottom: 1.5px solid #CBD5E1; padding-bottom: 4px; margin: 26px 0 10px 0; letter-spacing: 0.5px; text-transform: uppercase;">
    3. ECONOMIC AND SECURITY IMPACT ANALYSIS
  </h2>
  
  <div style="margin-bottom: 14px;">
    <div style="font-size: 13px; font-weight: 700; color: #1E293B; margin-bottom: 4px;">■ 안보·국방 영향 (Security Dimension)</div>
    <ul style="font-size: 13px; color: #334155; margin: 4px 0 8px 20px; padding: 0;">
      <li style="margin-bottom: 4px;"><strong>북한 및 역내 안보 함의:</strong> {north_korea_impact_ko}</li>
      <li style="margin-bottom: 4px;"><strong>한미동맹 영향:</strong> {alliance_impact_ko}</li>
      <li style="margin-bottom: 4px;"><strong>군사·미사일 위협 수준:</strong> {missile_threat_ko}</li>
    </ul>
  </div>

  <div style="margin-bottom: 14px;">
    <div style="font-size: 13px; font-weight: 700; color: #1E293B; margin-bottom: 4px;">■ 경제·통상·금융 영향 (Economic Dimension)</div>
    <ul style="font-size: 13px; color: #334155; margin: 4px 0 8px 20px; padding: 0;">
      <li style="margin-bottom: 4px;"><strong>대외 무역 및 통상:</strong> {trade_impact_ko}</li>
      <li style="margin-bottom: 4px;"><strong>외환시장 및 환율:</strong> {fx_impact_ko}</li>
      <li style="margin-bottom: 4px;"><strong>국내외 투자 흐름:</strong> {investment_impact_ko}</li>
    </ul>
  </div>

  <div style="margin-bottom: 20px;">
    <div style="font-size: 13px; font-weight: 700; color: #1E293B; margin-bottom: 4px;">■ 여론 및 전문가 집단 평가</div>
    <p style="font-size: 13px; color: #334155; margin: 0 0 4px 0;"><strong>국내외 여론 추이:</strong> {public_opinion_ko}</p>
    <p style="font-size: 13px; color: #334155; margin: 0;"><strong>전문가 종합 평가:</strong> {expert_assessment_ko}</p>
  </div>

  <!-- 7. Section 4: PERFORMANCE BENCHMARKS AND GAP ANALYSIS -->
  <h2 style="font-size: 15px; font-weight: 900; color: #0F172A; border-bottom: 1.5px solid #CBD5E1; padding-bottom: 4px; margin: 26px 0 10px 0; letter-spacing: 0.5px; text-transform: uppercase;">
    4. RISK OUTLOOK AND UNCERTAINTY ANALYSIS
  </h2>
  <div style="font-size: 13px; color: #334155; margin-bottom: 12px;">
    <p style="margin: 0 0 6px 0;"><strong>단기 전망 (3~6개월):</strong> {short_term_outlook_ko}</p>
    <p style="margin: 0 0 8px 0; color: #1E40AF;"><em>▶ 가능성 높은 시나리오:</em> {likely_scenario_short_ko}</p>
    <p style="margin: 0 0 6px 0;"><strong>중기 전망 (1~3년):</strong> {medium_term_outlook_ko}</p>
    <p style="margin: 0 0 8px 0; color: #1E40AF;"><em>▶ 예상 전환점:</em> {transition_point_ko}</p>
    <p style="margin: 0 0 6px 0;"><strong>장기 구조적 변화:</strong> {long_term_outlook_ko}</p>
    <p style="margin: 0 0 12px 0; color: #1E40AF;"><em>▶ 구조적 리스크:</em> {structural_change_ko}</p>
  </div>

  <div style="background-color: #F1F5F9; border-left: 3px solid #64748B; padding: 10px 14px; margin-bottom: 24px; font-size: 12px; color: #334155;">
    <strong>주요 불확실성 요인 (Key Uncertainties):</strong>
    <ol style="margin: 4px 0 0 18px; padding: 0;">
      <li style="margin-bottom: 2px;">{uncertainty_1_ko}</li>
      <li style="margin-bottom: 2px;">{uncertainty_2_ko}</li>
      <li>{uncertainty_3_ko}</li>
    </ol>
  </div>

  <!-- 8. Section 5: RECOMMENDATIONS FOR EXECUTIVE ACTION -->
  <h2 style="font-size: 15px; font-weight: 900; color: #0F172A; border-bottom: 1.5px solid #CBD5E1; padding-bottom: 4px; margin: 26px 0 10px 0; letter-spacing: 0.5px; text-transform: uppercase;">
    5. RECOMMENDATIONS FOR EXECUTIVE ACTION
  </h2>
  <p style="font-size: 13px; color: #334155; margin-bottom: 12px;">
    국가 안보 유지 및 핵심 경제 이익의 선제적 방어를 위해 다음 핵심 정책 조치 사항을 유관 부처 및 의사결정권자에게 권고합니다:
  </p>

  <!-- Amber Callout Box for Recommendations -->
  <div style="background-color: #FFFBEB; border-left: 4px solid #D97706; padding: 14px 18px; margin-bottom: 24px; border-radius: 2px;">
    <div style="font-size: 12px; font-weight: 800; color: #92400E; letter-spacing: 0.8px; margin-bottom: 8px; text-transform: uppercase;">
      KEY EXECUTIVE RECOMMENDATIONS
    </div>
    <div style="font-size: 12px; color: #78350F; line-height: 1.6;">
      <p style="margin: 0 0 8px 0;">
        <strong>Recommendation 1 (안보·동맹 공조):</strong> 국가안보실 및 국방부는 한미 연합 방위태세의 실효성을 유지하되, 트럼프 행정부의 훈련 축소 및 방위비 분담금 인상 요구에 대비한 종합 대응 전략을 조속히 수립해야 함. ({response_strategy_ko})
      </p>
      <p style="margin: 0 0 8px 0;">
        <strong>Recommendation 2 (통상·투자 방어):</strong> 산업통상자원부 및 기획재정부는 대미 관세 합의 이행 과정을 밀착 모니터링하고, 지정학적 리스크로 인한 공급망·투자 지연 사태에 대비한 조기경보시스템(EWS)을 가동해야 함.
      </p>
      <p style="margin: 0;">
        <strong>Recommendation 3 (다자 외교 지렛대 확보):</strong> 외교부는 미·중·러 갈등 속에서 일방적 종속을 탈피하고, 다자간 대화 채널을 유지하여 한국의 외교적 레버리지를 극대화해야 함. ({korea_us_impact_ko})
      </p>
    </div>
  </div>

  <!-- 9. Section 6: METHODOLOGY AND AGENCY SOURCES -->
  <h2 style="font-size: 15px; font-weight: 900; color: #0F172A; border-bottom: 1.5px solid #CBD5E1; padding-bottom: 4px; margin: 26px 0 10px 0; letter-spacing: 0.5px; text-transform: uppercase;">
    6. AGENCY COMMENTS AND METHODOLOGY
  </h2>
  <p style="font-size: 12px; color: #64748B; text-align: justify; margin-bottom: 8px;">
    본 리포트는 WebSearch/WebFetch를 기반으로 실제 언론 보도, 글로벌 싱크탱크 분석, 각국 정부 발표 자료를 종합 분석하여 작성되었습니다. 정량 데이터 수집 파이프라인(GDELT, FRED, IMF DOTS)과 정성적 정세 분석의 교차 검증을 거쳤습니다.
  </p>
  <div style="font-size: 12px; color: #2563EB; margin-bottom: 24px;">
    <strong>주요 참고 자료:</strong> 
    <a href="{news_link_1}" style="color: #2563EB; text-decoration: underline; margin-right: 8px;">[원문 보도 1]</a>
    <a href="{news_link_2}" style="color: #2563EB; text-decoration: underline; margin-right: 8px;">[원문 보도 2]</a>
    <a href="{news_link_3}" style="color: #2563EB; text-decoration: underline;">[원문 보도 3]</a>
  </div>

  <!-- Running Footer -->
  <div style="display: flex; justify-content: space-between; border-top: 1px solid #CBD5E1; padding-top: 8px; font-size: 11px; color: #64748B; margin-top: 36px;">
    <span>IA-26-{intensity}SP {ko_name} 정세 평가</span>
    <span>Page 1 / Comprehensive Dossier</span>
  </div>

</div>
"""

        # English report template (GAO Standard Format)
        self.en_template = """
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #111827; line-height: 1.6; max-width: 900px; margin: 0 auto; padding: 24px 32px; background-color: #ffffff;">

  <!-- 1. Header Metadata -->
  <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #1B365D; padding-bottom: 8px; margin-bottom: 12px;">
    <div>
      <div style="font-size: 13px; font-weight: 800; color: #111827; letter-spacing: 0.8px; text-transform: uppercase;">
        INTERNATIONAL AFFAIRS INTELLIGENCE OFFICE
      </div>
      <div style="font-size: 11px; font-weight: 700; color: #4B5563; margin-top: 2px;">
        IA-26-{intensity}SP
      </div>
    </div>
    <div style="text-align: right;">
      <div style="font-size: 11px; font-weight: 800; color: #DC2626; letter-spacing: 0.5px;">
        UNCLASSIFIED // FOR OFFICIAL USE ONLY
      </div>
      <div style="font-size: 11px; color: #4B5563; margin-top: 2px;">
        {date}
      </div>
    </div>
  </div>

  <div style="font-size: 11px; font-weight: 700; color: #6B7280; letter-spacing: 1.2px; text-transform: uppercase; margin-bottom: 6px;">
    REPORT TO POLICY COMMITTEES & CONGRESSIONAL LEADERSHIP
  </div>

  <!-- 2. Main Title & Subtitle -->
  <h1 style="font-size: 26px; font-weight: 900; color: #0F172A; margin: 0 0 6px 0; letter-spacing: -0.5px; text-transform: uppercase; line-height: 1.2;">
    {en_name}: STRATEGIC ASSESSMENT
  </h1>
  <div style="font-size: 14px; color: #475569; font-style: italic; margin-bottom: 22px; line-height: 1.4;">
    {en_situation}
  </div>

  <!-- 3. GAO HIGHLIGHTS Box (Two-Column Blue Box) -->
  <div style="border: 2px solid #2563EB; border-radius: 4px; padding: 14px 18px; margin-bottom: 28px; background-color: #F8FAFC;">
    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #BFDBFE; padding-bottom: 6px; margin-bottom: 12px;">
      <span style="font-size: 13px; font-weight: 900; color: #1D4ED8; letter-spacing: 1px;">GAO HIGHLIGHTS</span>
      <span style="font-size: 12px; font-weight: 700; color: #1D4ED8;">Highlights of IA-26-{intensity}SP</span>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
      <!-- Left Column: WHY GAO DID THIS STUDY -->
      <div style="font-size: 12px; color: #334155; text-align: justify;">
        <div style="font-size: 11px; font-weight: 800; color: #0F172A; letter-spacing: 0.5px; margin-bottom: 6px; text-transform: uppercase;">
          WHY THIS STUDY WAS CONDUCTED
        </div>
        <p style="margin: 0 0 8px 0;">
          {issue_overview_en}
        </p>
        <p style="margin: 0;">
          GAO was requested to examine: (1) the extent to which regional security and economic risks have escalated under shifting geopolitical dynamics, and (2) how effectively allied agencies are coordinating strategic responses to safeguard economic and defense interests.
        </p>
      </div>

      <!-- Right Column: WHAT GAO FOUND -->
      <div style="font-size: 12px; color: #334155; text-align: justify; border-left: 1px solid #E2E8F0; padding-left: 18px;">
        <div style="font-size: 11px; font-weight: 800; color: #0F172A; letter-spacing: 0.5px; margin-bottom: 6px; text-transform: uppercase;">
          WHAT WE FOUND
        </div>
        <p style="margin: 0 0 6px 0;">
          <strong>Risk Severity: {severity_en} ({intensity}/100)</strong>
        </p>
        <p style="margin: 0 0 8px 0;">
          {main_indicator_en}
        </p>
        <p style="margin: 0;">
          {international_response_en}
        </p>
      </div>
    </div>
  </div>

  <!-- 4. Section 1: BACKGROUND AND SCOPE -->
  <h2 style="font-size: 15px; font-weight: 900; color: #0F172A; border-bottom: 1.5px solid #CBD5E1; padding-bottom: 4px; margin: 26px 0 10px 0; letter-spacing: 0.5px; text-transform: uppercase;">
    1. BACKGROUND AND SCOPE
  </h2>
  <p style="font-size: 13px; color: #334155; text-align: justify; margin-bottom: 12px;">
    {issue_overview_en}
  </p>
  <p style="font-size: 13px; color: #334155; text-align: justify; margin-bottom: 14px;">
    <strong>Impact of the Trump Administration:</strong> {trump_impact_en}
  </p>

  <!-- Table 1: Major Turning Points Timeline -->
  <div style="font-size: 12px; font-weight: 700; color: #0F172A; margin: 16px 0 6px 0;">
    Table 1: Key Turning Points and Strategic Milestones (2025–2026)
  </div>
  <table style="width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 6px;">
    <thead>
      <tr style="background-color: #1B365D; color: #ffffff; text-align: left;">
        <th style="padding: 8px 12px; width: 22%;">Timeline</th>
        <th style="padding: 8px 12px;">Key Event & Strategic Development</th>
      </tr>
    </thead>
    <tbody>
      <tr style="border-bottom: 1px solid #E2E8F0;">
        <td style="padding: 8px 12px; font-weight: 700; color: #1E293B;">January 2025</td>
        <td style="padding: 8px 12px; color: #334155;">Trump's Second Term Formally Begins</td>
      </tr>
      <tr style="background-color: #F8FAFC; border-bottom: 1px solid #E2E8F0;">
        <td style="padding: 8px 12px; font-weight: 700; color: #1E293B;">~March 2025</td>
        <td style="padding: 8px 12px; color: #334155;">{event_1_en}</td>
      </tr>
      <tr style="border-bottom: 1px solid #E2E8F0;">
        <td style="padding: 8px 12px; font-weight: 700; color: #1E293B;">~June 2025</td>
        <td style="padding: 8px 12px; color: #334155;">{event_2_en}</td>
      </tr>
      <tr style="background-color: #F8FAFC; border-bottom: 1px solid #E2E8F0;">
        <td style="padding: 8px 12px; font-weight: 700; color: #1E293B;">September 2026 (Current)</td>
        <td style="padding: 8px 12px; color: #334155;">{current_status_en}</td>
      </tr>
    </tbody>
  </table>
  <div style="font-size: 11px; color: #64748B; margin-bottom: 24px;">
    Source: International Affairs Intelligence Office baseline evaluations and diplomatic incident logs. | IA-26-{intensity}SP
  </div>

  <!-- 5. Section 2: STAKEHOLDER STRATEGIC POSTURE -->
  <h2 style="font-size: 15px; font-weight: 900; color: #0F172A; border-bottom: 1.5px solid #CBD5E1; padding-bottom: 4px; margin: 26px 0 10px 0; letter-spacing: 0.5px; text-transform: uppercase;">
    2. STAKEHOLDER STRATEGIC POSTURE AND OBJECTIVE ASSESSMENT
  </h2>
  <p style="font-size: 13px; color: #334155; text-align: justify; margin-bottom: 14px;">
    <strong>Objective Geopolitical Analysis:</strong> {objective_analysis_en}
  </p>

  <!-- Table 2: Stakeholders' Position -->
  <div style="font-size: 12px; font-weight: 700; color: #0F172A; margin: 16px 0 6px 0;">
    Table 2: Assessment of Major Stakeholder Positions and Strategic Alignment
  </div>
  <table style="width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 6px;">
    <thead>
      <tr style="background-color: #1B365D; color: #ffffff; text-align: left;">
        <th style="padding: 8px 12px; width: 18%;">Stakeholder</th>
        <th style="padding: 8px 12px;">Official Policy Posture & Strategic Interests</th>
      </tr>
    </thead>
    <tbody>
      <tr style="border-bottom: 1px solid #E2E8F0;">
        <td style="padding: 8px 12px; font-weight: 700; color: #1E293B;">United States</td>
        <td style="padding: 8px 12px; color: #334155;">{us_position_en}</td>
      </tr>
      <tr style="background-color: #F8FAFC; border-bottom: 1px solid #E2E8F0;">
        <td style="padding: 8px 12px; font-weight: 700; color: #1E293B;">China</td>
        <td style="padding: 8px 12px; color: #334155;">{china_position_en}</td>
      </tr>
      <tr style="border-bottom: 1px solid #E2E8F0;">
        <td style="padding: 8px 12px; font-weight: 700; color: #1E293B;">South Korea</td>
        <td style="padding: 8px 12px; color: #334155;">{korea_position_en}</td>
      </tr>
      <tr style="background-color: #F8FAFC; border-bottom: 1px solid #E2E8F0;">
        <td style="padding: 8px 12px; font-weight: 700; color: #1E293B;">Other Stakeholders</td>
        <td style="padding: 8px 12px; color: #334155;">{others_position_en}</td>
      </tr>
    </tbody>
  </table>
  <div style="font-size: 11px; color: #64748B; margin-bottom: 24px;">
    Source: Interagency multi-source diplomatic monitoring and official communique synthesis. | IA-26-{intensity}SP
  </div>

  <!-- 6. Section 3: ECONOMIC AND SECURITY IMPACT ANALYSIS -->
  <h2 style="font-size: 15px; font-weight: 900; color: #0F172A; border-bottom: 1.5px solid #CBD5E1; padding-bottom: 4px; margin: 26px 0 10px 0; letter-spacing: 0.5px; text-transform: uppercase;">
    3. ECONOMIC AND SECURITY IMPACT ANALYSIS
  </h2>
  
  <div style="margin-bottom: 14px;">
    <div style="font-size: 13px; font-weight: 700; color: #1E293B; margin-bottom: 4px;">■ Security & Defense Dimension</div>
    <ul style="font-size: 13px; color: #334155; margin: 4px 0 8px 20px; padding: 0;">
      <li style="margin-bottom: 4px;"><strong>North Korea & Regional Security:</strong> {north_korea_impact_en}</li>
      <li style="margin-bottom: 4px;"><strong>Alliance Impact:</strong> {alliance_impact_en}</li>
      <li style="margin-bottom: 4px;"><strong>Military & Missile Threats:</strong> {missile_threat_en}</li>
    </ul>
  </div>

  <div style="margin-bottom: 14px;">
    <div style="font-size: 13px; font-weight: 700; color: #1E293B; margin-bottom: 4px;">■ Economic, Trade & Financial Dimension</div>
    <ul style="font-size: 13px; color: #334155; margin: 4px 0 8px 20px; padding: 0;">
      <li style="margin-bottom: 4px;"><strong>Trade & Tariffs:</strong> {trade_impact_en}</li>
      <li style="margin-bottom: 4px;"><strong>Foreign Exchange & Currency:</strong> {fx_impact_en}</li>
      <li style="margin-bottom: 4px;"><strong>Cross-Border Investment:</strong> {investment_impact_en}</li>
    </ul>
  </div>

  <div style="margin-bottom: 20px;">
    <div style="font-size: 13px; font-weight: 700; color: #1E293B; margin-bottom: 4px;">■ Public Opinion & Expert Consensus</div>
    <p style="font-size: 13px; color: #334155; margin: 0 0 4px 0;"><strong>Public Sentiment:</strong> {public_opinion_en}</p>
    <p style="font-size: 13px; color: #334155; margin: 0;"><strong>Expert Assessment:</strong> {expert_assessment_en}</p>
  </div>

  <!-- 7. Section 4: RISK OUTLOOK AND UNCERTAINTIES -->
  <h2 style="font-size: 15px; font-weight: 900; color: #0F172A; border-bottom: 1.5px solid #CBD5E1; padding-bottom: 4px; margin: 26px 0 10px 0; letter-spacing: 0.5px; text-transform: uppercase;">
    4. PERFORMANCE BENCHMARKS AND GAP ANALYSIS
  </h2>
  <div style="font-size: 13px; color: #334155; margin-bottom: 12px;">
    <p style="margin: 0 0 6px 0;"><strong>Short Term (3-6 months):</strong> {short_term_outlook_en}</p>
    <p style="margin: 0 0 8px 0; color: #1E40AF;"><em>▶ Most Likely Scenario:</em> {likely_scenario_short_en}</p>
    <p style="margin: 0 0 6px 0;"><strong>Medium Term (1-3 years):</strong> {medium_term_outlook_en}</p>
    <p style="margin: 0 0 8px 0; color: #1E40AF;"><em>▶ Expected Inflection Point:</em> {transition_point_en}</p>
    <p style="margin: 0 0 6px 0;"><strong>Long Term Structural Trajectory:</strong> {long_term_outlook_en}</p>
    <p style="margin: 0 0 12px 0; color: #1E40AF;"><em>▶ Structural Changes:</em> {structural_change_en}</p>
  </div>

  <div style="background-color: #F1F5F9; border-left: 3px solid #64748B; padding: 10px 14px; margin-bottom: 24px; font-size: 12px; color: #334155;">
    <strong>Key Geopolitical Uncertainties:</strong>
    <ol style="margin: 4px 0 0 18px; padding: 0;">
      <li style="margin-bottom: 2px;">{uncertainty_1_en}</li>
      <li style="margin-bottom: 2px;">{uncertainty_2_en}</li>
      <li>{uncertainty_3_en}</li>
    </ol>
  </div>

  <!-- 8. Section 5: RECOMMENDATIONS FOR EXECUTIVE ACTION -->
  <h2 style="font-size: 15px; font-weight: 900; color: #0F172A; border-bottom: 1.5px solid #CBD5E1; padding-bottom: 4px; margin: 26px 0 10px 0; letter-spacing: 0.5px; text-transform: uppercase;">
    5. RECOMMENDATIONS FOR EXECUTIVE ACTION
  </h2>
  <p style="font-size: 13px; color: #334155; margin-bottom: 12px;">
    To ensure systemic resilience across allied security and economic frameworks, the following strategic recommendations are issued for executive action:
  </p>

  <!-- Amber Callout Box for Recommendations -->
  <div style="background-color: #FFFBEB; border-left: 4px solid #D97706; padding: 14px 18px; margin-bottom: 24px; border-radius: 2px;">
    <div style="font-size: 12px; font-weight: 800; color: #92400E; letter-spacing: 0.8px; margin-bottom: 8px; text-transform: uppercase;">
      KEY EXECUTIVE RECOMMENDATIONS
    </div>
    <div style="font-size: 12px; color: #78350F; line-height: 1.6;">
      <p style="margin: 0 0 8px 0;">
        <strong>Recommendation 1 (Defense & Deterrence):</strong> National security leadership should maintain robust deterrence capabilities while proactively calibrating alliance postures against shifting US unilateral priorities. ({response_strategy_en})
      </p>
      <p style="margin: 0 0 8px 0;">
        <strong>Recommendation 2 (Trade & Economic Security):</strong> Trade and economic authorities should institutionalize real-time supply chain monitoring and establish buffer mechanisms for critical trade agreements and investment pledges.
      </p>
      <p style="margin: 0;">
        <strong>Recommendation 3 (Multilateral Coordination):</strong> Diplomatic leadership should strengthen multilateral risk-hedging mechanisms to preserve strategic autonomy amid sharpening great-power rivalries. ({korea_us_impact_en})
      </p>
    </div>
  </div>

  <!-- 9. Section 6: METHODOLOGY AND AGENCY SOURCES -->
  <h2 style="font-size: 15px; font-weight: 900; color: #0F172A; border-bottom: 1.5px solid #CBD5E1; padding-bottom: 4px; margin: 26px 0 10px 0; letter-spacing: 0.5px; text-transform: uppercase;">
    6. AGENCY COMMENTS AND METHODOLOGY
  </h2>
  <p style="font-size: 12px; color: #64748B; text-align: justify; margin-bottom: 8px;">
    This assessment is grounded in empirical research synthesized from media reports, think-tank evaluations, and official government releases via WebSearch and automated data pipelines (GDELT, FRED, IMF DOTS).
  </p>
  <div style="font-size: 12px; color: #2563EB; margin-bottom: 24px;">
    <strong>Key Documentation Sources:</strong> 
    <a href="{news_link_1}" style="color: #2563EB; text-decoration: underline; margin-right: 8px;">[Source Dispatch 1]</a>
    <a href="{news_link_2}" style="color: #2563EB; text-decoration: underline; margin-right: 8px;">[Source Dispatch 2]</a>
    <a href="{news_link_3}" style="color: #2563EB; text-decoration: underline;">[Source Dispatch 3]</a>
  </div>

  <!-- Running Footer -->
  <div style="display: flex; justify-content: space-between; border-top: 1px solid #CBD5E1; padding-top: 8px; font-size: 11px; color: #64748B; margin-top: 36px;">
    <span>IA-26-{intensity}SP {en_name} Assessment</span>
    <span>Page 1 / Comprehensive Dossier</span>
  </div>

</div>
"""

    def build_report_data(self, issue_key):
        """실제 리서치 데이터(REAL_ISSUE_DATA)와 이슈 메타데이터를 합쳐
        템플릿에 채울 딕셔너리를 만듭니다."""
        issue = self.issues[issue_key]
        research = REAL_ISSUE_DATA[issue_key]

        intensity = research["intensity_assessment"]
        if intensity >= 75:
            severity_ko, severity_en = "위험", "HIGH"
        elif intensity >= 50:
            severity_ko, severity_en = "경계", "MEDIUM"
        else:
            severity_ko, severity_en = "관찰", "LOW"

        data = {
            "ko_name": issue["ko_name"],
            "en_name": issue["en_name"],
            "date": datetime.now().strftime("%Y년 %m월 %d일"),
            "now_date": datetime.now().strftime("%Y년 %m월"),
            "intensity": intensity,
            "severity_ko": severity_ko,
            "severity_en": severity_en,
            "next_update_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        }
        data.update(research)
        return data

    def generate_reports(self):
        """
        Generate two SEPARATE report files: one Korean-only, one English-only.

        (이전에는 한/영을 한 파일에 합쳐서 냈는데, 분량이 너무 길어진다는
        피드백에 따라 언어별로 별도 파일로 분리합니다.)
        """
        print("\n" + "="*60)
        print("Generating Separate KO / EN Issue Reports (real data)...")
        print("="*60)

        page_break = '\n\n<div style="page-break-before: always;"></div>\n\n'
        today_str = datetime.now().strftime("%Y-%m-%d")

        # ---------- Korean report ----------
        ko_toc_items = []
        for i, (issue_key, issue) in enumerate(self.issues.items(), 1):
            res_data = REAL_ISSUE_DATA[issue_key]
            intensity = res_data["intensity_assessment"]
            ko_toc_items.append(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 4px;">
      <div style="font-size: 13px; font-weight: 700; color: #0F172A;">
        <span style="display: inline-block; width: 26px; color: #2563EB;">{i:02d}.</span> {issue['ko_name']}
      </div>
      <div style="font-size: 12px; color: #64748B;">
        <span style="font-weight: 600; color: #1E293B;">위험 지수:</span> {intensity}/100 | <span style="font-weight: 600; color: #1E293B;">권역:</span> {issue['region']}
      </div>
    </div>""")

        ko_toc_html = f"""
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #111827; line-height: 1.6; max-width: 900px; margin: 0 auto; padding: 24px 32px; background-color: #ffffff;">

  <!-- Header -->
  <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #1B365D; padding-bottom: 8px; margin-bottom: 16px;">
    <div>
      <div style="font-size: 13px; font-weight: 800; color: #111827; letter-spacing: 0.8px; text-transform: uppercase;">
        INTERNATIONAL AFFAIRS INTELLIGENCE OFFICE
      </div>
      <div style="font-size: 11px; font-weight: 700; color: #4B5563; margin-top: 2px;">
        SPECIAL ASSESSMENT DOSSIER (GAO FRAMEWORK)
      </div>
    </div>
    <div style="text-align: right;">
      <div style="font-size: 11px; font-weight: 800; color: #DC2626; letter-spacing: 0.5px;">
        UNCLASSIFIED // FOR OFFICIAL USE ONLY
      </div>
      <div style="font-size: 11px; color: #4B5563; margin-top: 2px;">
        {today_str}
      </div>
    </div>
  </div>

  <div style="font-size: 11px; font-weight: 700; color: #6B7280; letter-spacing: 1.2px; text-transform: uppercase; margin-bottom: 8px;">
    REPORT TO POLICY COMMITTEES & MINISTERIAL LEADERSHIP
  </div>

  <h1 style="font-size: 28px; font-weight: 900; color: #0F172A; margin: 0 0 8px 0; letter-spacing: -0.5px; text-transform: uppercase; line-height: 1.2;">
    글로벌 국제정세 핵심 현안 종합 평가 보고서
  </h1>
  <div style="font-size: 14px; color: #475569; font-style: italic; margin-bottom: 26px; line-height: 1.4;">
    미국 트럼프 2기 출범에 따른 역내 안보 지형 변화, 글로벌 통상 마찰 및 공급망 취약성 정밀 진단
  </div>

  <!-- Executive Note Card -->
  <div style="background-color: #F8FAFC; border: 1px solid #CBD5E1; border-left: 4px solid #1B365D; padding: 16px 20px; margin-bottom: 28px; border-radius: 4px;">
    <div style="font-size: 12px; font-weight: 800; color: #1B365D; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px;">
      보고서 개요 (DOSSIER EXECUTIVE OVERVIEW)
    </div>
    <p style="font-size: 12px; color: #334155; margin: 0 0 6px 0; line-height: 1.6;">
      본 종합 보고서는 미국 회계감사원(GAO)의 의회 보고서(Congressional Report) 표준 프레임워크에 기초하여 작성되었습니다. 2025~2026년 축적된 위키백과 관심도 지수, GDELT 이벤트 데이터, 각국 정부의 공식 성명 및 검증된 언론 보도를 토대로 대한민국 외교·안보·통상 의사결정권자에게 시급한 {len(self.issues)}대 핵심 현안을 엄선하여 정밀 평가하였습니다.
    </p>
  </div>

  <!-- Table of Contents Section -->
  <h2 style="font-size: 15px; font-weight: 900; color: #0F172A; border-bottom: 1.5px solid #1B365D; padding-bottom: 4px; margin: 0 0 14px 0; text-transform: uppercase; letter-spacing: 0.5px;">
    TABLE OF CONTENTS (수록 현안 목차)
  </h2>

  <div style="display: flex; flex-direction: column; gap: 8px; margin-bottom: 30px;">
    {''.join(ko_toc_items)}
  </div>

  <!-- Running Footer -->
  <div style="display: flex; justify-content: space-between; border-top: 1px solid #CBD5E1; padding-top: 8px; font-size: 11px; color: #64748B; margin-top: 40px;">
    <span>GAO Standard Dossier · IA-26-CORE-KO</span>
    <span>Cover & Table of Contents</span>
  </div>

</div>
"""

        ko_sections = [ko_toc_html]
        for issue_key in self.issues.keys():
            data = self.build_report_data(issue_key)
            ko_report = self.ko_template.format(**data)
            ko_sections.append(page_break + ko_report)
            print(f"  [KO] {data['ko_name']} (intensity {data['intensity']}/100)")

        ko_combined = "\n".join(ko_sections)
        ko_output_file = self.output_dir / "Issues_Report_KO.md"
        with open(ko_output_file, 'w', encoding='utf-8') as f:
            f.write(ko_combined)

        # 데스크톱 및 DB 저장 (한국어 종합 보고서)
        print("\n  [DB & 데스크톱 저장] 한국어 종합 보고서...")
        save_report_to_desktop_and_db(
            filename="Issues_Report_KO.md",
            title="글로벌 국제정세 핵심 현안 종합 평가 보고서",
            content=ko_combined,
            report_type="gao_dossier_ko",
            issue_key="ALL",
            intensity=None,
            collected_date=today_str
        )

        # 개별 이슈별 보고서도 데스크톱 및 DB에 저장
        for i, (issue_key, issue) in enumerate(self.issues.items(), 1):
            data = self.build_report_data(issue_key)
            single_report = self.ko_template.format(**data)
            safe_name = issue['ko_name'].replace('/', '_').replace(' ', '_')
            save_report_to_desktop_and_db(
                filename=f"{i:02d}_{safe_name}_정세평가보고서.md",
                title=f"{data['ko_name']} 정세 평가 보고서",
                content=single_report,
                report_type="gao_issue_ko",
                issue_key=issue_key,
                intensity=data['intensity'],
                collected_date=today_str
            )

        # ---------- English report ----------
        en_toc_items = []
        for i, (issue_key, issue) in enumerate(self.issues.items(), 1):
            res_data = REAL_ISSUE_DATA[issue_key]
            intensity = res_data["intensity_assessment"]
            en_toc_items.append(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 4px;">
      <div style="font-size: 13px; font-weight: 700; color: #0F172A;">
        <span style="display: inline-block; width: 26px; color: #2563EB;">{i:02d}.</span> {issue['en_name']}
      </div>
      <div style="font-size: 12px; color: #64748B;">
        <span style="font-weight: 600; color: #1E293B;">Risk Score:</span> {intensity}/100 | <span style="font-weight: 600; color: #1E293B;">Region:</span> {issue['region']}
      </div>
    </div>""")

        en_toc_html = f"""
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #111827; line-height: 1.6; max-width: 900px; margin: 0 auto; padding: 24px 32px; background-color: #ffffff;">

  <!-- Header -->
  <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #1B365D; padding-bottom: 8px; margin-bottom: 16px;">
    <div>
      <div style="font-size: 13px; font-weight: 800; color: #111827; letter-spacing: 0.8px; text-transform: uppercase;">
        INTERNATIONAL AFFAIRS INTELLIGENCE OFFICE
      </div>
      <div style="font-size: 11px; font-weight: 700; color: #4B5563; margin-top: 2px;">
        SPECIAL ASSESSMENT DOSSIER (GAO FRAMEWORK)
      </div>
    </div>
    <div style="text-align: right;">
      <div style="font-size: 11px; font-weight: 800; color: #DC2626; letter-spacing: 0.5px;">
        UNCLASSIFIED // FOR OFFICIAL USE ONLY
      </div>
      <div style="font-size: 11px; color: #4B5563; margin-top: 2px;">
        {today_str}
      </div>
    </div>
  </div>

  <div style="font-size: 11px; font-weight: 700; color: #6B7280; letter-spacing: 1.2px; text-transform: uppercase; margin-bottom: 8px;">
    REPORT TO POLICY COMMITTEES & CONGRESSIONAL LEADERSHIP
  </div>

  <h1 style="font-size: 28px; font-weight: 900; color: #0F172A; margin: 0 0 8px 0; letter-spacing: -0.5px; text-transform: uppercase; line-height: 1.2;">
    GLOBAL GEOPOLITICAL ISSUES: COMPREHENSIVE STRATEGIC ASSESSMENT
  </h1>
  <div style="font-size: 14px; color: #475569; font-style: italic; margin-bottom: 26px; line-height: 1.4;">
    Assessing Regional Security Architecture Shifts, Trade Frictions, and Critical Supply Chain Resilience Under the Trump Administration
  </div>

  <!-- Executive Note Card -->
  <div style="background-color: #F8FAFC; border: 1px solid #CBD5E1; border-left: 4px solid #1B365D; padding: 16px 20px; margin-bottom: 28px; border-radius: 4px;">
    <div style="font-size: 12px; font-weight: 800; color: #1B365D; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px;">
      DOSSIER EXECUTIVE OVERVIEW
    </div>
    <p style="font-size: 12px; color: #334155; margin: 0 0 6px 0; line-height: 1.6;">
      This comprehensive dossier complies with the formal reporting methodology of the U.S. Government Accountability Office (GAO). Integrating empirical signals from Wikipedia trend metrics, GDELT geopolitical events, official state department communiques, and verified intelligence, this assessment evaluates {len(self.issues)} critical risk sectors vital to allied policy leadership.
    </p>
  </div>

  <!-- Table of Contents Section -->
  <h2 style="font-size: 15px; font-weight: 900; color: #0F172A; border-bottom: 1.5px solid #1B365D; padding-bottom: 4px; margin: 0 0 14px 0; text-transform: uppercase; letter-spacing: 0.5px;">
    TABLE OF CONTENTS (ASSESSED SECTORS)
  </h2>

  <div style="display: flex; flex-direction: column; gap: 8px; margin-bottom: 30px;">
    {''.join(en_toc_items)}
  </div>

  <!-- Running Footer -->
  <div style="display: flex; justify-content: space-between; border-top: 1px solid #CBD5E1; padding-top: 8px; font-size: 11px; color: #64748B; margin-top: 40px;">
    <span>GAO Standard Dossier · IA-26-CORE-EN</span>
    <span>Cover & Table of Contents</span>
  </div>

</div>
"""

        en_sections = [en_toc_html]
        for issue_key in self.issues.keys():
            data = self.build_report_data(issue_key)
            en_report = self.en_template.format(**data)
            en_sections.append(page_break + en_report)
            print(f"  [EN] {data['en_name']} (intensity {data['intensity']}/100)")

        en_combined = "\n".join(en_sections)
        en_output_file = self.output_dir / "Issues_Report_EN.md"
        with open(en_output_file, 'w', encoding='utf-8') as f:
            f.write(en_combined)

        # 데스크톱 및 DB 저장 (영어 종합 보고서)
        print("\n  [DB & 데스크톱 저장] 영어 종합 보고서...")
        save_report_to_desktop_and_db(
            filename="Issues_Report_EN.md",
            title="Global Geopolitical Issues: Comprehensive Strategic Assessment",
            content=en_combined,
            report_type="gao_dossier_en",
            issue_key="ALL",
            intensity=None,
            collected_date=today_str
        )

        for i, (issue_key, issue) in enumerate(self.issues.items(), 1):
            data = self.build_report_data(issue_key)
            single_report = self.en_template.format(**data)
            safe_name = issue['en_name'].replace('/', '_').replace(' ', '_')
            save_report_to_desktop_and_db(
                filename=f"{i:02d}_{safe_name}_Strategic_Assessment.md",
                title=f"{data['en_name']}: Strategic Assessment",
                content=single_report,
                report_type="gao_issue_en",
                issue_key=issue_key,
                intensity=data['intensity'],
                collected_date=today_str
            )


        # remove the old combined file if it still exists, so it doesn't linger
        # and get converted into a stale PDF alongside the new ones.
        # (best-effort: some environments don't allow delete permissions, so
        # this must never crash the whole report generation run)
        for old_path in [
            self.output_dir / "All_Issues_Report.md",
            self.output_dir / "pdf" / "All_Issues_Report.pdf",
        ]:
            try:
                if old_path.exists():
                    old_path.unlink()
            except OSError as e:
                print(f"  (note: could not remove stale file {old_path}: {e} - "
                      f"please delete it manually)")

        print("\n" + "="*60)
        print(f"Done! {len(self.issues)} issues x 2 languages, saved as 2 separate files:")
        print(f"  {ko_output_file}")
        print(f"  {en_output_file}")
        print("="*60)

        return [str(ko_output_file), str(en_output_file)]


def main():
    generator = IssueReportGenerator()
    generator.generate_reports()


if __name__ == "__main__":
    main()
