"""data_retriever.py — 이슈별 데이터 검색 엔진

챗봇_구현_세부_계획.md 3.2절 설계를 구현. 기존 파이프라인이 만들어 둔 파일들을
그대로 읽는다 — 새 데이터 포맷을 만들지 않는다:

  - data/auto_benchmark_results.csv      (auto_benchmark_verifier.py 산출물)
  - data/reddit_signals/reddit_opinion_latest.csv   (fetch_reddit_opinion.py 산출물)
  - data/reddit_signals/reddit_opinion_summary.json (fetch_reddit_opinion.py 산출물)

MySQL은 "있으면 쓰고 없으면 CSV로 폴백"으로 설계했다. 이 프로토타입은 클라우드
샌드박스에서 작성되어 실제 MySQL(사용자의 로컬 Galaxy Book5 Pro 환경)에 붙어있지
않기 때문에, CSV 폴백 경로가 실제로 검증된 경로이고 MySQL 경로는 스키마 가정 하에
작성만 해 둔 상태다 — 로컬에서 처음 켤 때 반드시 실제 컬럼명과 대조해봐야 한다.

auto_benchmark_results.csv에는 issue_id 컬럼이 없다(기사 title/outlet만 있음).
그래서 이슈 매칭은 title에 이슈 키워드가 들어있는지로 근사한다 — 완벽하지
않지만, 이슈별 태깅 파이프라인(build_database.py 쪽)이 아직 이 CSV까지
커버하지 않는 현재 상태에서는 이게 유일하게 동작하는 방법이다. 이슈 태깅이
CSV 레벨에서 이뤄지게 되면 이 근사 로직은 걷어내면 된다.
"""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .issues import ISSUES

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

BENCHMARK_CSV = DATA_DIR / "auto_benchmark_results.csv"
REDDIT_CSV = DATA_DIR / "reddit_signals" / "reddit_opinion_latest.csv"
REDDIT_SUMMARY_JSON = DATA_DIR / "reddit_signals" / "reddit_opinion_summary.json"


@dataclass
class RetrievedContext:
    issue_id: Optional[str]
    articles: list[dict] = field(default_factory=list)
    tone_distribution: dict[str, int] = field(default_factory=dict)
    reddit_posts: list[dict] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)  # 데이터 부족/폴백 상황을 응답 생성기에 알림

    def is_empty(self) -> bool:
        return not self.articles and not self.reddit_posts


def _issue_keywords_for_matching(issue_id: str) -> list[str]:
    info = ISSUES.get(issue_id, {})
    return [kw.lower() for kw in info.get("keywords_primary", []) + info.get("keywords_secondary", [])]


def _load_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


