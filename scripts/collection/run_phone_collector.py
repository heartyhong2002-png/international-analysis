"""
run_phone_collector.py — 갤럭시 S20 울트라(Termux) 엣지 수집 노드 전용 무중단 자동 수집 러너
========================================================================================

특징:
1. 무거운 C 컴파일(numpy, pandas, lxml) 없는 순수 경량 수집기 5종 오케스트레이션.
2. 특정 수집기 네트워크 지연/오류 발생 시 프로세스 중단 없이 안전 격리(Fault-Tolerant).
3. 24시간 백그라운드 주기 실행 (기본 1시간, --interval-hours 또는 --interval-minutes 지원).
4. 수집 영수증 및 통합 상태 파일(data/phone_collector_status.json) 갱신.
5. 수집 후 Git 원격 자동 푸시 옵션(--sync-git) 지원으로 메인 PC/Airflow와 2-Tier 분산 동기화.
6. 1회 즉시 실행 모드(--once) 지원.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# 콘솔 인코딩 안전화 (Windows / Linux 공통)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data"
STATUS_FILE = DATA_DIR / "phone_collector_status.json"

# 스마트폰 엣지 노드에서 안전하게 가동되는 경량 수집기 8종
# Timeouts must exceed per-request budgets inside collectors (often 10–20s × N).
EDGE_COLLECTORS = [
    {
        "id": "maritime_chokepoints",
        "name": "해협·항만 병목 및 운임·에너지 센서",
        "script": "scripts/collection/fetch_maritime_chokepoints.py",
        "timeout": 180,
    },
    {
        "id": "whitehouse_official",
        "name": "백악관 공식 성명 및 브리핑 RSS",
        "script": "scripts/collection/fetch_whitehouse_official.py",
        "timeout": 120,
    },
    {
        "id": "federal_register",
        "name": "연방관보(Federal Register) 정책·통상·수출통제 고시",
        "script": "scripts/collection/fetch_federal_register.py",
        "timeout": 120,
    },
    {
        "id": "gov_announcements",
        "name": "주요국 공식 정부 발표문 (MOFA/State/FCDO 등)",
        "script": "scripts/collection/gov_announcements_collector.py",
        "timeout": 300,
    },
    {
        "id": "signal_gap_rss",
        "name": "4대 권역 신호 괴리 RSS (공식 vs 독립 언론)",
        "script": "scripts/collection/fetch_signal_gap_rss.py",
        "timeout": 300,
    },
    {
        "id": "bluesky_public",
        "name": "블루스카이(Bluesky AT Protocol) 8대 지정학·공급망 신호",
        "script": "scripts/collection/fetch_bluesky_public.py",
        "timeout": 180,
    },
    {
        "id": "telegram_osint",
        "name": "텔레그램 공개 채널 5대 군사·분쟁 OSINT",
        "script": "scripts/collection/fetch_telegram_public.py",
        "timeout": 180,
    },
    {
        "id": "local_opinions",
        "name": "로컬 포럼 및 대안 여론 센서 (PTT/핀충/로컬뉴스)",
        "script": "scripts/collection/fetch_local_opinions.py",
        "timeout": 180,
    },
]


def print_banner(round_num: int, start_time: str) -> None:
    print("\n" + "=" * 65)
    print(f"[Galaxy S20 Ultra Edge Node] 제 {round_num}회차 자동 수집 시작")
    print(f"시작 시각(UTC): {start_time}")
    print("=" * 65)


def run_single_collector(collector: dict) -> dict:
    """단일 수집기를 subprocess로 격리 실행하여 메인 루프를 안전하게 보호한다."""
    script_path = ROOT / collector["script"]
    if not script_path.exists():
        return {
            "id": collector["id"],
            "name": collector["name"],
            "status": "NOT_FOUND",
            "duration_sec": 0,
            "error": f"파일 없음: {collector['script']}",
        }

    print(f"\n▶ [{collector['name']}] 수집 실행 중...")
    start_t = time.time()

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=collector["timeout"],
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        duration = round(time.time() - start_t, 2)

        if proc.returncode == 0:
            print(f"  ✓ 완료 ({duration}초 소요)")
            lines = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
            for line in lines[-3:]:
                print(f"    {line}")
            return {
                "id": collector["id"],
                "name": collector["name"],
                "status": "SUCCESS",
                "duration_sec": duration,
                "error": None,
            }
        else:
            print(f"  ⚠️ 실패 (코드 {proc.returncode}, {duration}초)")
            err_sample = proc.stderr.strip()[:200] if proc.stderr else proc.stdout.strip()[:200]
            print(f"    에러 요약: {err_sample}")
            return {
                "id": collector["id"],
                "name": collector["name"],
                "status": "FAILED",
                "duration_sec": duration,
                "error": err_sample,
            }

    except subprocess.TimeoutExpired:
        duration = round(time.time() - start_t, 2)
        print(f"  ❌ 타임아웃 ({collector['timeout']}초 초과)")
        return {
            "id": collector["id"],
            "name": collector["name"],
            "status": "TIMEOUT",
            "duration_sec": duration,
            "error": f"Execution exceeded {collector['timeout']}s",
        }
    except Exception as e:
        duration = round(time.time() - start_t, 2)
        print(f"  ❌ 실행 중 예외: {e}")
        return {
            "id": collector["id"],
            "name": collector["name"],
            "status": "ERROR",
            "duration_sec": duration,
            "error": str(e)[:200],
        }


def _git(args: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    """git 명령을 캡처 실행한다. check=False — 호출측에서 코드/로그 판정."""
    return subprocess.run(
        ["git", *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )


def _git_err(proc: subprocess.CompletedProcess) -> str:
    return (proc.stderr or proc.stdout or "").strip()[:400]


def sync_to_git(branch: str | None = None) -> bool:
    """수집된 data/ 최신 결과를 Git 원격으로 커밋·푸시한다 (Edge-to-Core).

    Termux에서 흔한 실패:
    - user.name/email 미설정 → 커밋 거부
    - pull --rebase 충돌
    - HTTPS/SSH 인증 실패
    전역 git config는 수정하지 않고, 커밋 시에만 -c 로 작성자를 넘긴다.
    """
    print("\n[Git Data Sync] 최신 수집 데이터 원격 동기화 시도 중...")
    try:
        st_proc = _git(["status", "--porcelain", "--", "data/"], timeout=30)
        if st_proc.returncode != 0:
            print(f"  ⚠️ git status 실패: {_git_err(st_proc)}")
            return False
        if not st_proc.stdout.strip():
            print("  ℹ️ data/ 에 새로 변경된 파일이 없어 Git 푸시를 생략합니다.")
            return True

        add_proc = _git(["add", "--", "data/"], timeout=30)
        if add_proc.returncode != 0:
            print(f"  ⚠️ git add data/ 실패: {_git_err(add_proc)}")
            return False

        # 전역 config 없이 1회성 작성자 (EDGE_GIT_* 로 덮어쓰기 가능)
        edge_name = os.getenv("EDGE_GIT_NAME", "S20 Ultra Edge")
        edge_email = os.getenv("EDGE_GIT_EMAIL", "edge-collector@users.noreply.github.com")
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        commit_msg = f"data(edge): latest signals from S20 Ultra [{now_utc}]"
        commit_proc = _git(
            [
                "-c",
                f"user.name={edge_name}",
                "-c",
                f"user.email={edge_email}",
                "commit",
                "-m",
                commit_msg,
            ],
            timeout=45,
        )
        if commit_proc.returncode != 0:
            err = _git_err(commit_proc)
            print(f"  ⚠️ git commit 실패: {err}")
            if "author identity unknown" in err.lower() or "user.email" in err.lower():
                print("  💡 힌트: Termux에서 작성자 미설정입니다. 이 스크립트는 -c 로 우회합니다.")
                print("     그래도 실패하면 EDGE_GIT_NAME / EDGE_GIT_EMAIL 환경변수를 설정하세요.")
            return False
        print(f"  ✓ 로컬 커밋 완료: {commit_msg}")

        if not branch:
            br_proc = _git(["rev-parse", "--abbrev-ref", "HEAD"], timeout=15)
            branch = (br_proc.stdout or "").strip() or "cursor/actions-light-collection"
        if branch == "HEAD":
            print("  ⚠️ detached HEAD 상태입니다. --branch cursor/actions-light-collection 을 지정하세요.")
            return False

        # data/ 파일은 방금 수집한 최신 스냅샷이므로 rebase 시 -X theirs(리베이스에서 재적용되는 현재 커밋 우선)로 자동 해결
        rebase_proc = _git(["pull", "--rebase", "-X", "theirs", "origin", branch], timeout=90)
        if rebase_proc.returncode != 0:
            err = _git_err(rebase_proc)
            print(f"  ⚠️ git pull --rebase 실패 — 푸시 중단: {err}")
            # 중단된 rebase가 남아 있으면 다음 주기 보호를 위해 abort 시도
            if Path(ROOT / ".git" / "rebase-merge").exists() or Path(ROOT / ".git" / "rebase-apply").exists():
                abort_proc = _git(["rebase", "--abort"], timeout=30)
                print(
                    "  ↩️ rebase --abort 실행: "
                    + ("OK" if abort_proc.returncode == 0 else _git_err(abort_proc))
                )
            print("  💡 폰에서: git status 확인 후 git pull --rebase origin", branch)
            return False

        push_proc = _git(["push", "origin", branch], timeout=90)
        if push_proc.returncode == 0:
            print(f"  🚀 원격 저장소({branch}) 푸시 성공!")
            return True

        err = _git_err(push_proc)
        print(f"  ⚠️ 원격 푸시 실패: {err}")
        low = err.lower()
        if "authentication" in low or "permission" in low or "403" in low or "could not read username" in low:
            print("  💡 GitHub 인증 문제: Termux에 gh auth / PAT / SSH 키를 다시 확인하세요.")
        elif "non-fast-forward" in low or "rejected" in low:
            print("  💡 원격이 앞서 있습니다. git pull --rebase 후 다시 --sync-git 하세요.")
        return False

    except subprocess.TimeoutExpired:
        print("  ⚠️ Git 동기화 타임아웃 (네트워크/인증 대기 가능). 다음 주기에 재시도합니다.")
        # Timeout during pull --rebase can leave rebase state / index.lock behind.
        try:
            if Path(ROOT / ".git" / "rebase-merge").exists() or Path(ROOT / ".git" / "rebase-apply").exists():
                abort_proc = _git(["rebase", "--abort"], timeout=30)
                print(
                    "  ↩️ timeout 후 rebase --abort: "
                    + ("OK" if abort_proc.returncode == 0 else _git_err(abort_proc))
                )
            lock = ROOT / ".git" / "index.lock"
            if lock.exists():
                try:
                    lock.unlink()
                    print("  ↩️ stale index.lock 제거")
                except OSError as exc:
                    print(f"  ⚠️ index.lock 제거 실패: {exc}")
        except Exception as cleanup_exc:
            print(f"  ⚠️ timeout 정리 중 오류: {cleanup_exc}")
        return False
    except Exception as e:
        print(f"  ⚠️ Git 동기화 중 오류 발생 (다음 주기에 재시도): {type(e).__name__}: {e}")
        return False


def run_collection_cycle(round_num: int, sync_git: bool = False, branch: str | None = None) -> dict:
    """1회 전체 수집 사이클을 실행하고 상태를 기록한다."""
    start_iso = datetime.now(timezone.utc).isoformat()
    print_banner(round_num, start_iso)

    cycle_results = []
    success_count = 0

    for col in EDGE_COLLECTORS:
        res = run_single_collector(col)
        cycle_results.append(res)
        if res["status"] == "SUCCESS":
            success_count += 1
        time.sleep(1)

    end_iso = datetime.now(timezone.utc).isoformat()
    total_count = len(EDGE_COLLECTORS)

    summary = {
        "node_type": "Galaxy S20 Ultra (Termux Edge Collector)",
        "round": round_num,
        "started_at": start_iso,
        "finished_at": end_iso,
        "total_collectors": total_count,
        "success_count": success_count,
        "failed_count": total_count - success_count,
        "details": cycle_results,
        "git_sync": {"requested": bool(sync_git), "ok": None, "skipped": not sync_git},
    }

    # 동기화 전에 상태 파일을 써서 data/ 커밋에 이번 회차 영수증이 포함되게 한다.
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    if sync_git and success_count > 0:
        ok = sync_to_git(branch)
        summary["git_sync"] = {"requested": True, "ok": ok, "skipped": False}
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
    elif sync_git:
        print("\n[Git Data Sync] 성공한 수집기가 없어 푸시를 생략합니다.")
        summary["git_sync"] = {
            "requested": True,
            "ok": False,
            "skipped": True,
            "reason": "no_successful_collectors",
        }
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n" + "-" * 65)
    print(f"제 {round_num}회차 수집 종합: {total_count}개 중 {success_count}개 성공 / {total_count - success_count}개 실패")
    print(f"수집 노드 상태 저장: {STATUS_FILE}")
    if sync_git:
        print(f"Git 동기화: {summary['git_sync']}")
    print("-" * 65)

    return summary


def main():
    parser = argparse.ArgumentParser(description="Galaxy S20 Ultra Edge Collector Runner")
    parser.add_argument("--once", action="store_true", help="1회 수집 후 즉시 종료")
    parser.add_argument("--interval-hours", type=float, default=1.0, help="수집 반복 주기 (시간 단위, 기본 1.0)")
    parser.add_argument("--interval-minutes", type=float, default=None, help="수집 반복 주기 (분 단위)")
    parser.add_argument("--sync-git", action="store_true", help="수집 완료 후 data/ 결과를 Git으로 자동 푸시")
    parser.add_argument("--branch", type=str, default=None, help="푸시할 대상 Git 브랜치 (기본: 현재 브랜치)")
    args = parser.parse_args()

    if args.interval_minutes is not None:
        interval_sec = int(args.interval_minutes * 60)
        interval_desc = f"{args.interval_minutes}분"
    else:
        interval_sec = int(args.interval_hours * 3600)
        interval_desc = f"{args.interval_hours}시간"

    print("=" * 65)
    print("[Galaxy S20 Ultra] 24/7 무중단 수집 노드 가동 준비 완료")
    print(f"가동 모드: {'1회 단발 실행' if args.once else f'무한 반복 (매 {interval_desc} 주기)'}")
    print(f"Git 동기화: {'활성화됨 (수집 후 원격 자동 푸시)' if args.sync_git else '비활성화 (로컬 data/ 저장)'}")
    print("=" * 65)

    round_num = 1
    while True:
        try:
            run_collection_cycle(round_num, sync_git=args.sync_git, branch=args.branch)
        except Exception as e:
            print(f"경고: 사이클 실행 중 예기치 못한 에러 (다음 주기에 재시도): {e}")

        if args.once:
            print("\n--once 옵션에 따라 수집을 마치고 종료합니다.")
            break

        print(f"\n다음 수집까지 대기 중... ({interval_desc} 뒤 실행, 종료하려면 Ctrl+C)")
        try:
            time.sleep(interval_sec)
        except KeyboardInterrupt:
            print("\n사용자에 의해 수집 노드가 중단되었습니다.")
            break

        round_num += 1


if __name__ == "__main__":
    main()
