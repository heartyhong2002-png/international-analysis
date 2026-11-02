#!/bin/bash
# start_phone.sh — 갤럭시 S20 울트라 24/7 수집 노드 원클릭 시작기

set -euo pipefail

BRANCH="${EDGE_GIT_BRANCH:-cursor/actions-light-collection}"

echo "=========================================================="
echo "Galaxy S20 Ultra 24/7 Edge Collection Node Starter"
echo "branch: ${BRANCH}"
echo "=========================================================="

# 1. 화면이 꺼져도 CPU 잠들지 않도록 방지
if command -v termux-wake-lock >/dev/null 2>&1; then
  termux-wake-lock
  echo "[ok] CPU Wakelock 활성화"
else
  echo "[warn] termux-wake-lock 없음 — 화면 꺼짐 시 수집이 멈출 수 있음"
fi

# 2. 최신 코드 동기화 (명시 브랜치)
echo "[ok] 최신 코드 동기화: git pull --ff-only origin ${BRANCH}"
git fetch origin "${BRANCH}"
git checkout "${BRANCH}" 2>/dev/null || git checkout -B "${BRANCH}" "origin/${BRANCH}"
git pull --ff-only origin "${BRANCH}" || {
  echo "[warn] ff-only pull 실패 — 로컬 커밋/충돌 가능. 수동 확인: git status"
}

# 3. 수집기 가동
echo "자동 수집 시작 (종료: Ctrl+C)"
echo "GitHub 자동 푸시: bash start_phone.sh --once --sync-git"
echo "=========================================================="
python scripts/collection/run_phone_collector.py --branch "${BRANCH}" "$@"
