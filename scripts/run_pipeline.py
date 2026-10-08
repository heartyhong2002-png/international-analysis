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

# Windows에서는 터미널의 기본 문자 인코딩이 UTF-8이 아닐 수 있습니다.
# 출력 인코딩을 UTF-8로 바꾸면 한글, 이모지, 외국어가 깨질 가능성이 줄어듭니다.
if sys.platform == "win32":
    try:
        # Windows 콘솔은 환경에 따라 기본 인코딩이 cp949일 수 있어,
        # 이모지·외국어·특수문자를 출력할 때 UnicodeEncodeError가 발생할 수 있습니다.
        # 표준 출력/에러를 UTF-8로 맞추고, 표현할 수 없는 문자는 대체 문자로 처리합니다.
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        # 일부 실행 환경에서는 스트림을 재설정할 수 없으므로,
        # 인코딩 설정 실패가 파이프라인 실행 자체를 막지 않게 무시합니다.
        pass

# 이 파일(run_pipeline.py)이 들어 있는 폴더의 절대 경로입니다.
# 현재 작업 폴더가 어디인지와 상관없이 다른 스크립트의 위치를 찾기 위해 사용합니다.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def run_step(step_num, total, title, script_name, extra_args=None):
    """파이프라인의 한 단계를 실행하고 성공 여부를 반환합니다."""

    # 실행할 스크립트의 전체 경로를 만듭니다.
    script_path = os.path.join(SCRIPT_DIR, script_name)

    # 현재 파이썬 인터프리터로 다음 스크립트를 실행할 명령어입니다.
    # 예: [python.exe, collection/issue_data_collector.py, --resume]
    cmd = [sys.executable, script_path] + (extra_args or [])

    print("\n" + "#" * 60)
    print(f"# [{step_num}/{total}] {title}")
    print(f"#   $ python {script_name} {' '.join(extra_args or [])}".rstrip())
    print("#" * 60)

    # subprocess.run()은 자식 프로세스가 끝날 때까지 기다립니다.
    # 따라서 앞 단계가 끝난 뒤에만 다음 단계가 실행됩니다.
    start = time.time()
    result = subprocess.run(cmd)
    elapsed = time.time() - start

    # returncode가 0이 아니면 보통 해당 스크립트에서 오류가 발생한 것입니다.
    if result.returncode != 0:
        print(f"\n✗ {script_name} 실패 (종료 코드 {result.returncode}, {elapsed:.0f}초 경과)")
        print(f"  위 로그에서 에러 원인을 확인하고, 그 부분만 고친 뒤 이 스크립트를 다시 돌리면 됩니다.")
        return False

    print(f"\n✓ {script_name} 완료 ({elapsed:.0f}초)")
    return True


