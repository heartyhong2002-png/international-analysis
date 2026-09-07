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
from issue_research_data import REAL_ISSUE_DATA  # noqa: E402


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

        # Korean report template
        self.ko_template = """# {ko_name} 심층 분석 보고서

**작성일**: {date}
**분석 기간**: 2025년 1월 ~ {now_date}
**발행**: 국제정세 분석 시스템

---

## 📋 Executive Summary (요약)

### 현재 상황
{ko_situation}

### 위험도 평가
**위험도**: {severity_ko} ({intensity}/100)

**현황**:
- 핵심 지표: {main_indicator_ko}
- 국제 반응: {international_response_ko}
- 한반도 영향: {korea_impact_ko}

---

## 📖 배경 & 타임라인

### 이슈 개요
{issue_overview_ko}

### 주요 전환점
| 시기 | 사건 |
|------|------|
| 2025년 1월 | 트럼프 재임 시작 |
| 2025년 3월경 | {event_1_ko} |
| 2025년 6월경 | {event_2_ko} |
| 2026년 9월 (현재) | {current_status_ko} |

### 트럼프 정권의 영향
{trump_impact_ko}

---

## 📊 경제·안보 영향 분석

### 무역·환율·투자
- **무역**: {trade_impact_ko}
- **환율**: {fx_impact_ko}
- **투자**: {investment_impact_ko}

### 여론 & 전문가 평가
- **국제/국내 여론**: {public_opinion_ko}
- **전문가 평가**: {expert_assessment_ko}

---

## 🔍 현재 상황 평가

### 객관적 분석
{objective_analysis_ko}

### 주요 이해관계자들의 입장

**미국**: {us_position_ko}

**중국**: {china_position_ko}

**한국**: {korea_position_ko}

**기타 국가**: {others_position_ko}

### 주요 불확실성 요소
1. {uncertainty_1_ko}
2. {uncertainty_2_ko}
3. {uncertainty_3_ko}

---

## 🔮 향후 전망

### 단기 (3~6개월)
{short_term_outlook_ko}

**가능성 높은 시나리오**: {likely_scenario_short_ko}

### 중기 (1~3년)
{medium_term_outlook_ko}

**전환점 예상**: {transition_point_ko}

### 장기
{long_term_outlook_ko}

**구조적 변화**: {structural_change_ko}

---

## 🇰🇷 한국에의 영향

### 안보적 영향
- **북한 관련 함의**: {north_korea_impact_ko}
- **한미동맹 영향**: {alliance_impact_ko}
- **미사일/군사 위협**: {missile_threat_ko}

### 외교적 영향
- **한미관계**: {korea_us_impact_ko}
- **국제적 입장**: {international_position_ko}
- **대응 전략**: {response_strategy_ko}

---

## 📎 참고 자료

### 주요 뉴스 원본
- [관련 보도 1]({news_link_1})
- [관련 보도 2]({news_link_2})
- [관련 보도 3]({news_link_3})

### 조사 방법
본 리포트의 내용은 WebSearch/WebFetch를 통한 실제 언론·싱크탱크·정부 발표 자료
조사를 바탕으로 작성되었으며, 확인되지 않은 수치는 추정치로 표시하거나
정성적 서술로 대체했습니다. GDELT/FRED/IMF DOTS 등 정량 데이터 자동 수집
파이프라인(issue_data_collector.py)은 별도로 운영되며, 향후 버전에서
본 리포트와 통합될 예정입니다.

---

**문서 정보**:
- 언어: 한국어 (Korean)
- 버전: v2.0 (실데이터 기반)
- 마지막 업데이트: {date}
- 다음 업데이트 예정: {next_update_date}

---
"""

        # English report template
        self.en_template = """# {en_name}: In-Depth Analysis Report

**Date**: {date}
**Analysis Period**: January 2025 ~ {now_date}
**Published by**: International Affairs Analysis System

---

## 📋 Executive Summary

### Current Situation
{en_situation}

### Risk Assessment
**Risk Level**: {severity_en} ({intensity}/100)

**Key Points**:
- Main Indicator: {main_indicator_en}
- International Response: {international_response_en}
- Korea Impact: {korea_impact_en}

---

## 📖 Background & Timeline

### Issue Overview
{issue_overview_en}

### Major Turning Points
| Date | Event |
|------|-------|
| January 2025 | Trump's Second Term Begins |
| ~March 2025 | {event_1_en} |
| ~June 2025 | {event_2_en} |
| September 2026 (Current) | {current_status_en} |

### Trump Administration's Impact
{trump_impact_en}

---

## 📊 Economic & Security Impact Analysis

### Trade, Exchange Rate & Investment
- **Trade**: {trade_impact_en}
- **Exchange Rate**: {fx_impact_en}
- **Investment**: {investment_impact_en}

### Public Opinion & Expert Assessment
- **Public Opinion**: {public_opinion_en}
- **Expert Assessment**: {expert_assessment_en}

---

## 🔍 Current Situation Assessment

### Objective Analysis
{objective_analysis_en}

### Major Stakeholders' Positions

**United States**: {us_position_en}

**China**: {china_position_en}

**South Korea**: {korea_position_en}

**Other Countries**: {others_position_en}

### Key Uncertainties
1. {uncertainty_1_en}
2. {uncertainty_2_en}
3. {uncertainty_3_en}

---

## 🔮 Future Outlook

### Short Term (3-6 months)
{short_term_outlook_en}

**Most Likely Scenario**: {likely_scenario_short_en}

### Medium Term (1-3 years)
{medium_term_outlook_en}

**Expected Turning Point**: {transition_point_en}

### Long Term
{long_term_outlook_en}

**Structural Changes**: {structural_change_en}

---

## 🌏 Impact on Korea

### Security Impact
- **North Korea-Related Implications**: {north_korea_impact_en}
- **Alliance Impact**: {alliance_impact_en}
- **Missile/Military Threats**: {missile_threat_en}

### Diplomatic Impact
- **Korea-US Relations**: {korea_us_impact_en}
- **International Position**: {international_position_en}
- **Response Strategy**: {response_strategy_en}

---

## 📎 Reference Data

### Key News Sources
- [News Article 1]({news_link_1})
- [News Article 2]({news_link_2})
- [News Article 3]({news_link_3})

### Methodology
This report's content is based on actual research conducted via WebSearch/WebFetch
across news media, think tanks, and government releases. Unverified figures are
either labeled as estimates or replaced with qualitative description. A separate
quantitative data pipeline (issue_data_collector.py, covering GDELT/FRED/IMF DOTS)
is maintained independently and is planned for integration in a future version.

---

**Document Information**:
- Language: English
- Version: v2.0 (real-data based)
- Last Updated: {date}
- Next Update: {next_update_date}

---
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
        ko_toc_lines = [
            "# 국제정세 종합 분석 보고서",
            "",
            f"**생성일**: {today_str}",
            f"**대상 이슈**: {len(self.issues)}개",
            "",
            "---",
            "",
            "## 목차",
            "",
        ]
        for i, issue in enumerate(self.issues.values(), 1):
            ko_toc_lines.append(f"{i}. {issue['ko_name']}")

        ko_sections = ["\n".join(ko_toc_lines)]
        for issue_key in self.issues.keys():
            data = self.build_report_data(issue_key)
            ko_report = self.ko_template.format(**data)
            ko_sections.append(page_break + ko_report)
            print(f"  [KO] {data['ko_name']} (intensity {data['intensity']}/100)")

        ko_combined = "\n".join(ko_sections)
        ko_output_file = self.output_dir / "Issues_Report_KO.md"
        with open(ko_output_file, 'w', encoding='utf-8') as f:
            f.write(ko_combined)

        # ---------- English report ----------
        en_toc_lines = [
            "# Global Geopolitical Issues - Comprehensive Report",
            "",
            f"**Generated**: {today_str}",
            f"**Issues Covered**: {len(self.issues)}",
            "",
            "---",
            "",
            "## Table of Contents",
            "",
        ]
        for i, issue in enumerate(self.issues.values(), 1):
            en_toc_lines.append(f"{i}. {issue['en_name']}")

        en_sections = ["\n".join(en_toc_lines)]
        for issue_key in self.issues.keys():
            data = self.build_report_data(issue_key)
            en_report = self.en_template.format(**data)
            en_sections.append(page_break + en_report)
            print(f"  [EN] {data['en_name']} (intensity {data['intensity']}/100)")

        en_combined = "\n".join(en_sections)
        en_output_file = self.output_dir / "Issues_Report_EN.md"
        with open(en_output_file, 'w', encoding='utf-8') as f:
            f.write(en_combined)

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
