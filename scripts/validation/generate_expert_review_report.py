"""
generate_expert_review_report.py — 연구실 전문가(교수님·대학원생) & Bluesky 이중 인간 검증 보고서 생성기
====================================================================================================

실제 최신 분석 데이터(data/signal_gap/signal_gap_analysis.json)와
§10.4 독립 검증단 감사 결과(data/validation/multi_judge_audit_latest.json)를 바탕으로,
지도교수님·연구실 대학원생에게 바로 전달할 수 있는 Markdown 및 A4 DOCX 보고서를 생성합니다.

핵심 구조:
  - Part 1~2: 검증 철학, 4계층 모델 역할 분리, 연구실+Bluesky 이중 인간 검증 프로토콜
  - Part 3: Stage 1 블라인드 검수지 (AI 검증단 판정은 마스킹하고 원문·근거·산식만 제시)
  - Part 4: Bluesky 외부 피드백 연계 및 보정 규칙 (§10.2 준수)
  - 부록(Stage 2): 검수 완료 후 개봉하는 AI 검증단 실측 감사 결과표

사용법:
    .venv\\Scripts\\python.exe scripts/validation/generate_expert_review_report.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parents[2]
SIGNAL_GAP_PATH = REPO_ROOT / "data" / "signal_gap" / "signal_gap_analysis.json"
AUDIT_PATH = REPO_ROOT / "data" / "validation" / "multi_judge_audit_latest.json"
OUT_MD = REPO_ROOT / "docs" / "advisor_meeting" / "EXPERT_VALIDATION_REPORT.md"
OUT_DOCX = REPO_ROOT / "docs" / "advisor_meeting" / "EXPERT_VALIDATION_REPORT_A4.docx"


def _load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _format_evidence(evidence: Any) -> List[str]:
    if not evidence:
        return ["(제시된 원문 근거 문장 없음 — 근거 부족 / 확인 필요 대상)"]
    lines = []
    for idx, item in enumerate(evidence, start=1):
        if isinstance(item, dict):
            txt = item.get("phrase") or item.get("text") or json.dumps(item, ensure_ascii=False)
            src = item.get("source") or item.get("url") or ""
            lines.append(f"- `[E-{idx:02d}]` {txt}" + (f" *(출처: {src})*" if src else ""))
        else:
            lines.append(f"- `[E-{idx:02d}]` {item}")
    return lines


def build_markdown(sg_data: Dict[str, Any], audit_data: Dict[str, Any]) -> str:
    today_str = datetime.now().strftime("%Y-%m-%d")
    audit_results = audit_data.get("results", [])

    md: List[str] = [
        "# 국제정세 조기경보 시스템 전문가·커뮤니티 이중 검증 보고서",
        "",
        f"- **작성일**: {today_str}",
        "- **대상**: 지도교수님 · 연구실 대학원생 (1차 내부 전문가 검수) 및 Bluesky 공개 전문가/커뮤니티 (2차 외부 피드백)",
        "- **검증 원칙 (`VALIDATION_PLAN.md`)**: 본 시스템은 미래 사건 발생 여부를 예측하는 도구가 아니라, **특정 시점 공개 원문을 과장·왜곡 없이 출처·근거 문장·경보 수위에 연결했는지**를 감사하는 조기경보 프로토타입입니다. AI 다수결·자동 승인(`auto_accept`)은 전면 금지되며 최종 권위는 결정론적 산식 가드레일과 사람 검수에 있습니다.",
        "",
        "---",
        "",
        "## 1. 모델 및 검증 역할 분리 아키텍처",
        "",
        "번역·요약 생성 모델이 자신의 출력을 스스로 채점하는 편향(Self-Grading)을 원천 차단하기 위해, 생성 트랙과 검증 트랙의 모델 계열을 완전히 분리했습니다.",
        "",
        "| 계층 | 구성 요소 / 모델 | 담당 역할 | 격리·가드레일 원칙 |",
        "| :--- | :--- | :--- | :--- |",
        "| **생성·번역 트랙** | `qwen2.5:7b` · `exaone3.5:7.8b` · `llama3.1:8b` | 다국어 원문 팩트 추출, 한국어 브리핑, 영문 정제 | 검증단 참여 금지 (생성 전용) |",
        "| **결정론적 가드레일** | `calculate_alert_assessment()` | 출처 수·다양성·근거 커버리지·신호 괴리 기반 공식 경보 산출 | LLM 자의적 판단 제어 |",
        "| **독립 배심원 1 (단계)** | `tev1:latest` | 요약 신호 기반 5단계 경보 수위 독립 판정 | 산식 단계·타 모델 출력 비공개 |",
        "| **독립 배심원 2 (사실)** | `gemma2:9b` | `evidence_phrases` 원문 대조 (claim 단위 사실성 감사) | 빈 근거 시 `unverifiable_source_missing` |",
        "| **독립 배심원 3 (논리)** | `nemotron-3-nano:4b` | 사실→경보 추론의 과잉 해석·인과 비약 반박 | 타 모델 출력 비공개 |",
        "| **재판관 (종합 초안)** | `mistral:7b` *(보조 판결관)* | 배심원 3종 판정 + Trigger(`T1~T8`) 종합, 한국어 쟁점 요약 | **최종 확정권 없음** (`auto_accept=false`) |",
        "| **인간 검증 Track 1** | **지도교수님 · 연구실 대학원생** | 블라인드 5항목 검수 + 도메인 전문 판단(`domain_review_needed`) | Stage 1 잠금 후 Stage 2 AI 결과 대조 |",
        "| **인간 검증 Track 2** | **Bluesky 공개 전문가·이용자** | 검수 완료 브리프 게시 후 댓글·반례 수집·전처리·보정 | 전문가 대체물 아님 (보조 교차 신호로 분리) |",
        "",
        "> **외부 API 전송 한계 고지**: 기본 감사 파이프라인은 로컬 Ollama 모델만 사용하지만, `--nim-escalate` 옵션으로 2차 심층 감사를 실행할 경우 프롬프트(권역 요약 및 근거 문장)가 **외부 API(NVIDIA NIM)**로 전송됩니다. 비공개·민감 원문을 다룰 때는 로컬 감사만 사용해야 합니다.",
        "",
        "---",
        "",
        "## 2. 연구실(교수님·대학원생) × Bluesky 이중 검증 운영 절차",
        "",
        "1. **Step 1 — 연구실 내부 블라인드 검수 (Stage 1)**: 아래 **3장(블라인드 검수지)**에서 원문 근거와 산식 경보만 보고 5항목 및 도메인 전문 의견을 먼저 기록합니다. *(편향 방지를 위해 AI 배심원·재판관 의견은 부록으로 분리)*",
        "2. **Step 2 — AI 검증단과 교차 대조 (Stage 2)**: Stage 1 기록을 잠근 뒤 **부록**의 AI 검증단 판정(`gemma2`, `nemotron`, `mistral` 등)을 열어 사람이 놓친 환각·논리 비약이 있는지 비교합니다.",
        "3. **Step 3 — Bluesky 외부 피드백 연계 (확장 트랙)**: 연구실 1차 검수를 통과한 분석 요약을 Bluesky에 게시해 외부 연구자·현업자의 댓글/반론을 수집하고, 스팸 필터링·근거 추출 전처리를 거쳐 최종 브리프 수정에 반영합니다.",
        "",
        "---",
        "",
        "## 3. [Stage 1] 연구실 전문가 블라인드 검수지 (총 7개 권역)",
        "",
        "> **검수 안내**: 국제정치의 미래를 맞히는 것이 아니라, **(1) 제시된 근거 문장이 요약을 실제로 뒷받침하는지**, **(2) 경보 수위가 과장되지 않았는지**, **(3) 군사·외교적 의도나 현지 맥락 등 도메인 전문가 해석이 추가로 필요한지**를 표시해 주세요.",
        "",
    ]

    for idx, row in enumerate(audit_results, start=1):
        region = row["region"]
        sg = sg_data.get(region, {})
        ev_lines = _format_evidence(sg.get("evidence_phrases", []))

        md.extend([
            f"### 3.{idx}. `{region}` (`{row['alert_id']}`)",
            "",
            f"- **분석 시각**: `{sg.get('analyzed_at', '-')}`",
            f"- **산식 1차 경보**: `{row.get('formula_alert_ko', '-')}` (`{row.get('formula_alert_en', '-')}`) | **위험 점수**: `{row.get('risk_signal_score', '-')}`",
            f"- **수집 메타**: 출처 `{sg.get('source_item_count', '-')}`건 · 출처 다양성 `{sg.get('source_diversity', '-')}` · 근거 커버리지 `{sg.get('evidence_coverage', '-')}%`",
            f"- **한국어 헤드라인**: {sg.get('korean_headline', '-')}",
            f"- **한국어 브리핑**: {sg.get('korean_briefing', '-')}",
            f"- **산식 사유**: {sg.get('alert_reason', '-')}",
            "- **제시된 근거 문장 (`evidence_phrases`)**:",
            *ev_lines,
            "",
            "| 검수 항목 | 선택지 (체크) | 비고 / 수정 의견 |",
            "| :--- | :--- | :--- |",
            "| 1) **경보 단계 적절성** | `[ ] accept`  `[ ] revise`  `[ ] reject` | |",
            "| 2) **근거 문장 지원** | `[ ] supported`  `[ ] partial`  `[ ] unsupported` | |",
            "| 3) **출처 품질** | `[ ] primary`  `[ ] reputable_secondary`  `[ ] unknown` | |",
            "| 4) **해석 수위(비약 여부)** | `[ ] supported`  `[ ] overstated`  `[ ] insufficient` | |",
            "| 5) **오류 유형** | `[ ] none` `[ ] evidence_gap` `[ ] overclaim` `[ ] false_alarm_candidate` | |",
            "| 6) **도메인 전문 검토 필요** | `[ ] yes` *(외교의도·현지선전·공급망)*  `[ ] no` | |",
            "",
        ])

    md.extend([
        "---",
        "",
        "## 4. Bluesky 외부 커뮤니티 피드백 연계 설계 (참고)",
        "",
        "- **게시 단위**: Stage 1 검수를 거친 권역별 요약 카드 + 출처 링크 + 핵심 질문 1줄",
        "- **수집·전처리**: 공개 API(`app.bsky.feed.getPostThread`)로 답글 수집 ➔ 봇·욕설·단순 감탄 필터링 ➔ 근거 링크 포함 반론/보강 의견만 추출",
        "- **반영 원칙 (`VALIDATION_PLAN.md` §10.2)**: Bluesky 댓글은 **도메인 전문가 검토의 대체물이 아니며**, 연구실/전문가 검수표와 분리된 `external_feedback` 보조 지표로만 기록합니다.",
        "",
        "---",
        "",
        "## [부록 · Stage 2] AI 독립 검증단 실측 감사 결과 (Stage 1 검수 완료 후 대조용)",
        "",
        f"- **감사 생성 시각**: `{audit_data.get('generated_at', '-')}`",
        "- **주의**: 아래 표는 사람 검수 Stage 1을 먼저 마친 뒤 대조용으로만 확인합니다.",
        "",
        "| 권역 | 산식 | `tev1` (단계) | `gemma2` (근거) | Critic (논리) | Judge (권고) | Trigger Flags |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ])

    for row in audit_results:
        tev1_v = (row.get("tev1") or {}).get("stage_verdict") or "-"
        gemma_v = (row.get("gemma2") or {}).get("worst_verdict") or "-"
        critic_v = (row.get("deepseek_r1") or {}).get("inference_verdict") or "None(오류)"
        judge_v = (row.get("presiding_judge") or {}).get("recommended_decision") or "-"
        triggers = ", ".join((row.get("governance") or {}).get("triggers", []))
        md.append(
            f"| `{row['region']}` | `{row.get('formula_alert_en', '-')}` | `{tev1_v}` | `{gemma_v}` | `{critic_v}` | `{judge_v}` | `{triggers}` |"
        )

    md.append("")
    return "\n".join(md)


def build_docx(md_text: str, out_path: Path) -> None:
    from docx import Document
    from docx.shared import Mm, Pt, RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Mm(210)
    sec.page_height = Mm(297)
    sec.top_margin = Mm(18)
    sec.bottom_margin = Mm(18)
    sec.left_margin = Mm(18)
    sec.right_margin = Mm(18)

    style = doc.styles["Normal"]
    style.font.name = "Malgun Gothic"
    style.font.size = Pt(9.5)
    style.font.color.rgb = RGBColor(0x22, 0x22, 0x22)

    def add_table(rows_data: List[List[str]]) -> None:
        if not rows_data:
            return
        tbl = doc.add_table(rows=len(rows_data), cols=len(rows_data[0]))
        tbl.style = "Table Grid"
        for r_idx, row in enumerate(rows_data):
            for c_idx, val in enumerate(row):
                cell = tbl.cell(r_idx, c_idx)
                cell.text = val.replace("`", "").replace("**", "")
                for p in cell.paragraphs:
                    for run in p.runs:
                        run.font.name = "Malgun Gothic"
                        run.font.size = Pt(8.5)
                        if r_idx == 0:
                            run.bold = True
                if r_idx == 0:
                    tcPr = cell._tc.get_or_add_tcPr()
                    shd = OxmlElement("w:shd")
                    shd.set(qn("w:fill"), "EEF2F7")
                    tcPr.append(shd)
        doc.add_paragraph()

    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line == "---":
            if line == "---":
                doc.add_paragraph("─" * 55)
            i += 1
            continue

        if line.startswith("|"):
            tbl_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                tbl_lines.append(lines[i].strip())
                i += 1
            parsed_rows = []
            for tl in tbl_lines:
                cells = [c.strip() for c in tl.strip("|").split("|")]
                if all(set(c) <= set("-: ") for c in cells):
                    continue
                parsed_rows.append(cells)
            add_table(parsed_rows)
            continue

        clean = line.replace("`", "").replace("**", "")
        if line.startswith("# "):
            p = doc.add_heading(clean[2:], level=1)
        elif line.startswith("## [부록"):
            doc.add_page_break()
            p = doc.add_heading(clean[3:], level=2)
        elif line.startswith("## "):
            p = doc.add_heading(clean[3:], level=2)
        elif line.startswith("### "):
            p = doc.add_heading(clean[4:], level=3)
        elif line.startswith("- "):
            p = doc.add_paragraph(clean[2:], style="List Bullet")
        elif line.startswith("> "):
            p = doc.add_paragraph(clean[2:])
            for r in p.runs:
                r.italic = True
        else:
            doc.add_paragraph(clean)
        i += 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))


def main() -> None:
    sg_data = _load_json(SIGNAL_GAP_PATH)
    audit_data = _load_json(AUDIT_PATH)
    md_text = build_markdown(sg_data, audit_data)

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(md_text, encoding="utf-8")
    print(f"✅ Markdown 보고서 생성 완료: {OUT_MD}")

    try:
        build_docx(md_text, OUT_DOCX)
        print(f"✅ A4 DOCX 보고서 생성 완료: {OUT_DOCX}")
    except Exception as exc:
        print(f"⚠️ DOCX 생성 건너뜀 ({exc})")


if __name__ == "__main__":
    main()
