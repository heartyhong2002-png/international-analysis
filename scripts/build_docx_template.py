"""
build_docx_template.py — Builds the official declassified intelligence Word template
(templates/official_report_template.docx) using python-docx and docxtpl XML markup.
"""

from pathlib import Path
import docx
from docx.shared import Inches, Pt, RGBColor, Mm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATE_PATH = TEMPLATES_DIR / "official_report_template.docx"


def set_cell_background(cell, hex_color: str):
    """Sets background fill color of a table cell."""
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)


def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Sets cell padding (in twips: 20 twips = 1 pt)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


def set_table_borders(table, color="D1D5DB", sz="4", val="single"):
    """Sets clean subtle borders on a table."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideV w:val="none"/>'
        f'<w:left w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)


def format_paragraph(p, text, font_name="Malgun Gothic", size_pt=9.0, bold=False, italic=False,
                     color_rgb=(31, 41, 55), align=WD_ALIGN_PARAGRAPH.LEFT,
                     space_before=0, space_after=2, line_spacing=1.15):
    """Convenience helper to format a paragraph and its run."""
    p.alignment = align
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = line_spacing
    run = p.add_run(text)
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor(*color_rgb)
    # Hint for East Asian fonts in Word
    rPr = run._r.get_or_add_rPr()
    rFonts = parse_xml(f'<w:rFonts {nsdecls("w")} w:ascii="{font_name}" w:eastAsia="{font_name}" w:hAnsi="{font_name}"/>')
    rPr.append(rFonts)
    return run


def build_template():
    doc = docx.Document()

    # 1. Page Margins (20mm all around)
    for section in doc.sections:
        section.top_margin = Mm(20)
        section.bottom_margin = Mm(20)
        section.left_margin = Mm(20)
        section.right_margin = Mm(20)
        section.different_first_page_header_footer = True

        # Header for later pages
        header = section.header
        hp = header.paragraphs[0]
        format_paragraph(
            hp,
            "UNCLASSIFIED // {{ case_id }} // {{ report_title }}",
            font_name="Malgun Gothic",
            size_pt=8.0,
            bold=True,
            color_rgb=(107, 114, 128),
            space_after=4,
        )

        # Footer for later pages
        footer = section.footer
        fp = footer.paragraphs[0]
        format_paragraph(
            fp,
            "UNCLASSIFIED  |  INTERNATIONAL AFFAIRS INTELLIGENCE DIRECTORATE",
            font_name="Malgun Gothic",
            size_pt=8.0,
            bold=False,
            color_rgb=(156, 163, 175),
            align=WD_ALIGN_PARAGRAPH.CENTER,
        )

    # 2. Top Red Approved Stamp
    p_stamp = doc.add_paragraph()
    format_paragraph(
        p_stamp,
        "{{ red_stamp }}",
        font_name="Malgun Gothic",
        size_pt=8.5,
        bold=True,
        color_rgb=(200, 16, 46),  # Crimson Red #C8102E
        space_after=4,
    )

    # 3. Official Form Header Bar Table (FORM IA-1036, UNCLASSIFIED, OFFICIAL RECORD)
    table_hdr = doc.add_table(rows=1, cols=3)
    table_hdr.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_hdr.autofit = False

    widths_hdr = [Inches(1.8), Inches(3.4), Inches(1.8)]
    for row in table_hdr.rows:
        for idx, width in enumerate(widths_hdr):
            row.cells[idx].width = width
            set_cell_margins(row.cells[idx], top=40, bottom=40, left=40, right=40)

    cell_l, cell_m, cell_r = table_hdr.rows[0].cells
    cell_l.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    cell_m.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    cell_r.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    p_l = cell_l.paragraphs[0]
    format_paragraph(p_l, "FORM IA-1036 (Rev. 2026-09)", font_name="Malgun Gothic", size_pt=8.0, bold=False, color_rgb=(75, 85, 99))

    p_m = cell_m.paragraphs[0]
    format_paragraph(p_m, "UNCLASSIFIED", font_name="Malgun Gothic", size_pt=9.5, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, color_rgb=(17, 24, 39))

    # Bordered Official Record seal
    p_r = cell_r.paragraphs[0]
    format_paragraph(p_r, "[ OFFICIAL RECORD ]\nAUTHENTICATED", font_name="Malgun Gothic", size_pt=6.5, bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT, color_rgb=(55, 65, 81), line_spacing=1.0)

    # 4. Agency Heading
    p_agency1 = doc.add_paragraph()
    format_paragraph(
        p_agency1,
        "INTERNATIONAL AFFAIRS INTELLIGENCE DIRECTORATE",
        font_name="Malgun Gothic",
        size_pt=14.0,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        color_rgb=(17, 24, 39),
        space_before=8,
        space_after=2,
    )

    p_agency2 = doc.add_paragraph()
    format_paragraph(
        p_agency2,
        "Strategic Threat & Geopolitical Assessment Form  |  국제정세 및 전략위협 평가보고서",
        font_name="Malgun Gothic",
        size_pt=9.5,
        bold=False,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        color_rgb=(75, 85, 99),
        space_before=0,
        space_after=6,
    )

    # 5. Metadata Grid Table
    t_meta = doc.add_table(rows=5, cols=2)
    t_meta.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_meta.autofit = False
    set_table_borders(t_meta, color="9CA3AF", sz="6", val="single")

    widths_meta = [Inches(4.5), Inches(2.5)]
    for r in t_meta.rows:
        for idx, width in enumerate(widths_meta):
            r.cells[idx].width = width
            set_cell_margins(r.cells[idx], top=60, bottom=60, left=80, right=80)

    # Row 0
    p00 = t_meta.rows[0].cells[0].paragraphs[0]
    format_paragraph(p00, "Form Type: IA-71A - Strategic Threat Dossier", size_pt=8.0, bold=True, color_rgb=(31, 41, 55))
    p01 = t_meta.rows[0].cells[1].paragraphs[0]
    format_paragraph(p01, "Date: {{ report_date }}", size_pt=8.0, bold=True, color_rgb=(31, 41, 55))

    # Row 1 (Merge)
    cell_t1 = t_meta.rows[1].cells[0]
    cell_t2 = t_meta.rows[1].cells[1]
    cell_t1.merge(cell_t2)
    p10 = cell_t1.paragraphs[0]
    format_paragraph(p10, "Title: (U) {{ report_title }}", size_pt=8.5, bold=True, color_rgb=(17, 24, 39))

    # Row 2 (Merge)
    cell_a1 = t_meta.rows[2].cells[0]
    cell_a2 = t_meta.rows[2].cells[1]
    cell_a1.merge(cell_a2)
    p20 = cell_a1.paragraphs[0]
    format_paragraph(p20, "Approved By: [ ████████ ] CHIEF OF STRATEGIC ASSESSMENT", size_pt=8.0, color_rgb=(55, 65, 81))

    # Row 3 (Merge)
    cell_d1 = t_meta.rows[3].cells[0]
    cell_d2 = t_meta.rows[3].cells[1]
    cell_d1.merge(cell_d2)
    p30 = cell_d1.paragraphs[0]
    format_paragraph(p30, "Drafted By:  [ ████████ ] STRATEGIC REGIONAL DESK", size_pt=8.0, color_rgb=(55, 65, 81))

    # Row 4
    p40 = t_meta.rows[4].cells[0].paragraphs[0]
    format_paragraph(p40, "Case ID #: {{ case_id }}", size_pt=8.0, bold=True, color_rgb=(31, 41, 55))
    p41 = t_meta.rows[4].cells[1].paragraphs[0]
    format_paragraph(p41, "Subject: {{ case_subject }}", size_pt=8.0, bold=True, color_rgb=(31, 41, 55))

    # 6. Synopsis
    p_syn_head = doc.add_paragraph()
    format_paragraph(
        p_syn_head,
        "Synopsis: (U) DOCUMENT SYNOPSIS CREATED ON {{ report_date }} {{ report_time }} KST -- SEE STRATEGIC REPOSITORY FOR LIVE DATA",
        font_name="Malgun Gothic",
        size_pt=9.0,
        bold=True,
        color_rgb=(17, 24, 39),
        space_before=8,
        space_after=2,
    )

    p_syn1 = doc.add_paragraph()
    format_paragraph(p_syn1, "(U) {{ synopsis_1 }}", size_pt=8.5, space_before=0, space_after=3, line_spacing=1.2)

    p_syn2 = doc.add_paragraph()
    format_paragraph(p_syn2, "(U) {{ synopsis_2 }}", size_pt=8.5, space_before=0, space_after=8, line_spacing=1.2)

    # 7. Section 1: BACKGROUND AND SCOPE
    p_sec1 = doc.add_paragraph()
    format_paragraph(p_sec1, "1. 배경 및 정세 평가 (BACKGROUND AND SCOPE)", size_pt=10.0, bold=True, color_rgb=(17, 24, 39), space_before=6, space_after=3)

    p_bg = doc.add_paragraph()
    format_paragraph(p_bg, "(U) {{ background_text }}", size_pt=8.5, space_before=0, space_after=4, line_spacing=1.2)

    p_time_title = doc.add_paragraph()
    format_paragraph(p_time_title, "주요 신호 및 사태 전개 타임라인 (Chronology of Key Intelligence Signals):", size_pt=9.0, bold=True, color_rgb=(31, 41, 55), space_before=4, space_after=3)

    # Timeline Table with docxtpl row loop
    t_time = doc.add_table(rows=1, cols=2)
    t_time.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_time.autofit = False
    set_table_borders(t_time, color="111827", sz="6", val="single")

    # Header Row
    widths_time = [Inches(1.8), Inches(5.2)]
    hdr_time = t_time.rows[0].cells
    hdr_time[0].width = widths_time[0]
    hdr_time[1].width = widths_time[1]
    set_cell_background(hdr_time[0], "F3F4F6")
    set_cell_background(hdr_time[1], "F3F4F6")
    set_cell_margins(hdr_time[0], top=80, bottom=80, left=80, right=80)
    set_cell_margins(hdr_time[1], top=80, bottom=80, left=80, right=80)
    format_paragraph(hdr_time[0].paragraphs[0], "단계 (Phase)", size_pt=8.0, bold=True, color_rgb=(17, 24, 39))
    format_paragraph(hdr_time[1].paragraphs[0], "관측 사안 및 정보 신호 (Observed Incident & Signal)", size_pt=8.0, bold=True, color_rgb=(17, 24, 39))

    # Looping rows for docxtpl
    r_for = t_time.add_row()
    r_for.cells[0].text = "{%tr for item in timeline %}"

    r_data = t_time.add_row()
    r_data.cells[0].width = widths_time[0]
    r_data.cells[1].width = widths_time[1]
    set_cell_margins(r_data.cells[0], top=60, bottom=60, left=80, right=80)
    set_cell_margins(r_data.cells[1], top=60, bottom=60, left=80, right=80)
    format_paragraph(r_data.cells[0].paragraphs[0], "{{ item.phase }}", size_pt=8.0, bold=True, color_rgb=(31, 41, 55))
    format_paragraph(r_data.cells[1].paragraphs[0], "{{ item.content }}", size_pt=8.0, color_rgb=(31, 41, 55), line_spacing=1.15)

    r_end = t_time.add_row()
    r_end.cells[0].text = "{%tr endfor %}"

    # Analyst Assessment
    p_analyst = doc.add_paragraph()
    format_paragraph(p_analyst, "(U) 분석관 평가 (Analyst Assessment): {{ objective_analysis }}", size_pt=8.5, bold=False, color_rgb=(31, 41, 55), space_before=5, space_after=8, line_spacing=1.2)

    # 8. Section 2: STAKEHOLDER STRATEGIC POSTURE
    p_sec2 = doc.add_paragraph()
    format_paragraph(p_sec2, "2. 주요 당사국 전략적 태세 (STAKEHOLDER STRATEGIC POSTURE)", size_pt=10.0, bold=True, color_rgb=(17, 24, 39), space_before=6, space_after=3)

    t_posture = doc.add_table(rows=5, cols=2)
    t_posture.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_posture.autofit = False
    set_table_borders(t_posture, color="111827", sz="6", val="single")

    widths_posture = [Inches(1.8), Inches(5.2)]
    hdr_p = t_posture.rows[0].cells
    hdr_p[0].width = widths_posture[0]
    hdr_p[1].width = widths_posture[1]
    set_cell_background(hdr_p[0], "F3F4F6")
    set_cell_background(hdr_p[1], "F3F4F6")
    set_cell_margins(hdr_p[0], top=80, bottom=80, left=80, right=80)
    set_cell_margins(hdr_p[1], top=80, bottom=80, left=80, right=80)
    format_paragraph(hdr_p[0].paragraphs[0], "당사국 (Actor)", size_pt=8.0, bold=True, color_rgb=(17, 24, 39))
    format_paragraph(hdr_p[1].paragraphs[0], "공식 입장 및 전략적 대응 태세 (Official Stance & Strategic Posture)", size_pt=8.0, bold=True, color_rgb=(17, 24, 39))

    actors = [
        ("미국 (United States)", "{{ us_position }}"),
        ("중국 (China)", "{{ china_position }}"),
        ("대한민국 (South Korea)", "{{ korea_position }}"),
        ("기타 주요국 (Other Actors)", "{{ others_position }}"),
    ]

    for idx, (actor_name, var_tag) in enumerate(actors, start=1):
        row_c = t_posture.rows[idx].cells
        row_c[0].width = widths_posture[0]
        row_c[1].width = widths_posture[1]
        set_cell_margins(row_c[0], top=60, bottom=60, left=80, right=80)
        set_cell_margins(row_c[1], top=60, bottom=60, left=80, right=80)
        format_paragraph(row_c[0].paragraphs[0], actor_name, size_pt=8.0, bold=True, color_rgb=(31, 41, 55))
        format_paragraph(row_c[1].paragraphs[0], var_tag, size_pt=8.0, color_rgb=(31, 41, 55), line_spacing=1.15)

    # 9. Section 3: ECONOMIC AND SECURITY IMPACT ANALYSIS
    p_sec3 = doc.add_paragraph()
    format_paragraph(p_sec3, "3. 경제 및 안보 파급영향 분석 (ECONOMIC AND SECURITY IMPACT ANALYSIS)", size_pt=10.0, bold=True, color_rgb=(17, 24, 39), space_before=10, space_after=3)

    # Security
    p_sec_sub = doc.add_paragraph()
    format_paragraph(p_sec_sub, "■ 안보 및 군사적 파급효과 (Security Dimension)", size_pt=9.0, bold=True, color_rgb=(31, 41, 55), space_before=4, space_after=2)

    sec_items = [
        ("한반도 안보 영향", "{{ north_korea_impact }}"),
        ("동맹 구도 및 방위태세", "{{ alliance_impact }}"),
        ("군사적 위협 수준", "{{ missile_threat }}"),
    ]
    for label, val in sec_items:
        p_item = doc.add_paragraph()
        format_paragraph(p_item, f"(U) {label}: {val}", size_pt=8.5, color_rgb=(31, 41, 55), space_before=0, space_after=2, line_spacing=1.15)

    # Economic
    p_eco_sub = doc.add_paragraph()
    format_paragraph(p_eco_sub, "■ 경제 및 통상 파급효과 (Economic Dimension)", size_pt=9.0, bold=True, color_rgb=(31, 41, 55), space_before=4, space_after=2)

    eco_items = [
        ("통상 및 관세 영향", "{{ trade_impact }}"),
        ("외환 및 금융시장 영향", "{{ fx_impact }}"),
        ("핵심 산업 및 투자 영향", "{{ investment_impact }}"),
    ]
    for label, val in eco_items:
        p_item = doc.add_paragraph()
        format_paragraph(p_item, f"(U) {label}: {val}", size_pt=8.5, color_rgb=(31, 41, 55), space_before=0, space_after=2, line_spacing=1.15)

    # Public Opinion & Expert
    p_pop_sub = doc.add_paragraph()
    format_paragraph(p_pop_sub, "■ 여론 및 전문가 평가 (Public Opinion & Expert Assessment)", size_pt=9.0, bold=True, color_rgb=(31, 41, 55), space_before=4, space_after=2)

    pop_items = [
        ("국내외 여론 동향", "{{ public_opinion }}"),
        ("학계·싱크탱크 전문가 평가", "{{ expert_assessment }}"),
    ]
    for label, val in pop_items:
        p_item = doc.add_paragraph()
        format_paragraph(p_item, f"(U) {label}: {val}", size_pt=8.5, color_rgb=(31, 41, 55), space_before=0, space_after=2, line_spacing=1.15)

    # 10. Section 4: RISK OUTLOOK AND UNCERTAINTY ANALYSIS
    p_sec4 = doc.add_paragraph()
    format_paragraph(p_sec4, "4. 위험 전망 및 불확실성 요인 (RISK OUTLOOK AND UNCERTAINTY ANALYSIS)", size_pt=10.0, bold=True, color_rgb=(17, 24, 39), space_before=10, space_after=3)

    p_ro1 = doc.add_paragraph()
    format_paragraph(p_ro1, "(U) 단기 전망 (3~6개월): {{ short_term_outlook }}", size_pt=8.5, bold=True, color_rgb=(31, 41, 55), space_after=1)
    p_ro1_sc = doc.add_paragraph()
    format_paragraph(p_ro1_sc, "    ▶ 유력 시나리오: {{ likely_scenario_short }}", size_pt=8.5, color_rgb=(55, 65, 81), space_after=3, line_spacing=1.15)

    p_ro2 = doc.add_paragraph()
    format_paragraph(p_ro2, "(U) 중기 전망 (1~3년): {{ medium_term_outlook }}", size_pt=8.5, bold=True, color_rgb=(31, 41, 55), space_after=1)
    p_ro2_sc = doc.add_paragraph()
    format_paragraph(p_ro2_sc, "    ▶ 주요 전환점: {{ transition_point }}", size_pt=8.5, color_rgb=(55, 65, 81), space_after=3, line_spacing=1.15)

    p_ro3 = doc.add_paragraph()
    format_paragraph(p_ro3, "(U) 장기 구조적 변화: {{ long_term_outlook }}", size_pt=8.5, bold=True, color_rgb=(31, 41, 55), space_after=1)
    p_ro3_sc = doc.add_paragraph()
    format_paragraph(p_ro3_sc, "    ▶ 구조적 리스크: {{ structural_change }}", size_pt=8.5, color_rgb=(55, 65, 81), space_after=4, line_spacing=1.15)

    p_unc_head = doc.add_paragraph()
    format_paragraph(p_unc_head, "핵심 불확실성 요인 (Key Uncertainties):", size_pt=9.0, bold=True, color_rgb=(31, 41, 55), space_before=3, space_after=2)

    p_unc_loop = doc.add_paragraph()
    format_paragraph(p_unc_loop, "{% for unc in uncertainties %}• {{ unc }}\n{% endfor %}", size_pt=8.5, color_rgb=(55, 65, 81), space_before=0, space_after=4, line_spacing=1.15)

    # 11. Section 5: KEY STRATEGIC RECOMMENDATIONS
    p_sec5 = doc.add_paragraph()
    format_paragraph(p_sec5, "5. 핵심 전략적 정책 제언 (KEY STRATEGIC RECOMMENDATIONS)", size_pt=10.0, bold=True, color_rgb=(17, 24, 39), space_before=10, space_after=3)

    p_rec_loop = doc.add_paragraph()
    format_paragraph(
        p_rec_loop,
        "{% for rec in recommendations %}■ {{ rec.label }}\n{{ rec.text }}\n\n{% endfor %}",
        size_pt=8.5,
        color_rgb=(31, 41, 55),
        space_before=0,
        space_after=4,
        line_spacing=1.15,
    )

    # 12. Section 6: DATABASE QUERIES & METHODOLOGY
    p_sec6 = doc.add_paragraph()
    format_paragraph(p_sec6, "6. 데이터베이스 검증 쿼리 및 분석 방법론 (DATABASE QUERIES & METHODOLOGY)", size_pt=10.0, bold=True, color_rgb=(17, 24, 39), space_before=10, space_after=3)

    p_db_loop = doc.add_paragraph()
    format_paragraph(p_db_loop, "{% for q in db_queries %}• {{ q }}\n{% endfor %}", size_pt=8.5, color_rgb=(55, 65, 81), space_before=0, space_after=4, line_spacing=1.15)

    p_src_head = doc.add_paragraph()
    format_paragraph(p_src_head, "주요 출처 및 팩트체크 로그 (Key Sources & Verification Log):", size_pt=9.0, bold=True, color_rgb=(31, 41, 55), space_before=3, space_after=2)

    p_src_body = doc.add_paragraph()
    format_paragraph(p_src_body, "{{ key_sources }}", size_pt=8.5, color_rgb=(75, 85, 99), space_before=0, space_after=6, line_spacing=1.15)

    # 13. Enclosure(s)
    p_enc_head = doc.add_paragraph()
    format_paragraph(p_enc_head, "첨부 증빙 자료 (Enclosure(s)):", size_pt=9.0, bold=True, color_rgb=(31, 41, 55), space_before=4, space_after=2)

    p_enc_loop = doc.add_paragraph()
    format_paragraph(p_enc_loop, "{% for enc in enclosures %}• {{ enc }}\n{% endfor %}", size_pt=8.5, color_rgb=(75, 85, 99), space_before=0, space_after=8, line_spacing=1.15)

    # 14. Document Terminator
    p_term = doc.add_paragraph()
    format_paragraph(p_term, "◆◆", font_name="Malgun Gothic", size_pt=10.0, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, color_rgb=(31, 41, 55), space_before=8, space_after=12)

    doc.save(str(TEMPLATE_PATH))
    print(f"[Success] Official report Word template saved to: {TEMPLATE_PATH}")


if __name__ == "__main__":
    build_template()
