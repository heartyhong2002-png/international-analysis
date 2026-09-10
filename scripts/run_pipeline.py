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
    args = parser.parse_args()

    steps = []
    if not args.only_db:
        collector_args = ["--resume"] if args.resume else []
        steps.append(("이슈 데이터 수집 (Wikipedia + FRED + 제재 + 무역)",
                       "issue_data_collector.py", collector_args))
        if not args.skip_gov:
            steps.append(("정부 발표 수집 (RSS)", "gov_announcements_collector.py", []))
    steps.append(("MySQL DB로 통합", "build_database.py", []))

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
