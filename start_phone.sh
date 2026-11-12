#!/bin/bash
# start_phone.sh — 갤럭시 S20 울트라 24/7 수집 노드 원클릭 시작기

set -uo pipefail
# NOTE: do not use `set -e` — network/wakelock failures must not abort collection.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BRANCH="${EDGE_GIT_BRANCH:-cursor/actions-light-collection}"

echo "=========================================================="
echo "Galaxy S20 Ultra 24/7 Edge Collection Node Starter"
echo "branch: ${BRANCH}"
echo "cwd: ${SCRIPT_DIR}"
echo "=========================================================="

# 1. 화면이 꺼져도 CPU 잠들지 않도록 방지 (실패해도 수집 계속)
if command -v termux-wake-lock >/dev/null 2>&1; then
  if termux-wake-lock; then
    echo "[ok] CPU Wakelock 활성화"
  else
    echo "[warn] termux-wake-lock 실패 — 화면 꺼짐 시 수집이 멈출 수 있음"
  fi
else
  echo "[warn] termux-wake-lock 없음 — 화면 꺼짐 시 수집이 멈출 수 있음"
fi

# 2. 최신 코드 동기화 (명시 브랜치) — 로컬 data/ 충돌 시에도 원격 최신 코드로 자동 정렬
echo "[ok] 최신 코드 동기화 시도: git fetch origin ${BRANCH}"
if git fetch origin "${BRANCH}"; then
  git checkout "${BRANCH}" 2>/dev/null || git checkout -B "${BRANCH}" "origin/${BRANCH}" || true
  if ! git pull --ff-only origin "${BRANCH}"; then
    echo "[warn] ff-only pull 불가 (로컬 data/ 커밋 충돌) — 원격 최신 브랜치로 자동 리셋 후 수집을 재개합니다."
    git rebase --abort 2>/dev/null || true
    git merge --abort 2>/dev/null || true
    git reset --hard "origin/${BRANCH}" || true
  fi
else
  echo "[warn] git fetch 실패 (네트워크) — 로컬 스크립트로 수집을 계속합니다."
fi

# 3. 수집기 가동 (기본값: --sync-git 활성화하여 매 주기 GitHub 자동 푸시)
echo "자동 수집 시작 (종료: Ctrl+C)"
echo "GitHub 자동 푸시: 기본 활성화 (--sync-git)"
echo "=========================================================="
python scripts/collection/run_phone_collector.py --branch "${BRANCH}" --sync-git "$@"
