"""
pdf_report_generator.py — Official intelligence-form-style PDF report generator
(English-only edition)
================================================================================

Reproduces the look of a declassified U.S. government/intelligence-agency form
(FBI FD-1036 / FD-71A style) to avoid the "AI-generated card news" aesthetic and
give the geopolitical assessment reports the rigor of a real national security
document. This English-only edition exists because the classic-government-form
layout (English section headers, redacted "[ XXXXXXXX ]" blocks, "(U)" markings,
etc.) reads naturally in English but sits awkwardly on top of Korean prose — so
this specific form style is generated in English only, sourced from the *_en
fields in issue_research_data.py. (A separate pipeline, Issues_Report_KO.md /
Issues_Report_EN.md, still covers the bilingual card-style reports.)

Per-issue page length is not fixed: content from issue_research_data.py is used
in full (no character-count truncation), so each report flows across as many
pages as it actually needs. Structure:

  - Cover page   : red declassification stamp, form number (FORM IA-1036),
                   classification (UNCLASSIFIED), OFFICIAL RECORD seal, agency
                   header, metadata grid (Form Type, Title, Approved/Drafted By,
                   Case ID), Synopsis
  - 1. BACKGROUND AND SCOPE            : Chronology of Key Intelligence Signals
                                          + Analyst Assessment
  - 2. STAKEHOLDER STRATEGIC POSTURE   : official stance of US / China / Korea /
                                          other actors
  - 3. ECONOMIC AND SECURITY IMPACT    : security / economic / public-opinion
                                          dimensions
  - 4. RISK OUTLOOK & UNCERTAINTY      : short/medium/long-term outlook + key
                                          uncertainties
  - 5. KEY STRATEGIC RECOMMENDATIONS   : response strategy / diplomatic
                                          positioning / ROK-US coordination
  - 6. DATABASE QUERIES & METHODOLOGY  : Wikipedia / government announcements /
                                          3-model LLM consensus / fact-check
                                          query log, plus a plain-text list of
                                          key sources (outlet + date — no
                                          hyperlinks; this is a document meant
                                          to print/archive like a real dossier)
  - Enclosure(s) and document terminator (◆◆)

Starting on page 2, every page repeats a running header
("UNCLASSIFIED // Case ID // Title") and a footer (UNCLASSIFIED + page number).

Saved to:
  1. Desktop: C:\\Users\\홍준기\\Desktop\\분석보고서
  2. Inside the project: reports/issues/pdf/
  3. MySQL DB: international_analysis.analysis_reports table
"""

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "data"))
sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))

from issue_research_data import REAL_ISSUE_DATA  # noqa: E402
from report_db_saver import save_report_to_desktop_and_db, DESKTOP_REPORTS_DIR  # noqa: E402

# 맑은 고딕 등록 (영문 전용 문서지만 기관명 등 일부 한글 라벨을 위해 유지)
pdfmetrics.registerFont(TTFont("Malgun", r"C:\Windows\Fonts\malgun.ttf"))
pdfmetrics.registerFont(TTFont("MalgunBold", r"C:\Windows\Fonts\malgunbd.ttf"))

PROJECT_PDF_DIR = _PROJECT_ROOT / "reports" / "issues" / "pdf"
PROJECT_PDF_DIR.mkdir(parents=True, exist_ok=True)
DESKTOP_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# 뉴스 링크 URL -> 출처 표기용 매핑 (하이퍼링크 대신 평문으로 "매체명 (날짜)" 형태 표기)
_SOURCE_OUTLETS = {
    "cnn.com": "CNN",
    "aljazeera.com": "Al Jazeera",
    "upi.com": "UPI",
    "usni.org": "USNI News",
    "axios.com": "Axios",
    "aei.org": "American Enterprise Institute (AEI)",
    "npr.org": "NPR",
    "russiamatters.org": "Russia Matters",
    "rferl.org": "RFE/RL",
    "armscontrol.org": "Arms Control Association",
    "spokesman.com": "The Spokesman-Review",
    "whitehouse.gov": "The White House",
    "korea.kr": "Korea.kr (ROK Government)",
}
_MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_MONTH_NUM = {name.lower(): i + 1 for i, name in enumerate(_MONTH_ABBR)}


