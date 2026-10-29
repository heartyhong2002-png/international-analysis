"""
sync_notion_docs.py
===================
로컬 저장소의 최신 Markdown 문서 인벤토리(MD 문서 보관소)와
지금까지의 전체 프로젝트 작업 이력(Work History & Milestone Summary)을
Notion 허브 및 하위 페이지에 동기화합니다.
"""

import os
import sys
import datetime
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

from notion_client_base import NotionClient, load_env
from publish_notion_report import markdown_to_notion_blocks

ENV_PATH = REPO_ROOT / ".env"
MD_ARCHIVE_PAGE_ID = "3eede224-b441-8099-9d96-ea7444ebbf8b"


def save_env_key(key, value):
    lines = []
    found = False
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()

    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}\n")

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    os.environ[key] = value


def build_work_history_markdown():
    """지금까지의 전체 작업 내용을 단계별·트랙별로 정리한 종합 마크다운 생성"""
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    return f"""# 📚 전체 프로젝트 작업 이력 및 현황 종합 ({today_str} 기준)

> 본 페이지는 로컬 GitHub 저장소(`PROJECT_CONTEXT.md`, `AGENT_SYNC.md`, `project-handoff.md`)의 **지금까지의 모든 작업 내역과 아키텍처 결정 사항**을 Notion 허브에서 한눈에 열람할 수 있도록 자동 동기화한 페이지입니다.

---

## 1. 프로젝트 정체성 및 피벗 요약 (Identity & Pivot)

- **현재 정체성**: 국제정세 사건을 단정적으로 예측하는 서비스가 아니라, 정부 공식 발표·독립 언론·GDELT Cloud·해협/항만·운임/보험료·Google Trends·현지 공개 여론·여론조사·거시금융 지표를 교차검증해 공급망·지정학 리스크를 조기 탐지하는 **OSINT 기반 리스크 인텔리전스 프로토타입**
- **핵심 피벗 결정**: 미래 사건 예측의 정답 정의 모호성 및 장기 검증 한계를 인식하고, 관측·검수·설명 가능한 **조기경보(Early Warning) 및 출처 간 신호 괴리율(Signal Gap) 탐지** 문제로 재설계
- **최종 산출물**: `output/dashboard/index.html` (인터랙티브 HTML 대시보드)
- **증거 산출물**: MySQL 분석·증거 뷰 12종, 정통 공문서 양식(GAO / FBI FD-1036) 2페이지 PDF 및 Word(`.docx`) 보고서, 백테스트·검수 로그

---

## 2. 단계별 핵심 작업 완료 내역 (Chronological Work Log)

### Phase 1. 기반 파이프라인 및 다국어 오픈소스 LLM 라우팅 구축 (2026-09-08 ~ 09-21)
1. **저사양(16GB RAM, CPU-only) 맞춤형 Ollama LLM 라우팅 확립 (`prototype_all_in_one.py`)**
   - `bitsandbytes` GPU 양자화 한계를 극복하고 Ollama 동적 로드 아키텍처 채택
   - 권역별 6대 네이티브 모델 배치: 영어/유럽 4대 권역(`mistral-nemo:latest`), 한국어(`exaone3.5:7.8b`), 중국어(`qwen2.5:7b`), 일본어(`dsasai/llama3-elyza-jp-8b`), 아랍어(`falcon3:7b`), 러시아어(`second_constantine/yandex-gpt-5-lite:8b`)
2. **ADR-001 3단계 휴먼인더루프(Human-in-the-Loop) 및 3대 모델 합의 검증**
   - 사건 자체의 부정성과 매체의 비판적 프레이밍(Narrative)을 분리 정의
   - Mistral-NeMo · Qwen2.5 · EXAONE 3.5 3자 다수결 합의(`scripts/validation/verify_model_consensus.py`), Google Fact Check API 연동(`verify_factcheck_api.py`), 층화 표본 검수 도구(`sample_for_review.py`) 구현
3. **공식 인텔리전스 폼 PDF/DOCX 보고서 및 초기 수집망 구축**
   - Wikipedia 관심도, FRED 경제지표, OpenSanctions, IMF 무역, 주요국 외교부(한·미·영·독 등) RSS, 싱크탱크(Chatham House, Crisis Group, 38 North), 글로벌 3대 여론조사(Pew, ECFR, Ipsos) 파이프라인 구축
   - 미국 GAO 및 FBI FD-1036 공문서 양식 2페이지 PDF(`pdf_report_generator.py`) 및 Word(`docx_report_generator.py`) 자동 생성기 완성

---

### Phase 2. 조기경보 피벗, 신호 괴리율(Signal Gap) 및 대안 여론 센서 확장 (2026-09-21 ~ 09-29)
1. **권위주의/폐쇄 국가 3자 교차 수집 및 신호 괴리율(Signal Gap) 정량화**
   - 관영 매체(TASS, 신화통신 등) ↔ 독립/망명 매체(Meduza, Iran International, Raseef22 등) 비교 수집(`fetch_signal_gap_rss.py`) 및 괴리율 산출(`analyze_signal_gap.py`)
   - 중국 등 검열 국가의 실물 불안 역추적을 위한 금융 프록시(`fetch_financial_proxy.py`) 및 공개 Telegram OSINT 크롤러(`fetch_telegram_public.py`) 구축
2. **MySQL 통합 적재 및 신호 괴리 분석 SQL View 구축 (`scripts/db/build_database.py`, `create_views.sql`)**
   - `v_signal_attention_gap`, `v_signal_tone_gap`, `v_issue_public_vs_gov_daily`, `v_issue_geopolitical_risk_matrix` 등 고급 분석 뷰 구현
3. **Reddit 429 차단 우회 5대 로컬 여론 센서 및 Google Trends 급등 탐지기 (`2026-09-29`)**
   - `scripts/collection/fetch_local_opinions.py`: 대만 PTT, 중국 핀충(Pincong), Bluesky API, 구글 로컬 뉴스 RSS, 텔레그램 OSINT 통합 수집
   - `scripts/collection/fetch_google_trends.py`: 국가별 위험 키워드 90일 대비 7일 급등률(Surge Ratio) 실시간 포착

---

### Phase 3. 해협·운임 공급망 센서 및 복수 계통 시계열 교차검증 엔진 (2026-10-02 ~ 10-04)
1. **4대 핵심 해협 및 해운·에너지 시장 프록시 수집기 (`scripts/collection/fetch_maritime_chokepoints.py`)**
   - 바브엘만데브(홍해), 호르무즈, 대만해협, 말라카해협의 우회 지연일수·전쟁보험료 할증·AIS 불확실성 모델링 및 BDRY, ZIM, FRO(유조선사), 브렌트유, WTI, 천연가스 실시간 연동
2. **GDELT Cloud v2 사건 수집 및 ±72h 시계열 교차검증기 (`scripts/analysis/cross_verify_events.py`)**
   - 단일 출처 경보 격상 금지(`single_source_elevate_forbidden = True`) 가드레일 적용
   - 지리·토픽·시간창(±72h) 일치 시에만 독립 채널(해협 센서, 운임 시장, 로컬 여론, 텔레그램)을 결합하여 `CROSS_VERIFIED`, `PARTIALLY_CONFIRMED`, `UNVERIFIED` 상태 산출
3. **교차검증 전용 MySQL 4대 테이블 & 2대 뷰 및 5대 감시축 대시보드(`Balanced Watchboard`) 구현**
   - `load_cross_verification_to_db.py`를 통해 `v_cross_verified_events_summary`, `v_chokepoint_supply_chain_radar` 뷰 연동
   - Figma 시안 기반 5대 감시축(`MARITIME`, `ENERGY`, `INFORMATION`, `FINANCE / TRADE`, `STATE / ACTOR`) 균형 레이아웃을 `output/dashboard/index.html`에 반영

---

### Phase 4. 수집 레인 아키텍처, 쿼터 안전장치, DB 증거 계층 및 Notion 연동 (2026-10-10 ~ 10-28)
1. **4대 수집 레인(FAST · CONTEXT · OPINION · BASELINE) 및 57개 스크립트 인벤토리 체계화 (`2026-10-10`)**
   - `scripts/` 하위 폴더(`collection/`, `analysis/`, `db/`, `dashboard/`, `reports/`, `validation/`, `notion/`, `archive/`) 구조 정립 및 `PYTHON_SCRIPT_INVENTORY.md`, `COLLECTION_PIPELINE_ARCHITECTURE.md` 문서화
   - 외부 보조 수집기 4종(`fetch_acled.py`, `fetch_event_registry.py`, `fetch_mediacloud.py`, `fetch_gdelt_v2_public.py`) 구축 및 ACLED·Event Registry 인증 검증 완료
2. **GDELT Cloud QU 예산 안전장치 및 백악관 공식 RSS 수집기 (`2026-10-13 ~ 10-15`)**
   - `gdelt_cloud_budget.py`: 학술 계정 월 5,000 QU 보호를 위한 로컬 월/일 상한 및 기본 비활성화(`--with-gdelt-cloud`) 적용
   - `fetch_whitehouse_official.py`: 백악관 공식 Releases RSS 우선 수집 및 사이트맵 보완 수집기 구현(`--with-whitehouse`)
3. **Source Registry YAML 초안 및 Media Cloud 공식 API 호스트 갱신 (`2026-10-28`)**
   - `config/source_registry/` 스키마 및 5종 YAML(government, expert, local_media, opinion, customs) 초안 작성
   - `fetch_mediacloud.py`를 공식 `https://search.mediacloud.org/api/` + `Authorization: Token` 방식으로 업데이트
4. **DB 증거 계층(Evidence Writer) 트랜잭션 적재기 및 공식 뷰 가드레일 (`2026-10-28`)**
   - `scripts/db/evidence_writer.py`(원자적 트랜잭션 적재, 중복 `run_key` 차단), `load_validation_audit.py`, `manage_test_fixtures.py` 구현
   - 공식 뷰 4개에서 `TEST-FIXTURE` 데이터가 운영 성과 집계에 포함되지 않도록 완벽 분리
5. **HTML 대시보드 OSINT 표현 교정 및 강송희 교수님 연구 프로젝트 공간 분리 (`2026-10-28`)**
   - 대시보드 Information 축의 과장된 문구("국민 체감 불안도", 하드코딩 Critical 배지 등)를 "공개 온라인 정보환경 신호"로 교정 완료
   - 연구실 프로젝트 전용 폴더(`prof_kang_project/`)와 4대 템플릿을 구축하여 개인 포트폴리오와 명확히 분리
6. **Notion 4대 자동화 연동 및 전체 작업 내용 동기화 (`2026-10-28`)**
   - `scripts/notion/` 모듈을 통해 ① `AGENT_SYNC.md` 작업 보드 DB 자동 동기화, ② 최신 조기경보 리포트 블록 변환 퍼블리싱, ③ `MD 문서 보관소` 최신 파일 목록 업데이트, ④ 본 `전체 프로젝트 작업 이력` 페이지 자동 동기화 체계 구축 완료
7. **신호 괴리(Signal Gap) 정규화 및 `tev1` 10건 산식 불일치(Discrepancy) 감사 완료 (`2026-10-29`)**
   - `scripts/analysis/analyze_signal_gap.py`: 복합 인용문 리스트 정규화(`_normalize_evidence_phrases`) 및 비정치·문화·스포츠 기사 오탐 차단 프롬프트(`_build_news_digest`) 적용
   - `scripts/validation/backtest_tev1.py`: 5대 핵심 감시축 10건 시간 동결(time-frozen) 사례 확장 및 결정론적 `Risk Signal Score` 산식 vs `tev1` 판정 불일치 자동 감사 완료 (일치 5건·불일치 5건; 단일 출처 `UNVERIFIED` 가드레일 및 `CROSS_VERIFIED` 과민 반응 방어 실증)

---

## 3. 현재 대기 중이거나 이어서 진행할 다음 작업 (Next Steps)

1. **LLM 분석 · 경보 산식 DB 증거 계층 연결**: `analyze_signal_gap.py` 및 점수 산출 파이프라인이 `scripts/db/evidence_writer.py`(`save_scoring_run`)를 호출해 공식 경보 스냅샷을 누적하도록 연동
2. **대시보드 근거 추적 강화**: `v_alert_evidence_trace` 뷰를 `alert_event_id` 기준으로 대시보드 경보 카드에 직접 연결 및 `streamlit_dashboard.py`에 5대 감시축 구조 반영
3. **수집기 Source Registry 연동**: 싱크탱크 및 정부 발표 수집기가 `config/source_registry/*.yaml` 설정을 직접 읽도록 점진적 이관
4. **백테스트 및 인간 검수 표본 확대**: `validation_backtest_log.csv` 실제 사례를 10건 이상으로 확대하고 `load_validation_audit.py`로 DB 감사 테이블에 적재
"""


