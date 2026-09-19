"""
fetch_reddit_opinion.py — Reddit 공개 RSS(Atom) 기반 미국 여론 텍스트 마이닝 모듈
====================================================================================

목적 (PHASE2_THINKTANK_REDDIT_HANDOFF.md 참고):
  - Reddit 공식 API는 2025-11-11부터 셀프서비스 발급이 닫히고 사전 승인제(Responsible
    Builder Policy)로 바뀌었다. 그래서 API 키 없이 공개 `.rss`(Atom) 엔드포인트만 쓴다.
  - r/geopolitics, r/worldnews 게시물 + 게시물별 상위 댓글을 수집한다.
  - (선택) 로컬 LLM(Ollama)으로 게시물 감정/논란 키워드를 추출한다.

수집 대상 엔드포인트 (모두 인증 불필요):
  - 게시물 목록 : https://www.reddit.com/r/{sub}/.rss
  - 게시물 댓글 : https://www.reddit.com/r/{sub}/comments/{id}/{slug}/.rss?sort=top&limit=N

안전장치 (승인 없는 자동 수집은 회색지대이므로 최소한의 예의를 코드로 강제):
  - 요청 간 최소 간격(기본 6초 ≈ 분당 10회) — `--delay`로 조정
  - HTTP 403 또는 429를 받으면 재시도 없이 **그 자리에서 전체 수집 중단** (우회 시도 없음)
    ※ 게시물 목록 요청만 429에 한해 지수 백오프로 최대 3회 재시도, 그래도 429면 중단
  - 구체적인 User-Agent 명시, 기본 수집량 소량(서브레딧당 게시물 10, 댓글은 5개 글 x 15개)

결과물 (data/reddit_signals/):
  - reddit_opinion_latest.csv      : 최신 게시물 (매번 덮어씀 — 기존 호환)
  - reddit_comments_latest.csv     : 최신 댓글 (수집된 댓글이 있을 때만 덮어씀)
  - reddit_opinion_summary.json    : 요약 통계
  - history/reddit_posts_history.csv, history/reddit_comments_history.csv
                                   : 날짜별 누적 (같은 날 재실행해도 중복 안 쌓임)

⚠️ 검증 상태: 게시물 피드(`/r/{sub}/.rss`)는 2026-09-18 실제 실행으로 3건 수집 확인됨.
   **댓글 피드 형식은 이 코드를 작성한 클라우드 세션에서 reddit.com에 도달할 수 없어 실물
   확인을 못 했다.** 아래 가정에 기반한다:
     1) 댓글 페이지 `.rss`는 Atom이며, 게시물 자신은 id가 `t3_`로, 댓글은 `t1_`로 시작한다.
     2) `sort=top`, `limit=N` 쿼리는 무시될 수도 있다(무시돼도 동작은 함).
   가정이 틀리면 `_parse_comment_atom()`만 고치면 된다. **먼저 로컬에서 아래로 확인 권장:**
     python scripts/fetch_reddit_opinion.py --subreddit geopolitics --limit 2 --comment-posts 1
   그리고 data/reddit_signals/reddit_comments_latest.csv를 열어 body가 진짜 댓글인지 확인.

사용법:
  python scripts/fetch_reddit_opinion.py                      # 기본: 게시물 10건 + 상위 5개 글의 댓글 15개씩
  python scripts/fetch_reddit_opinion.py --subreddit geopolitics --limit 15
  python scripts/fetch_reddit_opinion.py --comments 0         # 댓글 수집 끄기(게시물만)
  python scripts/fetch_reddit_opinion.py --comments 25 --comment-posts 3
  python scripts/fetch_reddit_opinion.py --no-filter          # 고정글/AMA 필터 끄기
  python scripts/fetch_reddit_opinion.py --with-llm           # 로컬 Ollama로 게시물 감정/논란 키워드 분석
  python scripts/fetch_reddit_opinion.py --self-test          # 네트워크/Ollama 없이 로직 검증(실데이터 미변경)
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "reddit_signals"

DEFAULT_SUBREDDITS = ["geopolitics", "worldnews"]
DEFAULT_COMMENTS_PER_POST = 15   # 게시물당 수집할 댓글 수 (0이면 댓글 수집 안 함)
DEFAULT_COMMENT_POSTS = 5        # 서브레딧당 댓글을 가져올 게시물 수(필터 통과한 글 중 앞에서부터)
DEFAULT_DELAY_SEC = 6.0          # 요청 간 최소 간격 (익명 트래픽 분당 ~10회 수준 유지)
MAX_COMMENT_BODY_CHARS = 2000

# Reddit 공식 API 인증 정보 (.env 지원) — 현재 신규 발급은 사전 승인제라 대부분 비어 있음.
# 키가 있으면 OAuth를 우선 시도하고, 없거나 실패하면 공개 RSS로 자동 fallback.
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "").strip()
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "").strip()
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "InternationalAnalysisBot/1.0 (by /u/heartyhong2002)").strip()

# 공개 RSS용 요청 헤더
REQUEST_HEADERS = {"User-Agent": REDDIT_USER_AGENT}

_ATOM_NS = "{http://www.w3.org/2005/Atom}"
_MAX_RETRIES = 3

# 요청 간격 제어 (CLI --delay로 덮어씀)
REQUEST_DELAY_SEC = DEFAULT_DELAY_SEC
_last_request_ts: float | None = None

# 403/429를 받으면 True로 바뀌고, 이후 모든 Reddit 요청을 즉시 건너뛴다.
_BLOCK: dict = {"blocked": False, "reason": ""}

# 고정글/공지/정기 스레드 필터 (RSS에는 stickied 플래그가 없어 제목으로 판단)
_NOISE_TITLE_PATTERNS = [
    re.compile(r"subreddit rules", re.I),
    re.compile(r"^\s*rules\b", re.I),
    re.compile(r"\bAMA\b"),  # 대소문자 구분: 사람 이름 'Ama' 등 오탐 방지
    re.compile(r"\b(daily|weekly|monthly)\b.*\b(thread|discussion)\b", re.I),
]

# 댓글 필터
_BOT_AUTHORS = {"automoderator", "[deleted]", "deleted"}
_EMPTY_BODIES = {"", "[deleted]", "[removed]"}

# "submitted by /u/xxx [link] [comments]" 꼬리표 (게시물 content 끝에 항상 붙음)
_FOOTER_RE = re.compile(r"\s*submitted by\s+/?u/\S+\s*\[link\]\s*\[comments\]\s*$", re.I)


# ============================================================================
# 공통: 요청 제어 (간격 유지 + 403/429 즉시 중단)
# ============================================================================

def _reset_block() -> None:
    global _last_request_ts
    _BLOCK["blocked"] = False
    _BLOCK["reason"] = ""
    _last_request_ts = None


def _set_block(reason: str) -> None:
    if not _BLOCK["blocked"]:
        print(f"[fetch] ⛔ {reason} — Reddit 수집을 여기서 중단합니다(우회 시도 없음). "
              f"이미 모은 데이터는 저장됩니다.")
    _BLOCK["blocked"] = True
    _BLOCK["reason"] = reason


def _throttle() -> None:
    """직전 요청으로부터 REQUEST_DELAY_SEC가 지나도록 대기."""
    global _last_request_ts
    if _last_request_ts is not None and REQUEST_DELAY_SEC > 0:
        wait = REQUEST_DELAY_SEC - (time.monotonic() - _last_request_ts)
        if wait > 0:
            time.sleep(wait)
    _last_request_ts = time.monotonic()


# ============================================================================
# 1단계: Reddit 공개 RSS(Atom) 수집
# ============================================================================

def _fetch_with_retry(url: str, headers: dict, max_retries: int = _MAX_RETRIES,
                      retry_on_429: bool = True) -> bytes | None:
    """공개 RSS 요청.
    - 403: 즉시 전체 수집 중단(차단 신호로 간주, 재시도/우회 안 함)
    - 429: retry_on_429=True면 지수 백오프로 재시도(최대 max_retries), 그래도 429면 중단.
           retry_on_429=False(댓글 요청)면 재시도 없이 즉시 중단.
    - 그 외 오류/네트워크 실패: None 반환(파이프라인은 계속 진행)."""
    if _BLOCK["blocked"]:
        return None
    for attempt in range(max_retries):
        _throttle()
        try:
            res = requests.get(url, headers=headers, timeout=15)
        except requests.RequestException as e:
            print(f"[fetch] 네트워크 오류 ({attempt+1}/{max_retries}): {e}")
            time.sleep(1.5 * (attempt + 1))
            continue

        if res.status_code == 200:
            return res.content
        if res.status_code == 403:
            _set_block(f"HTTP 403 Forbidden (url={url})")
            return None
        if res.status_code == 429:
            if not retry_on_429:
                _set_block(f"HTTP 429 Too Many Requests (url={url})")
                return None
            wait = 2 ** (attempt + 1)
            print(f"[fetch] 429 Too Many Requests — {wait}초 대기 후 재시도 ({attempt+1}/{max_retries})")
            time.sleep(wait)
            continue
        print(f"[fetch] HTTP {res.status_code} 응답 (url={url})")
        return None

    if retry_on_429:
        _set_block(f"HTTP 429가 {max_retries}회 연속 발생 (url={url})")
    return None


def _strip_html(raw_html: str) -> str:
    """<content type="html">의 태그를 제거하고 HTML 엔티티(&#39; 등)를 복원."""
    text = re.sub(r"<[^>]+>", " ", raw_html or "")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_noise_title(title: str) -> bool:
    return any(p.search(title or "") for p in _NOISE_TITLE_PATTERNS)


def _parse_reddit_atom(xml_bytes: bytes, subreddit: str, limit: int, apply_filter: bool = True) -> list[dict]:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f"[parse] r/{subreddit} 피드 XML 파싱 실패(차단/에러 페이지일 수 있음): {e}")
        return []
    entries = root.findall(f"{_ATOM_NS}entry")

    posts = []
    skipped = 0
    for entry in entries:
        title = (entry.findtext(f"{_ATOM_NS}title") or "").strip()
        if apply_filter and _is_noise_title(title):
            skipped += 1
            continue

        updated = (entry.findtext(f"{_ATOM_NS}updated") or entry.findtext(f"{_ATOM_NS}published") or "").strip()

        link_el = entry.find(f"{_ATOM_NS}link")
        link = link_el.get("href", "") if link_el is not None else ""

        content_raw = entry.findtext(f"{_ATOM_NS}content") or ""
        content = _FOOTER_RE.sub("", _strip_html(content_raw)).strip()

        post_id = (entry.findtext(f"{_ATOM_NS}id") or "").strip()

        posts.append({
            "post_id": post_id,
            "subreddit": subreddit,
            "title": title,
            "link": link,
            "published": updated,
            "content": content,
        })
        if len(posts) >= limit:
            break
    if skipped:
        print(f"[filter] r/{subreddit} 고정글/공지/정기스레드 {skipped}건 제외")
    return posts


