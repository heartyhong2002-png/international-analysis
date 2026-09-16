"""
sample_for_review.py — ADR-001 2단계 인간 표본 검수 자동화 모듈
================================================================

ADR-001("LLM 역할정의 및 감성분석 휴먼인더루프")의 2단계(인간 표본 검수 15~20%)를
위한 층화 표본 추출(Stratified Sampling), 검수 시트 생성, 검수 완료본 병합(Sync),
품질 통계 감사 CLI 도구입니다.

주요 기능:
  1. 층화 표본 추출 (Stratified Sampling):
     - 언어(language) 및 이슈(issue_ids)별 그룹으로 묶어 특정 이슈/언어 편중 방지.
     - 각 계층별 최소 1건(min_samples_per_group=1) 추출 보장.
  2. 차등 가중 샘플링:
     - 안정 모델(en, ko, zh, ja): 기본 20% 무작위 추출.
     - 약점 모델(ru, ar): 프롬프트 지시 불이행 위험으로 기본 100% 전수 검수 추출.
  3. 검수 전용 시트 생성 (data/pending_human_review.csv):
     - 검수자에게 필요한 핵심 컬럼(제목, 근거문장, LLM라벨, 기입란)만 정리하여 내보냄.
  4. 검수 완료본 역병합 (--merge):
     - 검수자가 작성한 CSV를 원본 data/review_log.csv에 안전하게 반영 (이력 보존).
  5. 감사 및 통계 리포팅 (--stats):
     - 검수 커버리지, 모델 일치율, 과잉비판 오판율 등 혼동 행렬 지표 출력.

사용법:
    # 1. 새 검수 표본 추출 (기본 20%, ru/ar 100%)
    python scripts/sample_for_review.py

    # 2. 비율 커스텀 조정
    python scripts/sample_for_review.py --rate 0.15 --high-risk-rate 0.8

    # 3. 현재 검수 현황 통계 확인
    python scripts/sample_for_review.py --stats

    # 4. 엑셀 등에서 작성 완료한 검수 파일 병합
    python scripts/sample_for_review.py --merge data/pending_human_review.csv

    # 5. 자체 테스트 실행
    python scripts/sample_for_review.py --self-test
"""

import argparse
import csv
import math
import os
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 기본 경로
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_INPUT_CSV = DATA_DIR / "review_log.csv"
DEFAULT_OUTPUT_SAMPLE_CSV = DATA_DIR / "pending_human_review.csv"

# 약점 모델 언어 (Ollama 템플릿/few-shot 복사 취약 모델)
HIGH_RISK_LANGUAGES = {"ru", "ar"}

# 검수 전용 파일에 노출할 정돈된 컬럼 목록
REVIEW_SHEET_FIELDS = [
    "article_id",
    "language",
    "issue_ids",
    "continent",
    "source_type",
    "outlet_bias",
    "title",
    "llm_label",
    "llm_evidence_quote",
    "human_label",       # 검수자가 채울 곳 (우호적 / 중립적 / 비판적)
    "correction_note",   # 검수자가 채울 곳 (불일치 시 판단 근거)
    "reviewed_at",       # 검수 완료 일시 (비워두면 병합 시 자동 입력)
    "link",
]


