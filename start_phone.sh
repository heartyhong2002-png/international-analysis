#!/bin/bash
# start_phone.sh — 갤럭시 S20 울트라 24/7 수집 노드 원클릭 시작기

echo "=========================================================="
echo "📱 Galaxy S20 Ultra 24/7 Edge Collection Node Starter"
echo "=========================================================="

# 1. 화면이 꺼져도 CPU 잠들지 않도록 방지
termux-wake-lock
echo "✓ CPU Wakelock 활성화 완료"

# 2. 최신 코드 동기화
echo "✓ 최신 수집기 코드 동기화 (git pull)..."
git pull

# 3. 24시간 수집기 가동 (기본 1시간 주기)
echo "🚀 24시간 자동 수집기 가동 시작 (종료는 Ctrl+C)"
echo "=========================================================="
python scripts/collection/run_phone_collector.py "$@"