def _fetch_via_oauth(subreddit: str, limit: int, client_id: str, client_secret: str, user_agent: str,
                     apply_filter: bool = True) -> list[dict] | None:
    """Reddit 공식 OAuth API로 서브레딧 게시물 수집 (키가 있을 때만 사용; 신규 발급은 사전 승인제)."""
    token_url = "https://www.reddit.com/api/v1/access_token"
    auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
    data = {"grant_type": "client_credentials"}
    headers = {"User-Agent": user_agent}

    try:
        token_res = requests.post(token_url, auth=auth, data=data, headers=headers, timeout=10)
        if token_res.status_code != 200:
            print(f"[reddit_api] OAuth 토큰 발급 실패 (HTTP {token_res.status_code}): {token_res.text[:100]}")
            return None
        access_token = token_res.json().get("access_token")
        if not access_token:
            return None
    except Exception as e:
        print(f"[reddit_api] OAuth 인증 네트워크 에러: {e}")
        return None

    api_url = f"https://oauth.reddit.com/r/{subreddit}/hot.json?limit={min(limit + 10, 100)}"
    api_headers = {
        "Authorization": f"bearer {access_token}",
        "User-Agent": user_agent,
    }

    try:
        res = requests.get(api_url, headers=api_headers, timeout=15)
        if res.status_code == 200:
            payload = res.json()
            items = payload.get("data", {}).get("children", [])
            posts = []
            for item in items:
                d = item.get("data", {})
                title = d.get("title", "").strip()
                if apply_filter and (d.get("stickied") or _is_noise_title(title)):
                    continue
                selftext = d.get("selftext", "").strip()
                created_utc = d.get("created_utc", 0)
                published = datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat() if created_utc else ""
                permalink = d.get("permalink", "")
                link = f"https://www.reddit.com{permalink}" if permalink else ""
                post_id = d.get("name") or f"t3_{d.get('id', '')}"
                posts.append({
                    "post_id": post_id,
                    "subreddit": subreddit,
                    "title": title,
                    "link": link,
                    "published": published,
                    "content": selftext or title,
                })
                if len(posts) >= limit:
                    break
            return posts
        print(f"[reddit_api] r/{subreddit} API 호출 실패 (HTTP {res.status_code})")
    except Exception as e:
        print(f"[reddit_api] r/{subreddit} API 요청 에러: {e}")
    return None