def main():
    # 명령줄 옵션을 읽는 객체입니다.
    # 사용자가 --resume, --skip-gov 같은 옵션을 입력하면 args에 저장됩니다.
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
    parser.add_argument("--skip-trends", action="store_true",
                         help="구글 트렌드 위험 행동 지표(fetch_google_trends.py) 수집 생략")
    parser.add_argument("--skip-local-opinions", action="store_true",
                         help="대안 로컬 여론 5대 센서(fetch_local_opinions.py) 수집 생략")
    parser.add_argument("--skip-chokepoints", action="store_true",
                         help="해협·항만 및 해상 운임·에너지 센서(fetch_maritime_chokepoints.py) 수집 생략")
    parser.add_argument("--skip-cross-verification", action="store_true",
                         help="GDELT 사건 및 복수 계통 교차검증(cross_verify_events.py) 생략")
    args = parser.parse_args()

    # 실행할 작업들을 순서대로 저장할 리스트입니다.
    # 각 항목은 (화면에 표시할 이름, 실행할 파일, 추가 옵션) 형태입니다.
    steps = []
    if not args.only_db:
        # 옵션에 따라 일부 수집 작업을 steps에 넣거나 생략합니다.
        # 여기서는 파일을 바로 실행하지 않고, 실행 순서만 먼저 구성합니다.
        if not args.skip_us:
            steps.append(("미국 종합 시그널 수집 (정치·경제·금융·외교)", "collection/fetch_us_macro_signals.py", []))
        if args.with_kaggle:
            steps.append(("Kaggle 데이터셋 동기화 (Kayhan 등)", "collection/fetch_kaggle_datasets.py", []))
        collector_args = ["--resume"] if args.resume else []
        steps.append(("이슈 데이터 수집 (Wikipedia + FRED + 제재 + 무역)",
                       "collection/issue_data_collector.py", collector_args))
        if not args.skip_gov:
            steps.append(("정부 발표 수집 (RSS)", "collection/gov_announcements_collector.py", []))
        if not args.skip_experts:
            # PHASE2_THINKTANK_REDDIT_HANDOFF.md 작업 2: 싱크탱크(Chatham House/Crisis
            # Group/38 North)+현지언론(Moscow Times/Al-Monitor) 수집을 정식 파이프라인
            # 단계로 승격. --with-llm 없이 실행 -> 수집 + 규칙기반 태깅까지만(다른 수집
            # 단계와 동일하게, LLM 호출은 별도 검수 단계에서 수행하는 기존 관례를 따름).
            steps.append(("글로벌 싱크탱크·현지언론 전문가 분석 수집", "analysis/prototype_local_expert_sources.py", []))
        if not args.skip_polls:
            steps.append(("글로벌 실증 여론조사(Pew·ECFR·Ipsos) 수집", "collection/fetch_polling_data.py", []))
        if args.with_reddit:
            steps.append(("Reddit 공개 커뮤니티 여론 텍스트 마이닝", "collection/fetch_reddit_opinion.py", []))
        steps.append(("권위주의 3자 교차 수집(Triangulated OSINT)", "collection/fetch_signal_gap_rss.py", []))
        steps.append(("금융 대체 지표(Financial Proxy) 수집", "collection/fetch_financial_proxy.py", []))
        if not args.skip_trends:
            steps.append(("구글 트렌드 위험 행동 지표 수집", "collection/fetch_google_trends.py", []))
        if not args.skip_local_opinions:
            steps.append(("대안 로컬 여론 5대 센서 통합 수집", "collection/fetch_local_opinions.py", []))
        if not args.skip_chokepoints:
            steps.append(("해협·항만 및 해상 운임·에너지 센서 수집", "collection/fetch_maritime_chokepoints.py", []))
        if not args.skip_cross_verification:
            steps.append(("GDELT 사건 및 복수 계통 시계열 교차검증", "analysis/cross_verify_events.py", []))
    # 수집을 건너뛰는 --only-db를 사용하더라도,
    # 수집된 데이터를 DB에 넣고 결과물을 만드는 단계는 항상 실행합니다.
    steps.append(("MySQL DB로 통합", "db/build_database.py", []))
    steps.append(("해협 센서 및 교차검증 MySQL DB 동기화", "db/load_cross_verification_to_db.py", []))
    steps.append(("인터랙티브 HTML 대시보드 생성", "dashboard/generate_dashboard_v2.py", []))

    # 실제 실행 전에 전체 작업 목록을 사용자에게 보여줍니다.
    print("\n" + "=" * 60)
    print("🚀 국제정세 분석 파이프라인 시작")
    print(f"   총 {len(steps)}단계: " + " → ".join(s[1] for s in steps))
    print("=" * 60)

    pipeline_start = time.time()

    # steps에 저장한 작업을 앞에서부터 하나씩 실행합니다.
    # enumerate(..., start=1)은 첫 번째 작업 번호를 1부터 시작하게 합니다.
    for i, (title, script_name, extra_args) in enumerate(steps, start=1):
        ok = run_step(i, len(steps), title, script_name, extra_args)
        if not ok:
            # 한 단계라도 실패하면 뒤 단계는 실행하지 않고 즉시 종료합니다.
            print("\n" + "=" * 60)
            print(f"⚠ 파이프라인이 {i}단계({script_name})에서 멈췄습니다.")
            print("=" * 60)
            sys.exit(1)

    total_elapsed = time.time() - pipeline_start
    print("\n" + "=" * 60)
    print(f"✅ 파이프라인 전체 완료! (총 {total_elapsed/60:.1f}분)")
    print("=" * 60)


# 이 파일을 직접 실행했을 때만 main()을 호출합니다.
# 다른 파일에서 import할 때는 파이프라인이 자동으로 시작되지 않습니다.
if __name__ == "__main__":
    main()