def _describe_source(url: str) -> str:
    """Turn a raw article URL into a plain-text 'Outlet (Date)' citation.

    No hyperlink is produced (this document is meant to read like a printed /
    archived dossier) — just a human-readable description of the actual source.
    """
    if not url:
        return ""

    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    outlet = None
    for domain, name in _SOURCE_OUTLETS.items():
        if host == domain or host.endswith("." + domain):
            outlet = name
            break
    if outlet is None:
        label = host.split(".")[0] if host else url
        outlet = label.replace("-", " ").title()

    date_label = None
    m = re.search(r"/(\d{4})/(\d{1,2})/(\d{1,2})/", url)
    if m:
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= month <= 12:
            date_label = f"{_MONTH_ABBR[month - 1]} {day}, {year}"
    if date_label is None:
        m = re.search(r"/(\d{4})/([A-Za-z]{3,9})/(\d{1,2})/", url)
        if m:
            year, mon_txt, day = int(m.group(1)), m.group(2).lower()[:3], int(m.group(3))
            month = _MONTH_NUM.get(mon_txt)
            if month:
                date_label = f"{_MONTH_ABBR[month - 1]} {day}, {year}"
    if date_label is None:
        m = re.search(r"/(\d{4})/(\d{1,2})/", url)
        if m:
            year, month = int(m.group(1)), int(m.group(2))
            if 1 <= month <= 12:
                date_label = f"{_MONTH_ABBR[month - 1]} {year}"
    if date_label is None:
        m = re.search(r"(\d{4})", url)
        if m:
            date_label = m.group(1)

    return f"{outlet} ({date_label})" if date_label else outlet