def update_md_archive_page(client):
    """노션 'MD 문서 보관소' 페이지에 최신 추가된 마크다운 문서 목록이 누락되어 있으면 보강"""
    try:
        res = client.request("GET", f"/blocks/{client._clean_id(MD_ARCHIVE_PAGE_ID)}/children")
    except Exception as e:
        print(f"⚠ MD 문서 보관소 페이지 조회 실패 ({e}) - 건너뜁니다.")
        return False

    existing_texts = []
    for b in res.get("results", []):
        bt = b.get("type", "")
        rt = b.get(bt, {}).get("rich_text", [])
        text = "".join(x.get("plain_text", "") for x in rt)
        if text:
            existing_texts.append(text)

    joined_existing = "\n".join(existing_texts)
    if "NOTION_INTEGRATION_GUIDE.md" in joined_existing and "COLLECTION_PIPELINE_ARCHITECTURE.md" in joined_existing:
        print("✓ 'MD 문서 보관소' 페이지에 이미 최신 MD 문서 목록이 반영되어 있습니다.")
        return True

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    addendum_md = f"""---
## 2026-10 최신 추가 및 갱신된 문서 ({today_str} 동기화)
- docs/current/COLLECTION_PIPELINE_ARCHITECTURE.md — FAST·CONTEXT·OPINION·BASELINE 4대 수집 레인 및 Source Registry 설계
- docs/current/PYTHON_SCRIPT_INVENTORY.md — scripts/ 하위 역할별 Python 스크립트 인벤토리 및 파이프라인 호출 관계
- docs/current/ANTIGRAVITY_WHITEHOUSE_HANDOFF_PROMPT.md — 백악관 공식 RSS/사이트맵 수집기 범위 및 검증 경계 가이드
- docs/current/NOTION_INTEGRATION_GUIDE.md — Notion 작업 보드·보고서·작업 이력 자동화 연동 가이드
- config/source_registry/SCHEMA.md — 출처 레지스트리(Source Registry) 메타데이터 스키마 정의
- docs/history/PROFESSOR_LAB_MEETING_20261012.md — 지도교수님 연구실 면담 및 참여 검토 기록
- docs/advisor_meeting/PROJECT_ADVISOR_MEETING_BRIEF.md — 지도교수님 면담용 조기경보 피벗 및 아키텍처 브리프
- prof_kang_project/README.md — 강송희 교수님 연구실 프로젝트 전용 작업 공간(개인 프로젝트와 분리 운영)
"""
    blocks = markdown_to_notion_blocks(addendum_md)
    client.append_children(MD_ARCHIVE_PAGE_ID, blocks)
    print("✓ 'MD 문서 보관소' 페이지에 2026-10 신규 마크다운 문서 인벤토리 추가 완료!")
    return True