def fetch_subreddit_posts(subreddit: str, limit: int = 10, xml_bytes: bytes | None = None,
                          apply_filter: bool = True) -> list[dict]:
    """r/{subreddit} 게시물 수집.
    1) xml_bytes가 전달되면 그 XML을 그대로 파싱 (테스트용)
    2) .env에 REDDIT_CLIENT_ID / SECRET이 있으면 공식 OAuth API 우선 호출
    3) 키가 없거나 실패하면 공개 RSS/Atom(.rss)으로 수집."""
    if xml_bytes is not None:
        return _parse_reddit_atom(xml_bytes, subreddit, limit, apply_filter)

    if REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET:
        posts = _fetch_via_oauth(subreddit, limit, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET,
                                 REDDIT_USER_AGENT, apply_filter)
        if posts is not None:
            print(f"[fetch] r/{subreddit} (Reddit 공식 OAuth API로 {len(posts)}건 수집 완료)")
            return posts
        print(f"[fetch] r/{subreddit} 공식 API 실패 -> 공개 RSS 피드로 자동 우회합니다.")

    # 필터로 걸러지는 글을 감안해 넉넉히 요청 (기본 피드는 25건)
    url = f"https://www.reddit.com/r/{subreddit}/.rss?limit={min(limit + 10, 100)}"
    xml_bytes = _fetch_with_retry(url, REQUEST_HEADERS)
    if xml_bytes is None:
        reason = "직전 차단 신호로 요청 생략" if _BLOCK["blocked"] else "수집 실패"
        print(f"[fetch] r/{subreddit} {reason} — 건너뜀")
        return []
    return _parse_reddit_atom(xml_bytes, subreddit, limit, apply_filter)


# ---------------------------------------------------------------------------
# 1-2단계: 게시물별 댓글 RSS
# ---------------------------------------------------------------------------

def _norm_author(name: str) -> str:
    return re.sub(r"^/?u/", "", (name or "").strip())


def _parse_comment_atom(xml_bytes: bytes, post: dict, limit: int) -> list[dict]:
    """게시물 댓글 Atom 피드 파싱.
    가정: 게시물 자신의 entry는 id가 't3_', 댓글 entry는 id가 't1_'로 시작한다.
    't1_'가 하나도 없는데 entry가 2개 이상이면(형식 가정이 틀린 경우) 첫 entry(=게시물)만
    빼고 나머지를 댓글로 간주하며 경고를 출력한다."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f"[parse] 댓글 피드 XML 파싱 실패({post.get('post_id')}): {e}")
        return []
    entries = root.findall(f"{_ATOM_NS}entry")

    def _eid(e) -> str:
        return (e.findtext(f"{_ATOM_NS}id") or "").strip()

    candidates = [e for e in entries if _eid(e).startswith("t1_")]
    if not candidates and len(entries) > 1:
        print(f"[parse] ⚠️ {post.get('post_id')}: 't1_' 댓글 id가 없어 첫 entry를 제외한 나머지를 댓글로 간주합니다 "
              f"(형식 가정 재확인 필요)")
        candidates = entries[1:]

    comments = []
    for rank, entry in enumerate(candidates, start=1):
        author = _norm_author(entry.findtext(f"{_ATOM_NS}author/{_ATOM_NS}name") or "")
        body = _strip_html(entry.findtext(f"{_ATOM_NS}content") or "")
        if author.lower() in _BOT_AUTHORS or body.lower() in _EMPTY_BODIES:
            continue

        link_el = entry.find(f"{_ATOM_NS}link")
        link = link_el.get("href", "") if link_el is not None else ""
        published = (entry.findtext(f"{_ATOM_NS}updated") or entry.findtext(f"{_ATOM_NS}published") or "").strip()

        comments.append({
            "comment_id": _eid(entry),
            "post_id": post.get("post_id", ""),
            "subreddit": post.get("subreddit", ""),
            "post_title": post.get("title", ""),
            "author": author,
            "body": body[:MAX_COMMENT_BODY_CHARS],
            "link": link,
            "published": published,
            "feed_rank": rank,
        })
        if len(comments) >= limit:
            break
    return comments


def fetch_post_comments(post: dict, limit: int) -> list[dict]:
    """게시물 하나의 상위 댓글 수집. 403/429를 받으면 재시도 없이 전체 수집이 중단된다."""
    link = (post.get("link") or "").split("?")[0].rstrip("/")
    if limit <= 0 or "/comments/" not in link:
        return []
    # 봇/삭제 댓글이 걸러질 것을 감안해 조금 더 요청
    url = f"{link}/.rss?sort=top&limit={min(limit + 10, 100)}"
    xml_bytes = _fetch_with_retry(url, REQUEST_HEADERS, retry_on_429=False)
    if xml_bytes is None:
        return []
    return _parse_comment_atom(xml_bytes, post, limit)


# ============================================================================
# 2단계: 로컬 LLM 감정/논란 키워드 분석
# ============================================================================

REDDIT_SENTIMENT_PROMPT = """다음은 미국 Reddit r/{subreddit}에 실제로 올라온 게시물이다.
이 글이 드러내는 네티즌(대중) 여론의 감정 상태와 핵심 논란 키워드를 추출하라.