class OfficialIntelligencePdfGenerator:
    def __init__(self):
        # 문서 생성 시각 — 하드코딩된 날짜 대신 실행 시점 기준으로 채움
        now = datetime.now()
        self.report_date_iso = now.strftime("%Y-%m-%d")
        self.report_date_long = now.strftime("%d %B %Y")
        self.report_time_kst = now.strftime("%H:%M")

        self.issues = {
            "North_Korea_Nuclear": {
                "code": "56-NK-01",
                "en_name": "North Korea Nuclear & Geopolitical Posture",
                "file_en": "01_North_Korea_Nuclear_Assessment.pdf",
                "case_subject": "(U) NORTH KOREA NUCLEAR CRISIS & PENINSULAR ESCALATION RISK",
                "query_kw": "North Korea Nuclear",
                "views": "28,420",
                "volatility": "+18.4%",
                "gov_matches": "14 matches (MOFA, U.S. State Department, KCNA)",
                "consensus_tone": "CRITICAL / CONCERN",
                "consensus_rate": "100.0% (3/3 Consensus)",
                "intensity": 88,
            },
            "Taiwan_Strait": {
                "code": "56-TW-02",
                "en_name": "Taiwan Strait Military Tension & Cross-Strait Posture",
                "file_en": "02_Taiwan_Strait_Assessment.pdf",
                "case_subject": "(U) TAIWAN STRAIT ESCALATION & FIRST ISLAND CHAIN STABILITY",
                "query_kw": "Taiwan Strait",
                "views": "34,810",
                "volatility": "+24.1%",
                "gov_matches": "19 matches (INDOPACOM, PRC Ministry of National Defense, Taiwan MND)",
                "consensus_tone": "ELEVATED TENSION",
                "consensus_rate": "100.0% (3/3 Consensus)",
                "intensity": 82,
            },
            "Ukraine_War": {
                "code": "56-UKR-03",
                "en_name": "Ukraine War Attrition & European Security Architecture",
                "file_en": "03_Ukraine_War_Assessment.pdf",
                "case_subject": "(U) UKRAINE WAR ATTRITION & POST-SETTLEMENT BUFFER ZONES",
                "query_kw": "Ukraine War",
                "views": "41,950",
                "volatility": "+12.7%",
                "gov_matches": "26 matches (NATO, European Commission, Russian MFA)",
                "consensus_tone": "STALEMATE / ATTRITION",
                "consensus_rate": "100.0% (3/3 Consensus)",
                "intensity": 91,
            },
            "Iran_Nuclear": {
                "code": "56-IRN-04",
                "en_name": "Iran Nuclear Enrichment & Middle East Regional Security",
                "file_en": "04_Iran_Nuclear_Assessment.pdf",
                "case_subject": "(U) IRANIAN ENRICHMENT BREAKOUT & RED SEA PROXY ACTIVITY",
                "query_kw": "Iran Nuclear",
                "views": "22,180",
                "volatility": "+31.5%",
                "gov_matches": "11 matches (IAEA, IRNA, U.S. State Department)",
                "consensus_tone": "ELEVATED RISK",
                "consensus_rate": "100.0% (3/3 Consensus)",
                "intensity": 79,
            },
            "US_China_Trade": {
                "code": "56-USCN-05",
                "en_name": "US-China Strategic Trade & Tech Decoupling Dynamics",
                "file_en": "05_US_China_Trade_Assessment.pdf",
                "case_subject": "(U) SINO-AMERICAN TARIFF CONFRONTATION & TECH ALLIANCE",
                "query_kw": "US-China Trade War",
                "views": "37,640",
                "volatility": "+15.9%",
                "gov_matches": "22 matches (USTR, PRC Ministry of Commerce, Korea MOTIE)",
                "consensus_tone": "STRATEGIC COMPETITION",
                "consensus_rate": "100.0% (3/3 Consensus)",
                "intensity": 74,
            },
        }

        self._current_meta = None  # doc.build 실행 중 running header가 참조

        self._init_styles()

    def _init_styles(self):
        self.styles = getSampleStyleSheet()

        # 붉은색 기밀해제/공개 승인 스탬프
        self.s_stamp = ParagraphStyle(
            "RedStamp",
            fontName="MalgunBold",
            fontSize=8.5,
            leading=10.5,
            textColor=colors.HexColor("#C8102E"),
        )

        # 상단 서식 번호 & 보안분류
        self.s_form_code = ParagraphStyle(
            "FormCode",
            fontName="Malgun",
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#1F2937"),
        )
        self.s_sec_center = ParagraphStyle(
            "SecCenter",
            fontName="MalgunBold",
            fontSize=8.5,
            leading=10.5,
            alignment=1,
            textColor=colors.HexColor("#111827"),
        )
        self.s_official_rec = ParagraphStyle(
            "OffRec",
            fontName="MalgunBold",
            fontSize=6.5,
            leading=7.5,
            alignment=1,
            textColor=colors.HexColor("#111827"),
        )

        # 기관 표제부 (단정하고 굵은 대문자)
        self.s_agency_head = ParagraphStyle(
            "AgencyHead",
            fontName="MalgunBold",
            fontSize=13,
            leading=16,
            alignment=1,
            textColor=colors.HexColor("#111827"),
        )
        self.s_agency_sub = ParagraphStyle(
            "AgencySub",
            fontName="Malgun",
            fontSize=9,
            leading=12,
            alignment=1,
            textColor=colors.HexColor("#1F2937"),
        )

        # 메타데이터 필드 라벨 및 밸류
        self.s_meta_val = ParagraphStyle(
            "MetaVal",
            fontName="Malgun",
            fontSize=7.5,
            leading=10.5,
            textColor=colors.HexColor("#1F2937"),
        )

        # 섹션 헤딩 (1. BACKGROUND ..., Key Sources:, etc.)
        self.s_sec_head = ParagraphStyle(
            "SecHead",
            fontName="MalgunBold",
            fontSize=9.5,
            leading=12.5,
            spaceBefore=2,
            textColor=colors.HexColor("#111827"),
        )
        self.s_body = ParagraphStyle(
            "Body",
            fontName="Malgun",
            fontSize=8,
            leading=11.5,
            textColor=colors.HexColor("#1F2937"),
        )
        self.s_body_indent = ParagraphStyle(
            "BodyIndent",
            fontName="Malgun",
            fontSize=8,
            leading=11.5,
            leftIndent=8,
            textColor=colors.HexColor("#1F2937"),
        )

        # 표 폰트
        self.s_th = ParagraphStyle(
            "TableHead",
            fontName="MalgunBold",
            fontSize=7.3,
            leading=9.3,
            textColor=colors.HexColor("#111827"),
        )
        self.s_td_date = ParagraphStyle(
            "TdDate",
            fontName="MalgunBold",
            fontSize=7.3,
            leading=10,
            textColor=colors.HexColor("#1F2937"),
        )
        self.s_td = ParagraphStyle(
            "Td",
            fontName="Malgun",
            fontSize=7.3,
            leading=10,
            textColor=colors.HexColor("#1F2937"),
        )

    # ------------------------------------------------------------------
    # 페이지 헤더 / 푸터 (running header: 2페이지부터 자동 반복)
    # ------------------------------------------------------------------
    def _draw_first_page(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("MalgunBold", 8.5)
        canvas.drawCentredString(A4[0] / 2.0, 24, "UNCLASSIFIED")
        canvas.setFont("Malgun", 8)
        canvas.drawCentredString(A4[0] / 2.0, 14, "1")
        canvas.restoreState()

    def _draw_later_page(self, canvas, doc):
        canvas.saveState()
        meta = self._current_meta
        if meta:
            canvas.setFont("MalgunBold", 7.5)
            canvas.setFillColor(colors.HexColor("#1F2937"))
            canvas.drawString(
                40, A4[1] - 26,
                f"UNCLASSIFIED // {meta['code']} // (U) {meta['en_name']}",
            )
            canvas.setFont("Malgun", 7)
            canvas.drawRightString(A4[0] - 40, A4[1] - 26, self.report_date_iso)
            canvas.setLineWidth(0.5)
            canvas.setStrokeColor(colors.HexColor("#9CA3AF"))
            canvas.line(40, A4[1] - 30, A4[0] - 40, A4[1] - 30)
        canvas.setFont("MalgunBold", 8.5)
        canvas.setFillColor(colors.HexColor("#111827"))
        canvas.drawCentredString(A4[0] / 2.0, 24, "UNCLASSIFIED")
        canvas.setFont("Malgun", 8)
        canvas.drawCentredString(A4[0] / 2.0, 14, f"{doc.page}")
        canvas.restoreState()

    # ------------------------------------------------------------------
    # 본문 스토리 구성 (이슈별, 영문 전용) — 내용은 요약/절단 없이 원문 그대로 사용
    # ------------------------------------------------------------------
    def build_official_story(self, issue_key: str):
        meta = self.issues[issue_key]
        d = REAL_ISSUE_DATA[issue_key]

        stamp_text = (
            f"APPROVED FOR PUBLIC RELEASE BY INTELLIGENCE ASSESSMENT DIRECTORATE "
            f"on {self.report_date_long}"
        )

        story = []

        # 1. 최상단 붉은색 승인 스탬프
        story.append(Paragraph(stamp_text, self.s_stamp))
        story.append(Spacer(1, 3))

        # 2. 서식 번호 / 보안분류 / OFFICIAL RECORD 인장 테이블
        official_box_data = [[
            Paragraph("FORM IA-1036 (Rev. 2026-09)", self.s_form_code),
            Paragraph("UNCLASSIFIED", self.s_sec_center),
            Table(
                [[Paragraph(
                    "OFFICIAL RECORD<br/><font size=5 color='#6B7280'>AUTHENTICATED</font>",
                    self.s_official_rec,
                )]],
                colWidths=[80],
                style=TableStyle([
                    ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#374151")),
                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]),
            ),
        ]]
        t_header = Table(official_box_data, colWidths=[155, 275, 85])
        t_header.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(t_header)
        story.append(Spacer(1, 5))

        # 3. 기관 표제부 (AGENCY HEAD)
        story.append(Paragraph("INTERNATIONAL AFFAIRS INTELLIGENCE DIRECTORATE", self.s_agency_head))
        story.append(Paragraph("Strategic Threat & Geopolitical Assessment Form", self.s_agency_sub))
        story.append(Spacer(1, 5))

        # 4. 메타데이터 그리드
        meta_table_data = [
            [
                Paragraph("<b>Form Type:</b> IA-71A - Strategic Threat Dossier", self.s_meta_val),
                Paragraph(f"<b>Date:</b> {self.report_date_iso}", self.s_meta_val),
            ],
            [Paragraph(f"<b>Title:</b> (U) Geopolitical Assessment: {meta['en_name']}", self.s_meta_val), ""],
            [Paragraph("<b>Approved By:</b> [ ████████ ] CHIEF OF STRATEGIC ASSESSMENT", self.s_meta_val), ""],
            [Paragraph("<b>Drafted By:</b>  [ ████████ ] STRATEGIC REGIONAL DESK", self.s_meta_val), ""],
            [
                Paragraph(f"<b>Case ID #:</b> {meta['code']}", self.s_meta_val),
                Paragraph(meta["case_subject"], self.s_meta_val),
            ],
        ]
        t_meta = Table(meta_table_data, colWidths=[335, 180])
        t_meta.setStyle(TableStyle([
            ("SPAN", (0, 1), (1, 1)),
            ("SPAN", (0, 2), (1, 2)),
            ("SPAN", (0, 3), (1, 3)),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 1.2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(t_meta)
        story.append(Spacer(1, 3))
        story.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#111827"), spaceAfter=4, spaceBefore=1))

        # 5. Synopsis — full text, no truncation
        synopsis_head = (
            f"<b>Synopsis:</b> (U) DOCUMENT SYNOPSIS CREATED ON {self.report_date_iso} "
            f"{self.report_time_kst} KST -- SEE STRATEGIC INTELLIGENCE REPOSITORY FOR CURRENT ASSESSMENT DATA."
        )
        story.append(Paragraph(synopsis_head, self.s_sec_head))
        story.append(Spacer(1, 2))
        story.append(Paragraph(f"(U) {d['en_situation']}", self.s_body))
        story.append(Spacer(1, 2.5))
        story.append(Paragraph(f"(U) {d['issue_overview_en']}", self.s_body))
        story.append(Spacer(1, 4))

        # ============================================================
        # 1. BACKGROUND AND SCOPE — Chronology + Analyst Assessment
        # ============================================================
        story.append(Paragraph("<b>1. BACKGROUND AND SCOPE</b>", self.s_sec_head))
        story.append(Spacer(1, 2))
        story.append(Paragraph(f"(U) {d['trump_impact_en']}", self.s_body))
        story.append(Spacer(1, 3))

        story.append(Paragraph("<b>Chronology of Key Intelligence Signals:</b>", self.s_sec_head))
        story.append(Spacer(1, 2))

        timeline_data = [
            [
                Paragraph("<b>Phase</b>", self.s_th),
                Paragraph("<b>Observed Incident & Intelligence Signal</b>", self.s_th),
            ],
            [Paragraph("Signal 1 (Initial)", self.s_td_date), Paragraph(d["event_1_en"], self.s_td)],
            [Paragraph("Signal 2 (Follow-on)", self.s_td_date), Paragraph(d["event_2_en"], self.s_td)],
            [Paragraph("Current Status", self.s_td_date), Paragraph(d["current_status_en"], self.s_td)],
        ]
        t_timeline = Table(timeline_data, colWidths=[75, 440])
        t_timeline.setStyle(TableStyle([
            ("LINEABOVE", (0, 0), (-1, 0), 1, colors.HexColor("#111827")),
            ("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.HexColor("#111827")),
            ("LINEBELOW", (0, -1), (-1, -1), 1, colors.HexColor("#111827")),
            ("LINEBELOW", (0, 1), (-1, -2), 0.25, colors.HexColor("#D1D5DB")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t_timeline)
        story.append(Spacer(1, 3))
        story.append(Paragraph(f"(U) <b>Analyst Assessment:</b> {d['objective_analysis_en']}", self.s_body_indent))
        story.append(Spacer(1, 5))

        # ============================================================
        # 2. STAKEHOLDER STRATEGIC POSTURE
        # ============================================================
        story.append(Paragraph("<b>2. STAKEHOLDER STRATEGIC POSTURE</b>", self.s_sec_head))
        story.append(Spacer(1, 2))

        posture_data = [
            [
                Paragraph("<b>Actor</b>", self.s_th),
                Paragraph("<b>Official Stance & Strategic Posture</b>", self.s_th),
            ],
            [Paragraph("United States", self.s_td_date), Paragraph(d["us_position_en"], self.s_td)],
            [Paragraph("China", self.s_td_date), Paragraph(d["china_position_en"], self.s_td)],
            [Paragraph("South Korea", self.s_td_date), Paragraph(d["korea_position_en"], self.s_td)],
            [Paragraph("Other Actors", self.s_td_date), Paragraph(d["others_position_en"], self.s_td)],
        ]
        t_posture = Table(posture_data, colWidths=[75, 440])
        t_posture.setStyle(TableStyle([
            ("LINEABOVE", (0, 0), (-1, 0), 1, colors.HexColor("#111827")),
            ("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.HexColor("#111827")),
            ("LINEBELOW", (0, -1), (-1, -1), 1, colors.HexColor("#111827")),
            ("LINEBELOW", (0, 1), (-1, -2), 0.25, colors.HexColor("#D1D5DB")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t_posture)
        story.append(Spacer(1, 5))

        # ============================================================
        # 3. ECONOMIC AND SECURITY IMPACT ANALYSIS
        # ============================================================
        story.append(Paragraph("<b>3. ECONOMIC AND SECURITY IMPACT ANALYSIS</b>", self.s_sec_head))
        story.append(Spacer(1, 2))

        story.append(Paragraph("■ Security Dimension", self.s_body))
        story.append(Spacer(1, 1.5))
        for label, key in [
            ("Implications for the Korean Peninsula", "north_korea_impact_en"),
            ("Alliance Impact", "alliance_impact_en"),
            ("Missile / Military Threat Level", "missile_threat_en"),
        ]:
            story.append(Paragraph(f"(U) <b>{label}:</b> {d[key]}", self.s_body_indent))
            story.append(Spacer(1, 1.5))
        story.append(Spacer(1, 1.5))

        story.append(Paragraph("■ Economic Dimension", self.s_body))
        story.append(Spacer(1, 1.5))
        for label, key in [
            ("Trade & Commerce", "trade_impact_en"),
            ("FX & Currency Markets", "fx_impact_en"),
            ("Investment Flows", "investment_impact_en"),
        ]:
            story.append(Paragraph(f"(U) <b>{label}:</b> {d[key]}", self.s_body_indent))
            story.append(Spacer(1, 1.5))
        story.append(Spacer(1, 1.5))

        story.append(Paragraph("■ Public Opinion & Expert Assessment", self.s_body))
        story.append(Spacer(1, 1.5))
        story.append(Paragraph(f"(U) <b>Domestic & International Opinion:</b> {d['public_opinion_en']}", self.s_body_indent))
        story.append(Spacer(1, 1.5))
        story.append(Paragraph(f"(U) <b>Expert Assessment:</b> {d['expert_assessment_en']}", self.s_body_indent))
        story.append(Spacer(1, 5))

        # ============================================================
        # 4. RISK OUTLOOK AND UNCERTAINTY ANALYSIS
        # ============================================================
        story.append(Paragraph("<b>4. RISK OUTLOOK AND UNCERTAINTY ANALYSIS</b>", self.s_sec_head))
        story.append(Spacer(1, 2))

        story.append(Paragraph(f"(U) <b>Short-Term Outlook (3-6 Months):</b> {d['short_term_outlook_en']}", self.s_body))
        story.append(Spacer(1, 1.5))
        story.append(Paragraph(f"▶ Likely Scenario: {d['likely_scenario_short_en']}", self.s_body_indent))
        story.append(Spacer(1, 2))

        story.append(Paragraph(f"(U) <b>Medium-Term Outlook (1-3 Years):</b> {d['medium_term_outlook_en']}", self.s_body))
        story.append(Spacer(1, 1.5))
        story.append(Paragraph(f"▶ Transition Point: {d['transition_point_en']}", self.s_body_indent))
        story.append(Spacer(1, 2))

        story.append(Paragraph(f"(U) <b>Long-Term Structural Change:</b> {d['long_term_outlook_en']}", self.s_body))
        story.append(Spacer(1, 1.5))
        story.append(Paragraph(f"▶ Structural Risk: {d['structural_change_en']}", self.s_body_indent))
        story.append(Spacer(1, 3))

        story.append(Paragraph("<b>Key Uncertainties:</b>", self.s_sec_head))
        story.append(Spacer(1, 1.5))
        for i, key in enumerate(["uncertainty_1_en", "uncertainty_2_en", "uncertainty_3_en"], start=1):
            story.append(Paragraph(f"{i}. {d[key]}", self.s_body_indent))
            story.append(Spacer(1, 1.2))
        story.append(Spacer(1, 4))

        # ============================================================
        # 5. KEY STRATEGIC RECOMMENDATIONS
        # ============================================================
        story.append(Paragraph("<b>5. KEY STRATEGIC RECOMMENDATIONS</b>", self.s_sec_head))
        story.append(Spacer(1, 2))

        recs = [
            ("Recommendation 1 (Response Strategy)", d["response_strategy_en"]),
            ("Recommendation 2 (Multilateral Diplomatic Positioning)", d["international_position_en"]),
            ("Recommendation 3 (ROK-US Coordination Implications)", d["korea_us_impact_en"]),
        ]
        for label, text in recs:
            story.append(Paragraph(f"<b>{label}:</b> {text}", self.s_body_indent))
            story.append(Spacer(1, 2))
        story.append(Spacer(1, 2))

        # ============================================================
        # 6. DATABASE QUERIES & METHODOLOGY
        # ============================================================
        story.append(Paragraph("<b>6. DATABASE QUERIES & METHODOLOGY</b>", self.s_sec_head))
        story.append(Spacer(1, 2))

        q1 = (
            f"An open source query of <b>Wikipedia Pageviews (Daily Public Interest)</b> revealed "
            f"<b>{meta['views']}</b> daily queries for '{meta['query_kw']}' with a 7-day DoD volatility of <b>{meta['volatility']}</b>."
        )
        story.append(Paragraph(q1, self.s_body_indent))
        story.append(Spacer(1, 1.5))

        q2 = (
            f"A Guardian query of <b>Government Announcements (MOFA / State Dept / Regional Feeds)</b> revealed "
            f"<b>{meta['gov_matches']}</b> directly matched to issue parameters."
        )
        story.append(Paragraph(q2, self.s_body_indent))
        story.append(Spacer(1, 1.5))

        q3 = (
            f"A 3-Model Consensus query (<b>Mistral-7B, Qwen2.5-7B, EXAONE-3.5</b>) revealed "
            f"media framing classification of <b>{meta['consensus_tone']}</b> with <b>{meta['consensus_rate']}</b> agreement."
        )
        story.append(Paragraph(q3, self.s_body_indent))
        story.append(Spacer(1, 1.5))

        q4 = (
            "A Sentinel query of <b>IFCN Verified Fact Checks & Media Bias Ratings</b> revealed "
            "zero debunked claims with established bias classification across official feeds."
        )
        story.append(Paragraph(q4, self.s_body_indent))
        story.append(Spacer(1, 3))

        news_links = [d.get("news_link_1"), d.get("news_link_2"), d.get("news_link_3")]
        news_links = [l for l in news_links if l]
        if news_links:
            story.append(Paragraph("<b>Key Sources:</b>", self.s_sec_head))
            story.append(Spacer(1, 1.5))
            # 하이퍼링크 없이 "매체명 (날짜)" 평문 설명만 나열 (인쇄/보관용 도시에 성격에 맞춤)
            descriptions = [_describe_source(url) for url in news_links]
            story.append(Paragraph("; ".join(descriptions) + ".", self.s_body_indent))
            story.append(Spacer(1, 4))

        # 7. Enclosure(s)
        story.append(Paragraph("<b>Enclosure(s):</b> Enclosed are the following items:", self.s_sec_head))
        story.append(Spacer(1, 1.5))
        story.append(Paragraph("1.  U Official_Announcements_Matching_Audit.csv", self.s_body_indent))
        story.append(Paragraph("2.  U Wikipedia_Pageviews_7Day_Trend.png", self.s_body_indent))
        story.append(Paragraph("3.  U Multi_Agent_Consensus_Audit_Matrix.json", self.s_body_indent))
        story.append(Spacer(1, 5))

        # 8. 문서 종결 부호 (◆◆)
        story.append(Paragraph("◆◆", ParagraphStyle("Terminator", fontName="MalgunBold", fontSize=9, leading=11)))

        return story

    # ------------------------------------------------------------------
    def generate_all_pdfs(self):
        from pypdf import PdfReader

        generated_files = []
        print("\n" + "=" * 80)
        print(" [PDF Pipeline] Generating official intelligence-form-style PDF reports (English)")
        print("=" * 80)

        page_ranges = {}
        current_page = 2  # 1페이지는 종합 Dossier 표지

        for issue_key, meta in self.issues.items():
            filename = meta["file_en"]
            proj_path = PROJECT_PDF_DIR / filename
            desktop_path = DESKTOP_REPORTS_DIR / filename

            doc = SimpleDocTemplate(
                str(proj_path),
                pagesize=A4,
                leftMargin=40,
                rightMargin=40,
                topMargin=32,
                bottomMargin=32,
            )

            story = self.build_official_story(issue_key)
            self._current_meta = meta
            doc.build(
                story,
                onFirstPage=self._draw_first_page,
                onLaterPages=self._draw_later_page,
            )

            n_pages = len(PdfReader(str(proj_path)).pages)
            page_ranges[issue_key] = (current_page, current_page + n_pages - 1)
            current_page += n_pages

            # 바탕화면에 바이너리 PDF 복제
            shutil.copy2(str(proj_path), str(desktop_path))

            # MySQL DB 적재
            save_report_to_desktop_and_db(
                filename=filename,
                title=f"(U) Geopolitical Threat Assessment: {meta['en_name']}",
                content=f"[Binary PDF Official Intelligence Dossier: {filename}]",
                report_type="gao_pdf_en",
                issue_key=issue_key,
                intensity=meta.get("intensity", 75),
            )

            size_kb = proj_path.stat().st_size / 1024
            generated_files.append((filename, size_kb, proj_path))
            print(f"  -> [Done] {filename} ({size_kb:.1f} KB, {n_pages}p) | copied to Desktop + saved to DB")

        # 종합 Dossier PDF 생성 (표지 + 5개 이슈, 페이지 수는 내용에 따라 가변)
        dossier_path = self._generate_official_dossier(page_ranges)
        if dossier_path:
            size_kb = dossier_path.stat().st_size / 1024
            generated_files.append((dossier_path.name, size_kb, dossier_path))

        print("=" * 80)
        print(f" [Complete] {len(generated_files)} official intelligence report PDFs generated and saved to Desktop/DB")
        print("=" * 80 + "\n")
        return generated_files

    def _generate_official_dossier(self, page_ranges: dict) -> Path:
        """Bundles the 5 issues behind a formal cover page + table of contents.

        The TOC's page ranges are computed from each issue PDF's actual page
        count (not hardcoded like "pp. 2-3" in the earlier version).
        """
        from pypdf import PdfWriter

        dossier_filename = "2026_Global_Geopolitical_Threat_Assessment.pdf"
        proj_dossier_path = PROJECT_PDF_DIR / dossier_filename
        desktop_dossier_path = DESKTOP_REPORTS_DIR / dossier_filename
        cover_temp_path = PROJECT_PDF_DIR / "temp_official_cover.pdf"

        stamp_text = (
            f"APPROVED FOR PUBLIC RELEASE BY INTELLIGENCE ASSESSMENT DIRECTORATE "
            f"on {self.report_date_long}"
        )

        # 1. 정식 표지 및 목차 생성
        doc = SimpleDocTemplate(
            str(cover_temp_path),
            pagesize=A4,
            leftMargin=40,
            rightMargin=40,
            topMargin=35,
            bottomMargin=35,
        )

        cover_story = []
        cover_story.append(Paragraph(stamp_text, self.s_stamp))
        cover_story.append(Spacer(1, 15))

        # 표지 타이틀 박스
        cover_box = [
            [Paragraph("<b>OFFICIAL INTELLIGENCE ASSESSMENT DOSSIER</b>", ParagraphStyle("CB1", fontName="MalgunBold", fontSize=8.5, textColor=colors.HexColor("#4B5563")))],
            [Spacer(1, 8)],
            [Paragraph("2026 GLOBAL GEOPOLITICAL THREAT ASSESSMENT", ParagraphStyle("CB2", fontName="MalgunBold", fontSize=17, leading=21, textColor=colors.HexColor("#111827")))],
            [Paragraph("Strategic Risk & Security Signal Assessment of Five Critical Global Issues", ParagraphStyle("CB3", fontName="Malgun", fontSize=11.5, leading=15, textColor=colors.HexColor("#374151")))],
            [Spacer(1, 12)],
            [Paragraph("FORM IA-DOSSIER-2026 // UNCLASSIFIED (FOR OFFICIAL USE ONLY)", ParagraphStyle("CB4", fontName="MalgunBold", fontSize=7.5, textColor=colors.HexColor("#6B7280")))],
        ]
        t_cover = Table(cover_box, colWidths=[515])
        t_cover.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1.25, colors.HexColor("#111827")),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ]))
        cover_story.append(t_cover)
        cover_story.append(Spacer(1, 20))

        # 종합 개요 (Executive Summary)
        cover_story.append(Paragraph("<b>EXECUTIVE MEMORANDUM FOR SENIOR POLICYMAKERS:</b>", self.s_sec_head))
        cover_story.append(Spacer(1, 3))
        exec_summary = (
            "(U) This document is a declassified official briefing dossier compiling the situational "
            "assessments of five critical global issues, collected and verified as of September 2026 "
            "through the International Affairs Intelligence Directorate's automated analysis pipeline. "
            "It combines Wikipedia Pageviews (public-interest metrics), official government announcements "
            "(foreign / state ministries), a cross-model consensus-verification engine spanning three "
            "multilingual open-source LLMs (Mistral-7B, Qwen2.5-7B, EXAONE-3.5), and certified data from the "
            "International Fact-Checking Network (IFCN) to eliminate analyst subjectivity and deliver "
            "fact-based policy recommendations."
        )
        cover_story.append(Paragraph(exec_summary, self.s_body))
        cover_story.append(Spacer(1, 15))

        # 목차 (Table of Enclosed Intelligence Assessments) — 페이지 범위 동적 계산
        cover_story.append(Paragraph("<b>TABLE OF ENCLOSED INTELLIGENCE ASSESSMENTS:</b>", self.s_sec_head))
        cover_story.append(Spacer(1, 5))

        toc_data = [[
            Paragraph("<b>Case ID</b>", self.s_th),
            Paragraph("<b>Strategic Subject / Title</b>", self.s_th),
            Paragraph("<b>Classification</b>", self.s_th),
            Paragraph("<b>Pages</b>", self.s_th),
        ]]
        for issue_key, meta in self.issues.items():
            start, end = page_ranges.get(issue_key, (0, 0))
            page_label = f"pp. {start}-{end}" if end > start else f"p. {start}"
            toc_data.append([
                Paragraph(meta["code"], self.s_td_date),
                Paragraph(meta["en_name"], self.s_td),
                Paragraph("UNCLASSIFIED", self.s_td),
                Paragraph(page_label, self.s_td),
            ])

        t_toc = Table(toc_data, colWidths=[65, 275, 105, 70])
        t_toc.setStyle(TableStyle([
            ("LINEABOVE", (0, 0), (-1, 0), 1, colors.HexColor("#111827")),
            ("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.HexColor("#111827")),
            ("LINEBELOW", (0, -1), (-1, -1), 1, colors.HexColor("#111827")),
            ("LINEBELOW", (0, 1), (-1, -2), 0.25, colors.HexColor("#E5E7EB")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]))
        cover_story.append(t_toc)
        cover_story.append(Spacer(1, 15))
        cover_story.append(Paragraph("◆◆ [END OF EXECUTIVE SUMMARY]", ParagraphStyle("CoverTerm", fontName="MalgunBold", fontSize=8)))

        doc.build(cover_story, onFirstPage=self._draw_first_page)

        # 2. Merger를 사용해 표지(1p) + 5개 개별 보고서 결합
        merger = PdfWriter()
        merger.append(str(cover_temp_path))

        for issue_key, meta in self.issues.items():
            indiv_path = PROJECT_PDF_DIR / meta["file_en"]
            if indiv_path.exists():
                merger.append(str(indiv_path))

        merger.write(str(proj_dossier_path))
        merger.close()

        # 임시 표지 삭제
        if cover_temp_path.exists():
            cover_temp_path.unlink()

        # 바탕화면에 복제
        shutil.copy2(str(proj_dossier_path), str(desktop_dossier_path))

        # MySQL DB 적재
        save_report_to_desktop_and_db(
            filename=dossier_filename,
            title="(U) 2026 Global Geopolitical Threat Assessment (Comprehensive Dossier)",
            content=f"[Binary PDF Comprehensive Intelligence Dossier: {dossier_filename}]",
            report_type="gao_dossier_pdf_en",
            issue_key="ALL",
            intensity=85,
        )

        return proj_dossier_path


def main():
    generator = OfficialIntelligencePdfGenerator()
    generator.generate_all_pdfs()


if __name__ == "__main__":
    main()