def sync_work_history_page(client, hub_page_id, history_page_id=None):
    """노션 허브 하위에 '전체 프로젝트 작업 이력 및 현황 종합' 페이지를 생성하거나 최신 내용으로 갱신"""
    md_text = build_work_history_markdown()
    blocks = markdown_to_notion_blocks(md_text)
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    title = f"📚 전체 프로젝트 작업 이력 및 아키텍처 현황 ({today_str} 최신화)"

    # 허브 하위에서 기존 작업 이력 페이지 탐색
    target_page_id = None
    if history_page_id:
        try:
            page = client.get_page(history_page_id)
            if not page.get("archived", False):
                target_page_id = page["id"]
        except Exception:
            target_page_id = None

    if not target_page_id:
        res = client.request("GET", f"/blocks/{client._clean_id(hub_page_id)}/children")
        for b in res.get("results", []):
            if b.get("type") == "child_page":
                child_title = b.get("child_page", {}).get("title", "")
                if "전체 프로젝트 작업 이력" in child_title:
                    target_page_id = b["id"]
                    break

    if target_page_id:
        print(f"🔄 기존 작업 이력 페이지({target_page_id}) 내용을 최신 상태로 업데이트합니다...")
        client.update_page(target_page_id, {"title": [{"type": "text", "text": {"content": title}}]})
        # 기존 블록 삭제 후 최신 블록 적재
        existing_children = client.request("GET", f"/blocks/{client._clean_id(target_page_id)}/children")
        for blk in existing_children.get("results", []):
            try:
                client.request("DELETE", f"/blocks/{blk['id']}")
            except Exception:
                pass
        initial_blocks = blocks[:100]
        remaining_blocks = blocks[100:]
        client.append_children(target_page_id, initial_blocks)
        while remaining_blocks:
            chunk = remaining_blocks[:100]
            remaining_blocks = remaining_blocks[100:]
            client.append_children(target_page_id, chunk)
        page_url = f"https://www.notion.so/{target_page_id.replace('-', '')}"
    else:
        print(f"🚀 Notion 허브 하위에 새 '{title}' 페이지를 생성합니다...")
        initial_blocks = blocks[:100]
        remaining_blocks = blocks[100:]
        new_page = client.create_page(
            {"page_id": client._clean_id(hub_page_id)},
            {"title": [{"type": "text", "text": {"content": title}}]},
            children=initial_blocks,
        )
        target_page_id = new_page["id"]
        while remaining_blocks:
            chunk = remaining_blocks[:100]
            remaining_blocks = remaining_blocks[100:]
            client.append_children(target_page_id, chunk)
        page_url = new_page.get("url", f"https://www.notion.so/{target_page_id.replace('-', '')}")

    save_env_key("NOTION_HISTORY_PAGE_ID", target_page_id)
    print(f"✅ 전체 작업 이력 페이지 동기화 완료! 링크: {page_url}")
    return page_url


def sync_docs():
    env = load_env()
    client = NotionClient()
    ok, msg = client.test_connection()
    if not ok:
        print(f"❌ Notion 연결 실패: {msg}")
        return False

    hub_page_id = env.get("NOTION_HUB_PAGE_ID", "3eede224b44181f0bd20ea55620bf5c4")
    history_page_id = env.get("NOTION_HISTORY_PAGE_ID", "")

    update_md_archive_page(client)
    sync_work_history_page(client, hub_page_id, history_page_id)
    return True


if __name__ == "__main__":
    sync_docs()