def load_review_log(csv_path: Path) -> list[dict]:
    """review_log.csv 파일을 읽어 딕셔너리 리스트로 반환합니다."""
    if not csv_path.exists():
        return []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def save_review_log(csv_path: Path, rows: list[dict], fieldnames: list[str] = None) -> None:
    """리스트 데이터를 CSV로 안전하게 저장합니다."""
    if not rows:
        return
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if not fieldnames:
        fieldnames = list(rows[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def extract_primary_issue(issue_str: str) -> str:
    """issue_ids 필드에서 대표 이슈 1개를 추출합니다."""
    if not issue_str:
        return "unspecified"
    cleaned = issue_str.strip("[]'\" ")
    if not cleaned:
        return "unspecified"
    parts = [p.strip(" '\"") for p in cleaned.split(",")]
    return parts[0] if parts else "unspecified"


def select_stratified_samples(
    articles: list[dict],
    rate: float = 0.20,
    high_risk_rate: float = 1.00,
    min_samples_per_group: int = 1,
    seed: int = 42,
    include_unclassified: bool = False,
    require_llm_label: bool = False,
) -> list[dict]:
    """
    언어 및 이슈별로 계층화(Stratified)하여 대표성 있는 검수 표본을 추출합니다.
    - 약점 모델(ru, ar)은 high_risk_rate(기본 100%) 적용
    - 일반 모델(en, ko, zh, ja 등)은 rate(기본 20%) 적용
    - 미검수 기사(human_label이 비어있는 기사)만 표본 후보로 선정
    """
    rng = random.Random(seed)

    # 1. 검수 대상 필터링
    candidates = []
    for art in articles:
        # 이미 사람이 검수한 건 제외
        if (art.get("human_label") or "").strip():
            continue

        tag_status = (art.get("tag_status") or "").strip().lower()
        if not include_unclassified and tag_status == "unclassified":
            continue

        if require_llm_label and not (art.get("llm_label") or "").strip():
            continue

        candidates.append(art)

    if not candidates:
        return []

    # 2. 언어 및 이슈 기준 그룹화
    grouped = defaultdict(list)
    for art in candidates:
        lang = (art.get("language") or "en").strip().lower()
        issue = extract_primary_issue(art.get("issue_ids", ""))
        grouped[(lang, issue)].append(art)

    sampled = []
    for (lang, issue), items in grouped.items():
        # 언어별 샘플링 비율 결정
        sample_rate = high_risk_rate if lang in HIGH_RISK_LANGUAGES else rate
        target_count = math.ceil(len(items) * sample_rate)

        # 계층별 최소 표본 수 보장
        target_count = max(target_count, min(len(items), min_samples_per_group))

        # 무작위 추출
        shuffled = list(items)
        rng.shuffle(shuffled)
        sampled.extend(shuffled[:target_count])

    return sampled


def create_sample_batch(
    input_csv: Path = DEFAULT_INPUT_CSV,
    output_csv: Path = DEFAULT_OUTPUT_SAMPLE_CSV,
    rate: float = 0.20,
    high_risk_rate: float = 1.00,
    include_unclassified: bool = False,
    seed: int = 42,
) -> list[dict]:
    """검수 대기 표본 CSV(pending_human_review.csv)를 생성합니다."""
    articles = load_review_log(input_csv)
    if not articles:
        print(f"⚠ 입력 파일에 기사 데이터가 없습니다: {input_csv}")
        return []

    # 만약 LLM 라벨이 일부라도 있으면 require_llm_label=True 적용, 전혀 없으면 False로 전체 대상
    has_any_llm_label = any((a.get("llm_label") or "").strip() for a in articles)

    sampled = select_stratified_samples(
        articles,
        rate=rate,
        high_risk_rate=high_risk_rate,
        include_unclassified=include_unclassified,
        require_llm_label=has_any_llm_label,
        seed=seed,
    )

    if not sampled:
        print("✓ 현재 새로 검수할 대상(미검수 표본)이 없습니다.")
        return []

    # 검수 전용 시트 포맷으로 필드 정돈
    output_rows = []
    for item in sampled:
        row = {f: item.get(f, "") for f in REVIEW_SHEET_FIELDS}
        # 검수란은 비워둠
        row["human_label"] = ""
        row["correction_note"] = ""
        row["reviewed_at"] = ""
        output_rows.append(row)

    save_review_log(output_csv, output_rows, fieldnames=REVIEW_SHEET_FIELDS)

    # 요약 통계 출력
    lang_counts = Counter(r["language"] for r in output_rows)
    print(f"\n✅ 검수 표본 {len(output_rows)}건 추출 완료 ➔ {output_csv}")
    print("   [언어별 표본 분포]")
    for lang, cnt in sorted(lang_counts.items()):
        is_high = " (고위험 100% 전수)" if lang in HIGH_RISK_LANGUAGES else " (20% 표본)"
        print(f"     • {lang:<4}: {cnt:>3}건{is_high}")
    print("\n💡 엑셀 또는 CSV 편집기로 'human_label' (우호적/중립적/비판적) 컬럼을 입력한 후,")
    print(f"   'python scripts/sample_for_review.py --merge {output_csv.name}' 명령으로 반영하세요.\n")

    return output_rows


def merge_completed_reviews(
    completed_csv: Path,
    target_review_log_csv: Path = DEFAULT_INPUT_CSV,
) -> int:
    """검수자가 작성한 human_label 및 correction_note를 원본 review_log.csv에 병합합니다."""
    if not completed_csv.exists():
        print(f"✗ 검수 완료 파일을 찾을 수 없습니다: {completed_csv}")
        return 0

    completed_rows = load_review_log(completed_csv)
    # 검수란(human_label)이 채워진 행만 맵으로 구성
    review_map_by_id = {}
    review_map_by_title = {}
    valid_count = 0

    now_iso = datetime.now(timezone.utc).isoformat()

    for row in completed_rows:
        art_id = (row.get("article_id") or "").strip()
        title = (row.get("title") or "").strip()
        h_label = (row.get("human_label") or "").strip()
        c_note = (row.get("correction_note") or "").strip()
        r_at = (row.get("reviewed_at") or "").strip() or now_iso

        if h_label or c_note:
            payload = {
                "human_label": h_label,
                "correction_note": c_note,
                "reviewed_at": r_at,
            }
            if art_id:
                review_map_by_id[art_id] = payload
            if title:
                review_map_by_title[title] = payload
            valid_count += 1

    if not valid_count:
        print(f"⚠ {completed_csv}에 작성된 검수 내용(human_label)이 없습니다.")
        return 0

    target_rows = load_review_log(target_review_log_csv)
    if not target_rows:
        print(f"✗ 원본 검수 로그를 찾을 수 없습니다: {target_review_log_csv}")
        return 0

    updated_count = 0
    for row in target_rows:
        art_id = (row.get("article_id") or "").strip()
        title = (row.get("title") or "").strip()
        match = review_map_by_id.get(art_id) or review_map_by_title.get(title)
        if match:
            row["human_label"] = match["human_label"]
            row["correction_note"] = match["correction_note"]
            row["reviewed_at"] = match["reviewed_at"]
            updated_count += 1

    # 저장
    save_review_log(target_review_log_csv, target_rows)
    print(f"✅ 검수 결과 {updated_count}건을 {target_review_log_csv}에 안전하게 병합했습니다.")
    return updated_count


def print_audit_stats(csv_path: Path = DEFAULT_INPUT_CSV) -> None:
    """ADR-001 품질 감사 지표 및 검수 진행 통계를 출력합니다."""
    rows = load_review_log(csv_path)
    if not rows:
        print(f"⚠ 분석할 데이터가 없습니다: {csv_path}")
        return

    total = len(rows)
    tag_counts = Counter(r.get("tag_status", "unclassified") for r in rows)
    llm_classified = [r for r in rows if (r.get("llm_label") or "").strip()]
    human_reviewed = [r for r in rows if (r.get("human_label") or "").strip()]

    print("\n" + "=" * 65)
    print(f"📊 ADR-001 휴먼-인-더-루프(HITL) 검수 감사 리포트 ({csv_path.name})")
    print("=" * 65)
    print(f"• 총 수집 기사 수    : {total:,}건")
    print(f"  - matched (확정)   : {tag_counts.get('matched', 0):,}건")
    print(f"  - ambiguous (경계) : {tag_counts.get('ambiguous', 0):,}건")
    print(f"  - unclassified     : {tag_counts.get('unclassified', 0):,}건 (LLM 생략)")
    print("-" * 65)
    print(f"• LLM 1차 분류 완료  : {len(llm_classified):,}건")
    print(f"• 인간 2차 검수 완료 : {len(human_reviewed):,}건")

    if total > 0:
        coverage = (len(human_reviewed) / total) * 100
        print(f"• 전체 검수 커버리지 : {coverage:.1f}%")

    # LLM과 인간 검수가 모두 있는 데이터 대상 혼동 분석
    evaluated = [r for r in human_reviewed if (r.get("llm_label") or "").strip()]
    if evaluated:
        agreements = sum(1 for r in evaluated if r["llm_label"] == r["human_label"])
        acc = (agreements / len(evaluated)) * 100
        over_critical = sum(
            1 for r in evaluated if r["llm_label"] == "비판적" and r["human_label"] != "비판적"
        )
        under_critical = sum(
            1 for r in evaluated if r["llm_label"] != "비판적" and r["human_label"] == "비판적"
        )

        print("-" * 65)
        print(f"• 평가 유효 표본     : {len(evaluated)}건")
        print(f"• 모델-인간 일치 건수: {agreements}건 ({acc:.1f}% 정확도)")
        print(f"• 불일치 건수        : {len(evaluated) - agreements}건")
        print(f"  - 과잉 비판 (Over-Critical) : {over_critical}건 (사실 전달인데 비판으로 오판)")
        print(f"  - 비판 누락 (Under-Critical): {under_critical}건 (비판 서술인데 중립으로 오판)")
    else:
        print("-" * 65)
        print("• 평가 유효 표본     : 아직 LLM 분류와 인간 검수가 동시에 완료된 데이터 없음")
    print("=" * 65 + "\n")


def run_self_test() -> None:
    """자체 단위 테스트를 수행하여 샘플링과 병합 동작을 검증합니다."""
    print("🧪 [Self-Test] sample_for_review.py 자체 검증 시작...")

    # 가상 기사 60건 생성 (언어별 10건씩)
    test_articles = []
    languages = ["en", "ko", "zh", "ja", "ru", "ar"]
    for i in range(60):
        lang = languages[i % len(languages)]
        issue = "US_Canada_Trade" if i % 2 == 0 else "Trump_Economy"
        test_articles.append({
            "article_id": f"test_{i:03d}",
            "language": lang,
            "issue_ids": f"['{issue}']",
            "tag_status": "matched",
            "title": f"Test Headline {i} ({lang})",
            "llm_label": "중립적",
            "human_label": "",
            "correction_note": "",
        })

    # 1. 층화 표본 추출 테스트
    samples = select_stratified_samples(test_articles, rate=0.20, high_risk_rate=1.00, seed=123)

    sample_langs = Counter(s["language"] for s in samples)
    # ru와 ar은 10건 전부(100%) 추출되어야 함
    assert sample_langs["ru"] == 10, f"ru should have 10 samples, got {sample_langs['ru']}"
    assert sample_langs["ar"] == 10, f"ar should have 10 samples, got {sample_langs['ar']}"
    # 일반 언어는 10건 중 약 20% (각 2건 이상)
    for normal_lang in ["en", "ko", "zh", "ja"]:
        assert 2 <= sample_langs[normal_lang] <= 3, f"{normal_lang} sample count unexpected: {sample_langs[normal_lang]}"

    print("  ✓ 층화 샘플링 및 약점 언어 100% 가중 추출 검증 통과")

    # 2. 검수 완료본 병합 테스트
    temp_dir = DATA_DIR / "temp_test"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_review_log = temp_dir / "test_review_log.csv"
    temp_pending = temp_dir / "test_pending.csv"

    try:
        save_review_log(temp_review_log, test_articles)

        # pending에 1건 검수 작성 시뮬레이션
        mock_completed = [{
            "article_id": "test_000",
            "language": "en",
            "title": test_articles[0]["title"],
            "human_label": "비판적",
            "correction_note": "오판 교정 테스트",
            "reviewed_at": "",
        }]
        save_review_log(temp_pending, mock_completed)

        updated = merge_completed_reviews(temp_pending, temp_review_log)
        assert updated == 1, f"Expected 1 updated row, got {updated}"

        reloaded = load_review_log(temp_review_log)
        target = next(r for r in reloaded if r["article_id"] == "test_000")
        assert target["human_label"] == "비판적"
        assert target["correction_note"] == "오판 교정 테스트"
        assert target["reviewed_at"] != ""
        print("  ✓ 검수 결과 역병합 및 타임스탬프 자동 갱신 검증 통과")

    finally:
        # 임시 파일 정리
        if temp_review_log.exists():
            temp_review_log.unlink()
        if temp_pending.exists():
            temp_pending.unlink()
        if temp_dir.exists():
            try:
                temp_dir.rmdir()
            except Exception:
                pass

    print("🎉 [Self-Test] 모든 검증 통과 완료!\n")


def main():
    parser = argparse.ArgumentParser(description="ADR-001 2단계 인간 표본 검수 자동화 도구")
    parser.add_argument("--rate", type=float, default=0.20, help="안정 모델 기본 표본 추출 비율 (기본값: 0.20 = 20%%)")
    parser.add_argument("--high-risk-rate", type=float, default=1.00, help="약점 모델(ru, ar) 표본 추출 비율 (기본값: 1.00 = 100%%)")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_CSV, help="입력 원본 review_log.csv 경로")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_SAMPLE_CSV, help="생성할 검수 표본 CSV 경로")
    parser.add_argument("--merge", type=Path, default=None, help="검수 작성 완료된 CSV를 원본 review_log에 병합")
    parser.add_argument("--stats", action="store_true", help="현재 검수 현황 및 품질 감사 통계 출력")
    parser.add_argument("--include-unclassified", action="store_true", help="범위 밖(unclassified) 기사도 표본에 포함")
    parser.add_argument("--self-test", action="store_true", help="내부 단위 테스트 실행")
    args = parser.parse_args()

    if args.self_test:
        run_self_test()
        return

    if args.stats:
        print_audit_stats(args.input)
        return

    if args.merge:
        merge_completed_reviews(args.merge, args.input)
        return

    create_sample_batch(
        input_csv=args.input,
        output_csv=args.output,
        rate=args.rate,
        high_risk_rate=args.high_risk_rate,
        include_unclassified=args.include_unclassified,
    )


if __name__ == "__main__":
    main()