게시물 제목: {title}
게시물 본문/요약: {content}

1. sentiment: 대중의 감정 상태 — 다음 3개 중 정확히 하나만 쓸 것:
   - favorable (낙관/지지)
   - neutral (관망/사실 토론)
   - critical_anxious (불안/비난/우려)
2. key_controversy_keywords: 이 글의 핵심 논란 키워드 정확히 3개 (리스트, 원문 언어 그대로)
3. summary_ko: 이 글의 핵심 내용을 한국어 한 문장으로 요약

반드시 아래 JSON 형식으로만 답하라. 다른 설명은 절대 붙이지 마라.
{{"sentiment": "favorable|neutral|critical_anxious", "key_controversy_keywords": ["...", "...", "..."], "summary_ko": "..."}}"""

_EXPECTED_SENTIMENT_KEYS = {"sentiment", "key_controversy_keywords", "summary_ko"}
_VALID_SENTIMENTS = {"favorable", "neutral", "critical_anxious"}


def parse_sentiment_response(parsed: dict) -> dict | None:
    """call_ollama_json()이 이미 json.loads()까지 마친 dict를 받아 필수 키/값 검증.
    형식 위반이면 신뢰하지 않고 None 반환(prototype_local_expert_sources.py의
    parse_expert_response()와 같은 방어 원칙)."""
    if not isinstance(parsed, dict) or not _EXPECTED_SENTIMENT_KEYS.issubset(parsed.keys()):
        return None
    if parsed.get("sentiment") not in _VALID_SENTIMENTS:
        return None
    if not isinstance(parsed.get("key_controversy_keywords"), list):
        return None
    return parsed


# ============================================================================
# verify_model_consensus.py의 call_ollama_json()은 ADR-001 톤 라벨(label/
# evidence_quote) 스키마로 응답을 정규화하는 함수라, sentiment/key_controversy_
# keywords/summary_ko 같은 이 모듈 고유 필드에는 그대로 재사용할 수 없다(정규화
# 과정에서 유실됨). 그래서 같은 "Ollama HTTP 호출 + 코드펜스/잡설 방어 JSON 파싱"
# 패턴만 따르는 경량 버전을 이 모듈에 별도로 둔다. 제안: 나중에 ②/③ 트랙이
# verify_model_consensus.py를 손볼 일이 있으면, call_ollama_json()을 "raw JSON
# dict만 반환"하도록 리팩터링하고 label 정규화는 호출부(verify_model_consensus.py
# 자신)에서 하도록 바꾸면 이 파일의 중복을 없앨 수 있음 — 공동 소유 파일이라
# 이 프로토타입 단계에서 직접 고치지 않고 제안만 남김.
# ============================================================================

def _call_ollama_raw_json(model: str, prompt: str, timeout: int = 180) -> dict:
    import os

    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {"model": model, "prompt": prompt, "format": "json", "stream": False,
               "options": {"temperature": 0.3}}
    try:
        res = requests.post(url, json=payload, timeout=timeout)
        if res.status_code != 200:
            return {"error": f"HTTP {res.status_code}"}
        raw_text = res.json().get("response", "").strip()
        try:
            return json.loads(raw_text)
        except Exception:
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return {"error": "JSON 파싱 실패", "raw": raw_text}
    except Exception as e:
        return {"error": str(e)}


def analyze_post_sentiment(post: dict, model: str = "mistral-nemo:latest") -> dict:
    """이 모듈 고유 스키마(sentiment/key_controversy_keywords/summary_ko)를 그대로 받는다."""
    prompt = REDDIT_SENTIMENT_PROMPT.format(
        subreddit=post.get("subreddit", ""),
        title=post.get("title", ""),
        content=(post.get("content", "") or "")[:1200],
    )
    raw = _call_ollama_raw_json(model, prompt)
    validated = parse_sentiment_response(raw)
    if validated is None:
        post["sentiment"] = None
        post["key_controversy_keywords"] = []
        post["summary_ko"] = None
        post["llm_error"] = raw.get("error", "형식 검증 실패") if isinstance(raw, dict) else "형식 검증 실패"
    else:
        post["sentiment"] = validated["sentiment"]
        post["key_controversy_keywords"] = validated["key_controversy_keywords"]
        post["summary_ko"] = validated["summary_ko"]
    return post


# ============================================================================
# 오케스트레이터 + 저장
# ============================================================================

def run(subreddits: list[str], limit: int, with_llm: bool, model: str = "mistral-nemo:latest",
        xml_by_subreddit: dict[str, bytes] | None = None,
        comments_per_post: int = DEFAULT_COMMENTS_PER_POST,
        comment_posts: int = DEFAULT_COMMENT_POSTS,
        apply_filter: bool = True) -> tuple[list[dict], list[dict]]:
    """게시물 + 댓글 수집. (posts, comments) 반환."""
    _reset_block()
    print("\n" + "=" * 70)
    print("🗣️ [Reddit 공개 RSS 여론 텍스트 마이닝]")
    print(f"• 대상: {', '.join('r/' + s for s in subreddits)} (각 최대 {limit}건)")
    if comments_per_post > 0:
        print(f"• 댓글: 서브레딧당 앞 {comment_posts}개 글, 글마다 상위 {comments_per_post}개 (요청 간격 {REQUEST_DELAY_SEC:g}초)")
    else:
        print("• 댓글: 수집 안 함 (--comments 0)")
    print(f"• 고정글/AMA 필터: {'켜짐' if apply_filter else '꺼짐'}")
    print(f"• LLM 감정분석: {'실행 (' + model + ')' if with_llm else '미실행 (--with-llm 옵션 필요)'}")
    print("=" * 70)

    all_posts: list[dict] = []
    all_comments: list[dict] = []
    for sub in subreddits:
        xml_bytes = (xml_by_subreddit or {}).get(sub)
        posts = fetch_subreddit_posts(sub, limit=limit, xml_bytes=xml_bytes, apply_filter=apply_filter)
        print(f"\n[r/{sub}] 게시물 {len(posts)}건 수집")
        for idx, post in enumerate(posts):
            post["collected_at"] = datetime.now(timezone.utc).isoformat()
            if with_llm:
                post = analyze_post_sentiment(post, model=model)
                tag = post.get("sentiment") or "분석실패"
                print(f"  [{tag:<16}] {post['title'][:60]}")

            comments: list[dict] = []
            if comments_per_post > 0 and idx < comment_posts and not _BLOCK["blocked"]:
                comments = fetch_post_comments(post, comments_per_post)
                for c in comments:
                    c["collected_at"] = post["collected_at"]
                print(f"  💬 댓글 {len(comments):>2}건 ← {post['title'][:50]}")
            post["comments_collected"] = len(comments)
            all_posts.append(post)
            all_comments.extend(comments)

    if _BLOCK["blocked"]:
        print(f"\n⚠️ 수집이 중간에 중단되었습니다: {_BLOCK['reason']}")
    return all_posts, all_comments


POST_FIELDS = ["post_id", "subreddit", "title", "link", "published", "content",
               "sentiment", "key_controversy_keywords", "summary_ko",
               "comments_collected", "collected_at"]
COMMENT_FIELDS = ["comment_id", "post_id", "subreddit", "post_title", "author", "body",
                  "link", "published", "feed_rank", "collected_at"]
POST_HISTORY_FIELDS = ["collected_date"] + POST_FIELDS
COMMENT_HISTORY_FIELDS = ["collected_date"] + COMMENT_FIELDS


def _post_row(p: dict) -> dict:
    row = {k: p.get(k, "") for k in POST_FIELDS}
    row["key_controversy_keywords"] = ";".join(p.get("key_controversy_keywords") or [])
    for k in ("sentiment", "summary_ko"):
        row[k] = p.get(k) or ""
    return row


def _comment_row(c: dict) -> dict:
    return {k: c.get(k, "") for k in COMMENT_FIELDS}


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _append_history(path: Path, rows: list[dict], fieldnames: list[str], key_fields: list[str]) -> int:
    """날짜별 누적 CSV에 새 행만 추가. (key_fields 조합이 이미 있으면 건너뜀 → 같은 날 재실행해도 중복 없음)
    기존 파일의 헤더가 다르면(스키마 변경) 옛 파일을 .bak으로 보존하고 새로 시작한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_keys: set[tuple] = set()
    schema_mismatch = False
    if path.exists() and path.stat().st_size > 0:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames != fieldnames:
                schema_mismatch = True
            else:
                for r in reader:
                    existing_keys.add(tuple(r.get(k, "") for k in key_fields))
        if schema_mismatch:  # 파일 핸들을 닫은 뒤에 이름 변경(Windows 호환)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            bak = path.with_name(f"{path.stem}.{stamp}.old{path.suffix}")
            path.rename(bak)
            print(f"[history] 헤더가 달라 기존 파일을 보존했습니다: {bak.name}")

    new_rows = [r for r in rows if tuple(r.get(k, "") for k in key_fields) not in existing_keys]
    write_header = not path.exists() or path.stat().st_size == 0
    if new_rows or write_header:
        with open(path, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            if write_header:
                writer.writeheader()
            writer.writerows(new_rows)
    return len(new_rows)


def save_results(posts: list[dict], comments: list[dict] | None = None,
                 data_dir: Path | str | None = None) -> tuple[Path, Path]:
    """최신본 저장 + 날짜별 누적. data_dir를 주면 그 경로에만 쓴다(self-test용)."""
    comments = comments or []
    out_dir = Path(data_dir) if data_dir else DATA_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    hist_dir = out_dir / "history"

    csv_path = out_dir / "reddit_opinion_latest.csv"
    json_path = out_dir / "reddit_opinion_summary.json"
    comments_path = out_dir / "reddit_comments_latest.csv"

    post_rows = [_post_row(p) for p in posts]
    _write_csv(csv_path, post_rows, POST_FIELDS)
    print(f"\n✓ 게시물 CSV 저장 완료: {csv_path} ({len(posts)}건)")

    comment_rows = [_comment_row(c) for c in comments]
    if comment_rows:  # 이번에 댓글을 못 모았으면(차단/옵션 끔) 직전의 좋은 데이터를 지우지 않음
        _write_csv(comments_path, comment_rows, COMMENT_FIELDS)
        print(f"✓ 댓글 CSV 저장 완료: {comments_path} ({len(comments)}건)")

    by_subreddit: dict[str, dict] = {}
    for sub in sorted({p["subreddit"] for p in posts}):
        sub_posts = [p for p in posts if p["subreddit"] == sub]
        sentiments = [p.get("sentiment") for p in sub_posts if p.get("sentiment")]
        keyword_counter = Counter()
        for p in sub_posts:
            keyword_counter.update(p.get("key_controversy_keywords") or [])

        by_subreddit[sub] = {
            "total_posts": len(sub_posts),
            "analyzed_posts": len(sentiments),
            "comments_collected": sum(1 for c in comments if c.get("subreddit") == sub),
            "sentiment_distribution": dict(Counter(sentiments)),
            "top_controversy_keywords": [kw for kw, _ in keyword_counter.most_common(10)],
        }

    now = datetime.now(timezone.utc)
    summary = {
        "generated_at": now.isoformat(),
        "total_posts": len(posts),
        "total_comments": len(comments),
        "subreddits": by_subreddit,
    }
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ 요약 JSON 저장 완료: {json_path}")

    # 날짜별 누적 (UTC 수집일 기준)
    def _with_date(row: dict) -> dict:
        r = dict(row)
        r["collected_date"] = (row.get("collected_at") or now.isoformat())[:10]
        return r

    added_posts = _append_history(hist_dir / "reddit_posts_history.csv",
                                  [_with_date(r) for r in post_rows],
                                  POST_HISTORY_FIELDS, ["collected_date", "post_id"])
    added_comments = _append_history(hist_dir / "reddit_comments_history.csv",
                                     [_with_date(r) for r in comment_rows],
                                     COMMENT_HISTORY_FIELDS, ["collected_date", "comment_id"])
    print(f"✓ 누적 저장: 게시물 +{added_posts}건, 댓글 +{added_comments}건 ({hist_dir})")

    return csv_path, json_path


# ============================================================================
# self-test: 네트워크/Ollama 없이 파싱·필터·중단·누적 로직 검증
#            (실제 data/reddit_signals/ 는 절대 건드리지 않는다 — 임시 폴더에만 씀)
# ============================================================================

_MOCK_POSTS_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title>geopolitics</title>
<entry>
  <title>Subreddit Rules: Must Read Before Posting</title>
  <link href="https://www.reddit.com/r/geopolitics/comments/rules01/subreddit_rules/" />
  <id>t3_rules01</id>
  <updated>2026-06-19T17:30:54+00:00</updated>
  <content type="html">&lt;p&gt;1. No Trolling&lt;/p&gt; submitted by /u/mod [link] [comments]</content>
</entry>
<entry>
  <title>I covered EU and NATO affairs for a decade. AMA on the Baltic states!</title>
  <link href="https://www.reddit.com/r/geopolitics/comments/ama001/ama/" />
  <id>t3_ama001</id>
  <updated>2026-09-14T12:20:23+00:00</updated>
  <content type="html">&lt;p&gt;Ask me anything.&lt;/p&gt; submitted by /u/journalist [link] [comments]</content>
</entry>
<entry>
  <title>US and China trade talks collapse again, tensions escalate</title>
  <link href="https://www.reddit.com/r/geopolitics/comments/abc123/us_china_trade/" />
  <id>t3_abc123</id>
  <updated>2026-09-18T10:00:00+00:00</updated>
  <content type="html">&lt;!-- SC_OFF --&gt;&lt;div&gt;&lt;p&gt;It&amp;#39;s the same every year, nothing changes.&lt;/p&gt;&lt;/div&gt;&lt;!-- SC_ON --&gt; &amp;#32; submitted by &amp;#32; &lt;a href="https://www.reddit.com/user/tester"&gt; /u/tester &lt;/a&gt; &lt;span&gt;&lt;a href="https://x"&gt;[link]&lt;/a&gt;&lt;/span&gt; &lt;span&gt;&lt;a href="https://y"&gt;[comments]&lt;/a&gt;&lt;/span&gt;</content>
</entry>
<entry>
  <title>Analysis: why the new EU-Mercosur deal actually matters</title>
  <link href="https://www.reddit.com/r/geopolitics/comments/def456/eu_mercosur/" />
  <id>t3_def456</id>
  <updated>2026-09-18T09:00:00+00:00</updated>
  <content type="html">&lt;p&gt;Interesting breakdown of the tariff schedule.&lt;/p&gt; submitted by /u/analyst [link] [comments]</content>
</entry>
</feed>"""


def _mock_comment_atom(post_id: str, comments: list[tuple[str, str, str]]) -> bytes:
    """post_id, [(comment_id, author, body_html)] -> Atom 바이트. 첫 entry는 게시물 자신(t3_)."""
    entries = [f"""<entry><title>post</title><link href="https://www.reddit.com/x/" /><id>{post_id}</id>
<updated>2026-09-18T10:00:00+00:00</updated><content type="html">&lt;p&gt;post body&lt;/p&gt;</content></entry>"""]
    for cid, author, body in comments:
        entries.append(f"""<entry><author><name>/u/{author}</name><uri>https://www.reddit.com/user/{author}</uri></author>
<title>/u/{author} on post</title><link href="https://www.reddit.com/r/geopolitics/comments/x/y/{cid[3:]}/" />
<id>{cid}</id><updated>2026-09-18T11:00:00+00:00</updated><content type="html">{body}</content></entry>""")
    return ('<?xml version="1.0" encoding="UTF-8"?><feed xmlns="http://www.w3.org/2005/Atom">'
            + "".join(entries) + "</feed>").encode("utf-8")


_MOCK_COMMENTS_BY_POST = {
    "abc123": _mock_comment_atom("t3_abc123", [
        ("t1_c1", "alice", "&lt;p&gt;Same old story, they&amp;#39;ll be back at the table in a month.&lt;/p&gt;"),
        ("t1_c2", "AutoModerator", "&lt;p&gt;Please read the rules.&lt;/p&gt;"),
        ("t1_c3", "bob", "&lt;p&gt;[deleted]&lt;/p&gt;"),
        ("t1_c4", "carol", "&lt;p&gt;Tariffs will hurt consumers first.&lt;/p&gt;"),
    ]),
    "def456": _mock_comment_atom("t3_def456", [
        ("t1_c5", "dave", "&lt;p&gt;Good analysis of the quota system.&lt;/p&gt;"),
    ]),
}


def _mock_call_ollama_raw_json(model: str, prompt: str, timeout: int = 180) -> dict:
    text = prompt.lower()
    if "trade talks collapse" in text:
        return {"sentiment": "critical_anxious",
                "key_controversy_keywords": ["trade war", "tariffs", "US-China"],
                "summary_ko": "미중 무역협상이 또 결렬되어 긴장이 고조되고 있다는 게시물."}
    if "eu-mercosur" in text:
        return {"sentiment": "neutral",
                "key_controversy_keywords": ["EU-Mercosur", "tariff schedule", "trade deal"],
                "summary_ko": "EU-메르코수르 협정의 관세 일정을 분석하는 게시물."}
    return {"sentiment": "neutral", "key_controversy_keywords": [], "summary_ko": ""}


class _FakeResp:
    def __init__(self, status_code: int, content: bytes = b""):
        self.status_code = status_code
        self.content = content
        self.text = content.decode("utf-8", errors="replace")
        self.headers: dict = {}


def _make_fake_get(calls: list[str], comment_status: int = 200):
    """requests.get 대체. 게시물 피드/댓글 피드를 모의 데이터로 응답. comment_status가 200이 아니면 댓글 요청에 그 코드를 반환."""
    def fake_get(url, headers=None, timeout=None, **kwargs):
        calls.append(url)
        if "/comments/" in url:
            if comment_status != 200:
                return _FakeResp(comment_status)
            m = re.search(r"/comments/([a-z0-9]+)/", url)
            body = _MOCK_COMMENTS_BY_POST.get(m.group(1) if m else "", b"")
            return _FakeResp(200, body)
        return _FakeResp(200, _MOCK_POSTS_ATOM.encode("utf-8"))
    return fake_get


def _snapshot_dir(d: Path) -> dict:
    if not d.exists():
        return {}
    return {str(p.relative_to(d)): (p.stat().st_mtime_ns, p.stat().st_size) for p in d.rglob("*") if p.is_file()}


def _self_test() -> bool:
    import tempfile
    import unittest.mock as mock

    print("=" * 60)
    print("🧪 self-test: fetch_reddit_opinion.py (모의 데이터 · 임시 폴더 · 실데이터 미변경)")
    print("=" * 60)
    all_ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal all_ok
        all_ok &= bool(cond)
        print(f"  {'✓' if cond else '✗'} {label}")

    this = sys.modules[__name__]
    real_before = _snapshot_dir(DATA_DIR)

    # 테스트 중에는 OAuth/딜레이/sleep을 모두 꺼서 네트워크·대기 없이 돌린다
    saved = {k: getattr(this, k) for k in ("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REQUEST_DELAY_SEC")}
    this.REDDIT_CLIENT_ID = ""
    this.REDDIT_CLIENT_SECRET = ""
    this.REQUEST_DELAY_SEC = 0
    try:
        with mock.patch.object(time, "sleep"):
            # 1) 게시물 파싱: 필터 / 엔티티 / 꼬리표 제거
            print("\n[1] 게시물 파싱")
            posts = fetch_subreddit_posts("geopolitics", limit=10, xml_bytes=_MOCK_POSTS_ATOM.encode("utf-8"))
            check(len(posts) == 2, f"고정글(Rules)·AMA 제외 후 {len(posts)}건 (기대: 2건)")
            check(posts[0]["title"].startswith("US and China trade talks collapse"), "제목 추출")
            check(posts[0]["content"] == "It's the same every year, nothing changes.",
                  f"본문 정리(태그·엔티티·꼬리표): {posts[0]['content']!r}")
            check(posts[0]["link"].endswith("/comments/abc123/us_china_trade/"), "링크(href) 추출")
            unfiltered = fetch_subreddit_posts("geopolitics", limit=10, xml_bytes=_MOCK_POSTS_ATOM.encode("utf-8"),
                                               apply_filter=False)
            check(len(unfiltered) == 4, f"--no-filter 시 {len(unfiltered)}건 (기대: 4건)")
            check(fetch_subreddit_posts("x", 5, xml_bytes=b"<html>blocked</html>") == [], "깨진 XML은 크래시 없이 빈 리스트")

            # 2) 댓글 파싱
            print("\n[2] 댓글 파싱")
            cs = _parse_comment_atom(_MOCK_COMMENTS_BY_POST["abc123"], posts[0], limit=10)
            check([c["author"] for c in cs] == ["alice", "carol"],
                  f"게시물(t3_)·AutoModerator·[deleted] 제외: {[c['author'] for c in cs]}")
            check(cs[0]["body"] == "Same old story, they'll be back at the table in a month.", "댓글 본문 정리")
            check(all(c["comment_id"].startswith("t1_") and c["post_id"] == "t3_abc123" for c in cs), "comment_id/post_id 연결")
            check(len(_parse_comment_atom(_MOCK_COMMENTS_BY_POST["abc123"], posts[0], limit=1)) == 1, "limit 적용")

            # 3) 전체 흐름(run) — requests.get 모의
            print("\n[3] run() 전체 흐름 (댓글 수집 + LLM 모의)")
            calls: list[str] = []
            with mock.patch.object(requests, "get", side_effect=_make_fake_get(calls)), \
                 mock.patch.object(this, "_call_ollama_raw_json", side_effect=_mock_call_ollama_raw_json):
                r_posts, r_comments = run(["geopolitics"], limit=10, with_llm=True, comments_per_post=15)
            check(len(r_posts) == 2 and all(p.get("sentiment") for p in r_posts),
                  f"게시물 {len(r_posts)}건 전부 감정분석 ({[p['sentiment'] for p in r_posts]})")
            check(len(r_comments) == 3, f"댓글 총 {len(r_comments)}건 (기대: 2+1=3)")
            check(sum(1 for u in calls if "/comments/" in u) == 2 and len(calls) == 3,
                  f"요청 수 {len(calls)}회 (기대: 게시물 피드 1 + 댓글 피드 2)")
            check(all(".rss" in u for u in calls), "모든 요청이 .rss 엔드포인트")
            check([p["comments_collected"] for p in r_posts] == [2, 1], "게시물별 comments_collected 기록")

            # 4) --comments 0 → 댓글 요청 없음
            print("\n[4] 댓글 끄기 / comment_posts 제한")
            calls = []
            with mock.patch.object(requests, "get", side_effect=_make_fake_get(calls)):
                p0, c0 = run(["geopolitics"], limit=10, with_llm=False, comments_per_post=0)
            check(len(p0) == 2 and c0 == [] and len(calls) == 1, f"--comments 0: 요청 {len(calls)}회, 댓글 0건")
            calls = []
            with mock.patch.object(requests, "get", side_effect=_make_fake_get(calls)):
                p1, c1 = run(["geopolitics"], limit=10, with_llm=False, comments_per_post=15, comment_posts=1)
            check(len(c1) == 2 and sum(1 for u in calls if "/comments/" in u) == 1, "comment_posts=1: 첫 글만 댓글 수집")

            # 5) 403/429 → 즉시 전체 중단
            print("\n[5] 403/429 즉시 중단")
            for status in (403, 429):
                calls = []
                with mock.patch.object(requests, "get", side_effect=_make_fake_get(calls, comment_status=status)):
                    pb, cb = run(["geopolitics", "worldnews"], limit=10, with_llm=False, comments_per_post=15)
                n_comment_calls = sum(1 for u in calls if "/comments/" in u)
                check(_BLOCK["blocked"] and n_comment_calls == 1 and cb == [],
                      f"HTTP {status}: 댓글 요청 {n_comment_calls}회 후 중단, 이후 요청 없음(총 {len(calls)}회)")
                check(len(pb) == 2, f"HTTP {status}: 중단 전에 모은 게시물 {len(pb)}건은 유지")
            _reset_block()
    finally:
        for k, v in saved.items():
            setattr(this, k, v)

    # 6) 저장 + 날짜별 누적 (임시 폴더)
    print("\n[6] 저장 / 누적 (임시 폴더)")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for i, p in enumerate(r_posts):
            p["collected_at"] = "2026-09-19T01:00:00+00:00"
        for c in r_comments:
            c["collected_at"] = "2026-09-19T01:00:00+00:00"
        csv_path, json_path = save_results(r_posts, r_comments, data_dir=tmp_dir)
        check(csv_path.exists() and json_path.exists() and (tmp_dir / "reddit_comments_latest.csv").exists(),
              "latest CSV/JSON/댓글 CSV 생성")
        summary = json.loads(json_path.read_text(encoding="utf-8"))
        check(summary["total_posts"] == 2 and summary["total_comments"] == 3
              and summary["subreddits"]["geopolitics"]["comments_collected"] == 3, "요약 JSON 집계")

        def _rows(name: str) -> list[dict]:
            with open(tmp_dir / "history" / name, newline="", encoding="utf-8-sig") as f:
                return list(csv.DictReader(f))

        check(len(_rows("reddit_posts_history.csv")) == 2 and len(_rows("reddit_comments_history.csv")) == 3,
              "history 최초 누적: 게시물 2 / 댓글 3")
        save_results(r_posts, r_comments, data_dir=tmp_dir)  # 같은 날 재실행
        check(len(_rows("reddit_posts_history.csv")) == 2 and len(_rows("reddit_comments_history.csv")) == 3,
              "같은 날 재실행해도 중복 누적 없음")
        for p in r_posts:
            p["collected_at"] = "2026-09-20T01:00:00+00:00"
        for c in r_comments:
            c["collected_at"] = "2026-09-20T01:00:00+00:00"
        save_results(r_posts, r_comments, data_dir=tmp_dir)  # 다음 날
        check(len(_rows("reddit_posts_history.csv")) == 4 and len(_rows("reddit_comments_history.csv")) == 6,
              "다음 날 실행은 날짜별로 누적(게시물 4 / 댓글 6)")
        before = (tmp_dir / "reddit_comments_latest.csv").read_text(encoding="utf-8-sig")
        save_results(r_posts, [], data_dir=tmp_dir)  # 댓글 0건 실행
        check((tmp_dir / "reddit_comments_latest.csv").read_text(encoding="utf-8-sig") == before,
              "댓글 0건 실행이 직전 댓글 latest를 지우지 않음")
        # 스키마(헤더) 변경 시 옛 파일 보존
        hp = tmp_dir / "history" / "reddit_posts_history.csv"
        hp.write_text("old_col\nx\n", encoding="utf-8")
        save_results(r_posts, r_comments, data_dir=tmp_dir)
        check(any(".old" in f.name for f in (tmp_dir / "history").iterdir()) and len(_rows("reddit_posts_history.csv")) == 2,
              "헤더가 다르면 옛 history를 .old로 보존하고 새로 시작")

    # 7) 감정 응답 검증 로직
    print("\n[7] parse_sentiment_response 방어 로직")
    cases = [
        ({"sentiment": "favorable", "key_controversy_keywords": ["a", "b", "c"], "summary_ko": "x"}, True),
        ({"sentiment": "made_up_value", "key_controversy_keywords": ["a"], "summary_ko": "x"}, False),
        ({"sentiment": "neutral", "key_controversy_keywords": "not_a_list", "summary_ko": "x"}, False),
        ({"error": "JSON 파싱 실패"}, False),
        (["not", "a", "dict"], False),
    ]
    for raw, expect_valid in cases:
        check((parse_sentiment_response(raw) is not None) == expect_valid, f"{raw}")

    # 8) 실데이터 보호
    print("\n[8] 실데이터 보호")
    check(_snapshot_dir(DATA_DIR) == real_before, f"실제 {DATA_DIR} 는 self-test 전후 동일(변경 없음)")

    print("\n" + ("✅ 전부 통과" if all_ok else "❌ 일부 실패 — 위 로그에서 어떤 단계가 깨졌는지 확인 필요"))
    return all_ok


def main():
    parser = argparse.ArgumentParser(description="Reddit 공개 RSS 기반 여론 텍스트 마이닝 도구 (게시물 + 댓글)")
    parser.add_argument("--subreddit", type=str, default=None,
                         help="단일 서브레딧 지정 (기본값: geopolitics + worldnews 둘 다)")
    parser.add_argument("--limit", type=int, default=10, help="서브레딧당 수집 게시물 수 (기본값: 10)")
    parser.add_argument("--comments", type=int, default=DEFAULT_COMMENTS_PER_POST,
                         help=f"게시물당 수집할 상위 댓글 수 (기본값: {DEFAULT_COMMENTS_PER_POST}, 0이면 댓글 수집 안 함)")
    parser.add_argument("--comment-posts", type=int, default=DEFAULT_COMMENT_POSTS,
                         help=f"서브레딧당 댓글을 가져올 게시물 수 (기본값: {DEFAULT_COMMENT_POSTS})")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY_SEC,
                         help=f"Reddit 요청 간 최소 간격(초) (기본값: {DEFAULT_DELAY_SEC:g})")
    parser.add_argument("--no-filter", action="store_true", help="고정글/AMA/정기스레드 제외 필터 끄기")
    parser.add_argument("--with-llm", action="store_true", help="로컬 Ollama로 게시물 감정/논란 키워드 분석 실행")
    parser.add_argument("--model", type=str, default="mistral-nemo:latest", help="감정분석에 쓸 Ollama 모델명")
    parser.add_argument("--self-test", action="store_true", help="네트워크/Ollama 없이 로직 검증 (실데이터 미변경)")
    args = parser.parse_args()

    if args.self_test:
        ok = _self_test()
        sys.exit(0 if ok else 1)

    global REQUEST_DELAY_SEC
    REQUEST_DELAY_SEC = max(0.0, args.delay)

    subreddits = [args.subreddit] if args.subreddit else DEFAULT_SUBREDDITS
    posts, comments = run(subreddits, limit=args.limit, with_llm=args.with_llm, model=args.model,
                          comments_per_post=max(0, args.comments), comment_posts=max(0, args.comment_posts),
                          apply_filter=not args.no_filter)
    if posts:
        save_results(posts, comments)


if __name__ == "__main__":
    main()