class DataRetriever:
    """MySQL 연결을 선택적으로 받는다. 없으면(None) CSV 전용으로 동작."""

    def __init__(self, mysql_connection=None, data_dir: Path = DATA_DIR):
        self.db = mysql_connection
        self.data_dir = data_dir

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------

    def get_context(self, issue_id: Optional[str], days: int = 30) -> RetrievedContext:
        """의도 분류기가 뽑아준 issue_id 하나에 대해 관련 데이터를 전부 모아
        RetrievedContext로 반환. issue_id가 None이면(이슈 특정 실패) 빈 컨텍스트."""
        ctx = RetrievedContext(issue_id=issue_id)

        if issue_id is None:
            ctx.warnings.append("쿼리에서 특정 이슈를 찾지 못했습니다 — 21개 이슈 목록 중 하나를 언급해 주세요.")
            return ctx

        if self.db is not None:
            try:
                self._fill_from_mysql(ctx, issue_id, days)
            except Exception as e:  # noqa: BLE001 — DB 스키마 불일치 등 어떤 이유든 CSV로 안전하게 폴백
                ctx.warnings.append(f"MySQL 조회 실패({e}) — CSV 데이터로 대체합니다.")

        if not ctx.articles:
            self._fill_from_csv(ctx, issue_id)

        return ctx

    # ------------------------------------------------------------------
    # CSV 경로 (검증됨 — 이 프로토타입에서 실제로 동작하는 경로)
    # ------------------------------------------------------------------

    def _fill_from_csv(self, ctx: RetrievedContext, issue_id: str) -> None:
        keywords = _issue_keywords_for_matching(issue_id)

        # 1) 벤치마크/톤 CSV에서 제목 키워드 매칭
        rows = _load_csv(BENCHMARK_CSV)
        matched = [r for r in rows if any(kw in r.get("title", "").lower() for kw in keywords)]
        for r in matched:
            ctx.articles.append({
                "title": r.get("title"),
                "outlet": r.get("source_outlet"),
                "allsides_bias": r.get("allsides_bias"),
                "tone": r.get("consensus_label"),
                "agreement_ratio": r.get("agreement_ratio"),
                "link": r.get("link"),
            })
            outlet = r.get("source_outlet")
            if outlet:
                ctx.sources.append(outlet)

        for r in matched:
            tone = r.get("consensus_label", "미분류")
            ctx.tone_distribution[tone] = ctx.tone_distribution.get(tone, 0) + 1

        if not matched and rows:
            ctx.warnings.append(
                f"'{issue_id}' 관련 기사가 현재 벤치마크 캐시(auto_benchmark_results.csv, {len(rows)}건)에 없습니다. "
                "auto_benchmark_verifier.py를 더 많은 --limit으로 재실행하면 커버리지가 늘어날 수 있습니다."
            )

        # 2) Reddit 커뮤니티 의견
        reddit_rows = _load_csv(REDDIT_CSV)
        reddit_matched = [
            r for r in reddit_rows
            if any(kw in (r.get("title", "") + " " + r.get("content", "")).lower() for kw in keywords)
        ]
        for r in reddit_matched:
            ctx.reddit_posts.append({
                "subreddit": r.get("subreddit"),
                "title": r.get("title"),
                "sentiment": r.get("sentiment"),
                "summary_ko": r.get("summary_ko"),
                "link": r.get("link"),
            })
            ctx.sources.append(f"r/{r.get('subreddit')}")

        ctx.sources = sorted(set(s for s in ctx.sources if s))

    # ------------------------------------------------------------------
    # MySQL 경로 (스키마 가정 — 로컬 환경에서 실 컬럼명 대조 필요)
    # ------------------------------------------------------------------

    def _fill_from_mysql(self, ctx: RetrievedContext, issue_id: str, days: int) -> None:
        """DATABASE_SETUP.md 기준 articles/tone_labels/issue_tracking 테이블 가정.
        실제 컬럼명이 다르면 이 메서드만 고치면 된다(다른 경로엔 영향 없음) —
        auto_benchmark_verifier.py가 AllSides 파싱에서 쓴 것과 같은 '방어적 처리' 원칙.
        """
        cursor = self.db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT a.title, a.source_outlet, a.link, t.tone_label
            FROM articles a
            JOIN tone_labels t ON t.article_id = a.article_id
            WHERE a.issue_id = %s
              AND a.published_at > NOW() - INTERVAL %s DAY
            ORDER BY a.published_at DESC
            LIMIT 20
            """,
            (issue_id, days),
        )
        rows = cursor.fetchall()
        for r in rows:
            ctx.articles.append({
                "title": r["title"],
                "outlet": r["source_outlet"],
                "tone": r["tone_label"],
                "link": r["link"],
            })
            tone = r["tone_label"] or "미분류"
            ctx.tone_distribution[tone] = ctx.tone_distribution.get(tone, 0) + 1
            if r["source_outlet"]:
                ctx.sources.append(r["source_outlet"])

        cursor.close()

    # ------------------------------------------------------------------
    # 보조: Reddit 서브레딧 전체 요약(이슈 무관, 전반적 여론 지형 파악용)
    # ------------------------------------------------------------------

    def get_reddit_overview(self) -> dict:
        if not REDDIT_SUMMARY_JSON.exists():
            return {}
        with open(REDDIT_SUMMARY_JSON, "r", encoding="utf-8") as f:
            return json.load(f)


def format_tone_distribution(tone_distribution: dict[str, int]) -> str:
    """{"비판적": 3, "중립적": 2} -> "비판적 60% | 중립적 40%" 같은 표시용 문자열."""
    total = sum(tone_distribution.values())
    if total == 0:
        return "톤 데이터 없음"
    parts = [f"{tone} {round(count / total * 100)}%" for tone, count in
              sorted(tone_distribution.items(), key=lambda x: x[1], reverse=True)]
    return " | ".join(parts)


if __name__ == "__main__":
    retriever = DataRetriever(mysql_connection=None)
    for issue_id in ["US_China_Trade", "Iran_Nuclear", "Japan_Korea_Relations"]:
        ctx = retriever.get_context(issue_id)
        print(f"\n=== {issue_id} ===")
        print(f"기사 {len(ctx.articles)}건, Reddit {len(ctx.reddit_posts)}건")
        print(f"톤 분포: {format_tone_distribution(ctx.tone_distribution)}")
        print(f"출처: {ctx.sources}")
        if ctx.warnings:
            print(f"경고: {ctx.warnings}")
