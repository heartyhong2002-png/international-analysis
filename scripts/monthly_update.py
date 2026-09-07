"""
Monthly International Affairs Analysis Update Pipeline
월간 국제정세 분석 업데이트 파이프라인

Orchestrates complete workflow:
1. Collect latest geopolitical data (GDELT, FRED, etc.)
2. Analyze issue intensity and trends
3. Generate/update interactive dashboard
4. Generate bilingual analysis reports
5. Archive previous month's data
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import shutil

# Windows 콘솔의 기본 인코딩(cp949)이 이모지/특수문자(•, ✅, 🌍 등)를 표현하지
# 못해 UnicodeEncodeError가 나는 것을 방지하기 위해 UTF-8로 강제 설정합니다.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from issue_data_collector import (
    fetch_gdelt_sentiment,
    fetch_fred_issue_indicators,
    fetch_sanctions_data,
    calculate_issue_intensity,
    ISSUE_KEYWORDS
)
from generate_dashboard import IssueDashboard
from generate_reports import IssueReportGenerator

# ============================================================================
# Configuration
# ============================================================================

LOG_DIR = Path("logs")
DATA_DIR = Path("data/issues")
ARCHIVE_DIR = Path("data/archive")
OUTPUT_DIR = Path("output")
REPORTS_DIR = OUTPUT_DIR / "reports"
DASHBOARD_DIR = OUTPUT_DIR / "dashboard"

# Ensure directories exist
for directory in [LOG_DIR, DATA_DIR, ARCHIVE_DIR, OUTPUT_DIR, REPORTS_DIR, DASHBOARD_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Setup logging
log_file = LOG_DIR / f"monthly_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# Phase 1: Data Collection
# ============================================================================

def phase_collect_data():
    """
    Collect latest geopolitical data from all sources
    """
    logger.info("\n" + "="*70)
    logger.info("PHASE 1: Data Collection")
    logger.info("="*70)

    collection_summary = {
        "timestamp": datetime.now().isoformat(),
        "sources": {},
        "issues_analyzed": 0,
        "errors": []
    }

    try:
        # 1. GDELT News Sentiment Data
        logger.info("\n[1/3] Collecting GDELT news sentiment data...")
        issue_summaries = []

        for issue_name, keywords in ISSUE_KEYWORDS.items():
            try:
                logger.info(f"  • Fetching data for: {issue_name}")
                df_gdelt = fetch_gdelt_sentiment(keywords, days_back=30)
                intensity = calculate_issue_intensity(df_gdelt)

                # Save raw data
                if not df_gdelt.empty:
                    csv_file = DATA_DIR / f"{issue_name}_gdelt_{datetime.now().strftime('%Y%m')}.csv"
                    df_gdelt.to_csv(csv_file, index=False)
                    logger.info(f"    ✓ Saved: {csv_file}")

                issue_summaries.append({
                    "issue": issue_name,
                    "intensity": intensity,
                    "article_count": df_gdelt['article_count'].sum() if not df_gdelt.empty else 0,
                    "status": "success"
                })
                collection_summary["issues_analyzed"] += 1

            except Exception as e:
                logger.error(f"    ✗ Error collecting data for {issue_name}: {str(e)}")
                issue_summaries.append({
                    "issue": issue_name,
                    "intensity": 0,
                    "article_count": 0,
                    "status": "error",
                    "error": str(e)
                })
                collection_summary["errors"].append({
                    "source": "GDELT",
                    "issue": issue_name,
                    "error": str(e)
                })

        collection_summary["sources"]["gdelt"] = {
            "status": "completed",
            "issues_processed": len(issue_summaries),
            "successful": sum(1 for x in issue_summaries if x["status"] == "success")
        }

        # 2. FRED Economic Indicators
        logger.info("\n[2/3] Collecting FRED economic indicators...")
        try:
            fred_data = fetch_fred_issue_indicators()
            logger.info(f"  ✓ Collected {len(fred_data)} economic indicators")
            collection_summary["sources"]["fred"] = {
                "status": "completed",
                "indicators": len(fred_data)
            }
        except Exception as e:
            logger.error(f"  ✗ Error collecting FRED data: {str(e)}")
            collection_summary["sources"]["fred"] = {
                "status": "error",
                "error": str(e)
            }
            collection_summary["errors"].append({
                "source": "FRED",
                "error": str(e)
            })

        # 3. Sanctions Data
        logger.info("\n[3/3] Collecting OpenSanctions data...")
        try:
            sanctions_data = fetch_sanctions_data()
            logger.info(f"  ✓ Collected sanctions data for {len(sanctions_data)} countries")
            collection_summary["sources"]["sanctions"] = {
                "status": "completed",
                "countries": len(sanctions_data)
            }
        except Exception as e:
            logger.error(f"  ✗ Error collecting sanctions data: {str(e)}")
            collection_summary["sources"]["sanctions"] = {
                "status": "error",
                "error": str(e)
            }
            collection_summary["errors"].append({
                "source": "OpenSanctions",
                "error": str(e)
            })

        # Save collection summary
        summary_file = DATA_DIR / f"collection_summary_{datetime.now().strftime('%Y%m%d')}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(collection_summary, f, indent=2, ensure_ascii=False)
        logger.info(f"\n✓ Collection summary saved: {summary_file}")

        return collection_summary, issue_summaries

    except Exception as e:
        logger.error(f"Fatal error in data collection phase: {str(e)}")
        raise

# ============================================================================
# Phase 2: Analysis
# ============================================================================

def phase_analyze_data(issue_summaries):
    """
    Analyze collected data and compute risk indicators
    """
    logger.info("\n" + "="*70)
    logger.info("PHASE 2: Data Analysis")
    logger.info("="*70)

    analysis_summary = {
        "timestamp": datetime.now().isoformat(),
        "total_issues": len(issue_summaries),
        "high_priority": [],
        "medium_priority": [],
        "low_priority": []
    }

    try:
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(issue_summaries)
        df = df.sort_values("intensity", ascending=False)

        # Categorize by intensity
        logger.info("\n📊 Issue Risk Assessment:")

        high = df[df['intensity'] > 60]
        medium = df[(df['intensity'] >= 30) & (df['intensity'] <= 60)]
        low = df[df['intensity'] < 30]

        logger.info(f"\n🔴 HIGH PRIORITY ({len(high)} issues, Intensity > 60):")
        for idx, row in high.iterrows():
            logger.info(f"   • {row['issue']}: {row['intensity']:.1f}/100")
            analysis_summary["high_priority"].append({
                "issue": row['issue'],
                "intensity": float(row['intensity']),
                "articles": int(row['article_count'])
            })

        logger.info(f"\n🟡 MEDIUM PRIORITY ({len(medium)} issues, 30-60):")
        for idx, row in medium.iterrows():
            logger.info(f"   • {row['issue']}: {row['intensity']:.1f}/100")
            analysis_summary["medium_priority"].append({
                "issue": row['issue'],
                "intensity": float(row['intensity']),
                "articles": int(row['article_count'])
            })

        logger.info(f"\n🟢 LOW PRIORITY ({len(low)} issues, < 30):")
        for idx, row in low.iterrows():
            logger.info(f"   • {row['issue']}: {row['intensity']:.1f}/100")
            analysis_summary["low_priority"].append({
                "issue": row['issue'],
                "intensity": float(row['intensity']),
                "articles": int(row['article_count'])
            })

        # Calculate global tension index (average intensity)
        global_tension = df['intensity'].mean()
        analysis_summary["global_tension_index"] = float(global_tension)

        logger.info(f"\n🌍 Global Tension Index: {global_tension:.1f}/100")

        if global_tension > 60:
            logger.info("   Status: 🔴 CRITICAL")
        elif global_tension > 45:
            logger.info("   Status: 🟠 HIGH")
        elif global_tension > 30:
            logger.info("   Status: 🟡 MODERATE")
        else:
            logger.info("   Status: 🟢 STABLE")

        # Save analysis summary
        analysis_file = DATA_DIR / f"analysis_summary_{datetime.now().strftime('%Y%m%d')}.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_summary, f, indent=2, ensure_ascii=False)
        logger.info(f"\n✓ Analysis summary saved: {analysis_file}")

        return analysis_summary

    except Exception as e:
        logger.error(f"Fatal error in analysis phase: {str(e)}")
        raise

# ============================================================================
# Phase 3: Dashboard Generation
# ============================================================================

def phase_generate_dashboard(analysis_summary):
    """
    Generate/update interactive HTML dashboard
    """
    logger.info("\n" + "="*70)
    logger.info("PHASE 3: Dashboard Generation")
    logger.info("="*70)

    try:
        logger.info("\nGenerating interactive dashboard...")
        dashboard = IssueDashboard()
        output_file = dashboard.save_dashboard()

        logger.info(f"✓ Dashboard generated: {output_file}")
        logger.info(f"  • Location: {output_file.absolute()}")
        logger.info(f"  • Size: {output_file.stat().st_size:,} bytes")

        return {
            "status": "success",
            "output_file": str(output_file),
            "file_size": output_file.stat().st_size
        }

    except Exception as e:
        logger.error(f"Fatal error in dashboard generation: {str(e)}")
        raise

# ============================================================================
# Phase 4: Report Generation
# ============================================================================

def phase_generate_reports(analysis_summary):
    """
    Generate bilingual analysis reports for each issue
    """
    logger.info("\n" + "="*70)
    logger.info("PHASE 4: Report Generation")
    logger.info("="*70)

    try:
        logger.info("\nGenerating bilingual issue reports...")
        report_gen = IssueReportGenerator()

        # Generate reports for high and medium priority issues
        high_priority_issues = [x['issue'] for x in analysis_summary['high_priority']]
        medium_priority_issues = [x['issue'] for x in analysis_summary['medium_priority']]
        priority_issues = high_priority_issues + medium_priority_issues[:3]  # Top issues

        generated_files = report_gen.generate_reports()

        logger.info(f"\n✓ Generated {len(generated_files)} bilingual reports")
        for file_path in generated_files:
            if Path(file_path).exists():
                size = Path(file_path).stat().st_size
                logger.info(f"  • {Path(file_path).name} ({size:,} bytes)")

        # 마크다운 리포트를 PDF로도 변환
        # PDF 변환은 부가 기능이므로, 관련 라이브러리 문제로 파이프라인 전체가
        # 죽지 않도록 import 자체를 이 블록 안에서 처리합니다.
        logger.info("\n마크다운 리포트를 PDF로 변환 중...")
        try:
            from convert_to_pdf import main as convert_reports_to_pdf

            pdf_files = convert_reports_to_pdf()
            logger.info(f"✓ {len(pdf_files)}개 PDF 생성 완료")
        except Exception as pdf_err:
            logger.warning(f"⚠ PDF 변환 실패 (리포트 자체는 정상 생성됨): {pdf_err}")
            pdf_files = []

        return {
            "status": "success",
            "reports_generated": len(generated_files),
            "report_files": generated_files,
            "pdf_files": pdf_files
        }

    except Exception as e:
        logger.error(f"Fatal error in report generation: {str(e)}")
        raise

# ============================================================================
# Phase 5: Archive & Cleanup
# ============================================================================

def phase_archive_previous():
    """
    Archive previous month's data for historical tracking
    """
    logger.info("\n" + "="*70)
    logger.info("PHASE 5: Data Archival")
    logger.info("="*70)

    try:
        # Get previous month
        today = datetime.now()
        previous_month = today - timedelta(days=today.day)
        archive_date = previous_month.strftime('%Y%m')

        archive_month_dir = ARCHIVE_DIR / archive_date
        archive_month_dir.mkdir(parents=True, exist_ok=True)

        # Archive CSV files from previous month
        csv_files = list(DATA_DIR.glob(f"*_{archive_date}.csv"))
        if csv_files:
            for csv_file in csv_files:
                shutil.copy2(csv_file, archive_month_dir / csv_file.name)
                logger.info(f"  ✓ Archived: {csv_file.name}")

        # Archive summary files
        summary_files = list(DATA_DIR.glob(f"*_summary_{archive_date[:6]}*.json"))
        for summary_file in summary_files:
            shutil.copy2(summary_file, archive_month_dir / summary_file.name)
            logger.info(f"  ✓ Archived: {summary_file.name}")

        logger.info(f"\n✓ Archived data location: {archive_month_dir}")

        return {
            "status": "success",
            "archive_location": str(archive_month_dir),
            "files_archived": len(csv_files) + len(summary_files)
        }

    except Exception as e:
        logger.warning(f"Warning in archival phase: {str(e)}")
        return {
            "status": "warning",
            "error": str(e)
        }

# ============================================================================
# Main Pipeline Execution
# ============================================================================

def main():
    """
    Execute complete monthly update pipeline
    """

    print("\n" + "="*70)
    print("🌍 International Affairs Analysis - Monthly Update Pipeline")
    print("="*70)
    print(f"Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    logger.info("\n" + "="*70)
    logger.info("🌍 Monthly Update Pipeline Started")
    logger.info("="*70)

    pipeline_results = {
        "start_time": datetime.now().isoformat(),
        "phases": {}
    }

    try:
        # Phase 1: Data Collection
        collection_summary, issue_summaries = phase_collect_data()
        pipeline_results["phases"]["collection"] = collection_summary

        # Phase 2: Analysis
        analysis_summary = phase_analyze_data(issue_summaries)
        pipeline_results["phases"]["analysis"] = analysis_summary

        # Phase 3: Dashboard Generation
        dashboard_result = phase_generate_dashboard(analysis_summary)
        pipeline_results["phases"]["dashboard"] = dashboard_result

        # Phase 4: Report Generation
        reports_result = phase_generate_reports(analysis_summary)
        pipeline_results["phases"]["reports"] = reports_result

        # Phase 5: Archive
        archive_result = phase_archive_previous()
        pipeline_results["phases"]["archive"] = archive_result

        # Save pipeline execution log
        pipeline_results["end_time"] = datetime.now().isoformat()
        pipeline_results["status"] = "completed"

        pipeline_log = OUTPUT_DIR / f"pipeline_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(pipeline_log, 'w', encoding='utf-8') as f:
            json.dump(pipeline_results, f, indent=2, ensure_ascii=False)

        # Summary output
        logger.info("\n" + "="*70)
        logger.info("✅ PIPELINE EXECUTION COMPLETE")
        logger.info("="*70)
        logger.info(f"\n📊 Summary:")
        logger.info(f"  • Data Collection: {collection_summary['sources'].get('gdelt', {}).get('status', 'N/A')}")
        logger.info(f"  • Issues Analyzed: {analysis_summary['total_issues']}")
        logger.info(f"  • Global Tension Index: {analysis_summary['global_tension_index']:.1f}/100")
        logger.info(f"  • Dashboard: ✓ Generated")
        logger.info(f"  • Reports: ✓ {reports_result['reports_generated']} files")
        logger.info(f"\n📁 Output Locations:")
        logger.info(f"  • Dashboard: {DASHBOARD_DIR / 'index.html'}")
        logger.info(f"  • Reports: {REPORTS_DIR}")
        logger.info(f"  • Logs: {LOG_DIR}")
        logger.info(f"\n📝 Execution Log: {pipeline_log}")
        logger.info("="*70 + "\n")

        return pipeline_results

    except Exception as e:
        logger.error(f"\n❌ PIPELINE EXECUTION FAILED")
        logger.error(f"Error: {str(e)}", exc_info=True)

        pipeline_results["end_time"] = datetime.now().isoformat()
        pipeline_results["status"] = "failed"
        pipeline_results["error"] = str(e)

        pipeline_log = OUTPUT_DIR / f"pipeline_log_failed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(pipeline_log, 'w', encoding='utf-8') as f:
            json.dump(pipeline_results, f, indent=2, ensure_ascii=False)

        return pipeline_results


if __name__ == "__main__":
    results = main()
    sys.exit(0 if results.get("status") == "completed" else 1)
