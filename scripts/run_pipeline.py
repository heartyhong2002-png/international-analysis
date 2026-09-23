"""
run_pipeline.py — 전체 파이프라인을 한 번에 실행
====================================================

매번 issue_data_collector.py → gov_announcements_collector.py →
build_database.py를 손으로 하나씩 실행하는 게 귀찮아서 만든 오케스트레이터.
이거 하나만 실행하면 셋 다 순서대로(각각 별도 프로세스로) 돌아갑니다.

사용법:
    python scripts/run_pipeline.py
    python scripts/run_pipeline.py --resume        # Wikipedia 수집만 --resume 모드로
    python scripts/run_pipeline.py --skip-gov       # 정부 발표 재수집 생략 (기존 데이터 그대로 사용)
    python scripts/run_pipeline.py --skip-polls     # 글로벌 여론조사(Pew/ECFR/Ipsos) 재수집 생략
    python scripts/run_pipeline.py --with-reddit    # Reddit 공개 RSS 커뮤니티 여론 수집 포함
    python scripts/run_pipeline.py --only-db        # 수집은 건너뛰고 build_database.py만 실행

왜 3개를 import해서 함수 호출로 합치지 않고 subprocess로 따로 실행하냐면:
  - 각 스크립트가 자기 파일 위치 기준으로 DATA_DIR을 잡기 때문에 문제는 없지만,
    각자 전역 상태(_wiki_failed_keywords 같은 모듈 레벨 리스트)나 argparse를
    따로 갖고 있어서, 한 프로세스에 다 import해서 합치면 상태가 꼬일 수 있음.
  - 하나가 중간에 죽어도(API 에러, 네트워크 문제 등) 나머지에 영향 안 주고
    "어디까지 됐고 어디서 멈췄는지"가 명확하게 남음.
"""

import argparse
import os
import subprocess
import sys
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def run_step(step_num, total, title, script_name, extra_args=None):
    script_path = os.path.join(SCRIPT_DIR, script_name)
    cmd = [sys.executable, script_path] + (extra_args or [])

    print("\n" + "#" * 60)
    print(f"# [{step_num}/{total}] {title}")
    print(f"#   $ python {script_name} {' '.join(extra_args or [])}".rstrip())
    print("#" * 60)

    start = time.time()
    result = subprocess.run(cmd)
    elapsed = time.time() - start

    if result.returncode != 0:
        print(f"\n✗ {script_name} 실패 (종료 코드 {result.returncode}, {elapsed:.0f}초 경과)")
        print(f"  위 로그에서 에러 원인을 확인하고, 그 부분만 고친 뒤 이 스크립트를 다시 돌리면 됩니다.")
        return False

    print(f"\n✓ {script_name} 완료 ({elapsed:.0f}초)")
    return True


def main():
    parser = argparse.ArgumentParser(description="전체 데이터 수집 + DB 적재 파이프라인을 한 번에 실행")
    parser.add_argument("--resume", action="store_true",
                         help="issue_data_collector.py를 --resume 모드로 실행 (이미 있는 이슈는 건너뜀)")
    parser.add_argument("--skip-gov", action="store_true",
                         help="gov_announcements_collector.py 재실행 생략 (기존에 수집된 정부 발표 데이터를 그대로 씀)")
    parser.add_argument("--only-db", action="store_true",
                         help="수집 단계(1, 2번)는 건너뛰고 build_database.py만 실행")
    parser.add_argument("--with-kaggle", action="store_true",
                         help="Kaggle 공개 데이터셋(Kayhan 아카이브 등) 자동 다운로드/동기화 실행")
    parser.add_argument("--skip-us", action="store_true",
                         help="미국 거시/정치/외교 데이터 수집 생략")
    parser.add_argument("--skip-experts", action="store_true",
                         help="글로벌 싱크탱크/현지언론 전문가 분석 수집(prototype_local_expert_sources.py) 생략")
    parser.add_argument("--skip-polls", action="store_true",
                         help="글로벌 실증 여론조사 수집(fetch_polling_data.py) 생략 (기존 Pew/ECFR/Ipsos 데이터 사용)")
    parser.add_argument("--with-reddit", action="store_true",
                         help="Reddit 공개 커뮤니티 여론 텍스트 마이닝(fetch_reddit_opinion.py) 동시 실행")
    args = parser.parse_args()

    steps = []
    if not args.only_db:
        if not args.skip_us:
            steps.append(("미국 종합 시그널 수집 (정치·경제·금융·외교)", "fetch_us_macro_signals.py", []))
        if args.with_kaggle:
            steps.append(("Kaggle 데이터셋 동기화 (Kayhan 등)", "fetch_kaggle_datasets.py", []))
        collector_args = ["--resume"] if args.resume else []
        steps.append(("이슈 데이터 수집 (Wikipedia + FRED + 제재 + 무역)",
                       "issue_data_collector.py", collector_args))
        if not args.skip_gov:
            steps.append(("정부 발표 수집 (RSS)", "gov_announcements_collector.py", []))
        if not args.skip_experts:
            # PHASE2_THINKTANK_REDDIT_HANDOFF.md 작업 2: 싱크탱크(Chatham House/Crisis
            # Group/38 North)+현지언론(Moscow Times/Al-Monitor) 수집을 정식 파이프라인
            # 단계로 승격. --with-llm 없이 실행 -> 수집 + 규칙기반 태깅까지만(다른 수집
            # 단계와 동일하게, LLM 호출은 별도 검수 단계에서 수행하는 기존 관례를 따름).
            steps.append(("글로벌 싱크탱크·현지언론 전문가 분석 수집", "prototype_local_expert_sources.py", []))
        if not args.skip_polls:
            steps.append(("글로벌 실증 여론조사(Pew·ECFR·Ipsos) 수집", "fetch_polling_data.py", []))
        if args.with_reddit:
            steps.append(("Reddit 공개 커뮤니티 여론 텍스트 마이닝", "fetch_reddit_opinion.py", []))
        steps.append(("권위주의 3자 교차 수집(Triangulated OSINT)", "fetch_signal_gap_rss.py", []))
        steps.append(("금융 대체 지표(Financial Proxy) 수집", "fetch_financial_proxy.py", []))
    steps.append(("MySQL DB로 통합", "build_database.py", []))
    steps.append(("인터랙티브 HTML 대시보드 생성", "generate_dashboard_v2.py", []))

    print("\n" + "=" * 60)
    print("🚀 국제정세 분석 파이프라인 시작")
    print(f"   총 {len(steps)}단계: " + " → ".join(s[1] for s in steps))
    print("=" * 60)

    pipeline_start = time.time()
    for i, (title, script_name, extra_args) in enumerate(steps, start=1):
        ok = run_step(i, len(steps), title, script_name, extra_args)
        if not ok:
            print("\n" + "=" * 60)
            print(f"⚠ 파이프라인이 {i}단계({script_name})에서 멈췄습니다.")
            print("=" * 60)
            sys.exit(1)

    total_elapsed = time.time() - pipeline_start
    print("\n" + "=" * 60)
    print(f"✅ 파이프라인 전체 완료! (총 {total_elapsed/60:.1f}분)")
    print("=" * 60)


if __name__ == "__main__":
    main()
