# [2단계] 싱크탱크 중심 데이터 고급화 및 Reddit 여론 마이닝 인수인계서
(PHASE2_THINKTANK_REDDIT_HANDOFF.md)

> **문서 목적**: 1단계(로컬 대시보드 확인) 완료 후, 2단계인 **"데이터 신뢰도 고급화(싱크탱크 정식 승격) 및 Reddit 여론 텍스트 마이닝 모듈 구축"**을
> 다른 Claude 세션에서 즉시 구현하고 실행할 수 있도록 설계와 실행 코드를 완벽히 정리한 가이드입니다.

---

## 1. 🎯 2단계 핵심 목표

1. **위키백과 역할 재정의**:
   - 위키백과는 사실 정보 출처가 아니라 **"대중의 관심도/검색량(트래픽 지표)"**로만 역할을 한정.
2. **글로벌 싱크탱크 3종 메인 파이프라인 정식 승격**:
   - 🇬🇧 **Chatham House** (영국 왕립국제문제연구소)
   - 🌐 **International Crisis Group** (글로벌 분쟁 위기그룹)
   - 🇺🇸 **38 North** (미국 스팀슨 센터 - 한반도/동북아)
   - 위 3대 싱크탱크의 분석 칼럼을 `run_pipeline.py`와 대시보드 메인 피드에 정식 연동하여 **전문성 100% 신뢰도 확보**.
3. **Reddit 공개 RSS 기반 미국 여론 텍스트 마이닝 모듈 신설 (`scripts/fetch_reddit_opinion.py`)**:
   - 복잡한 Reddit API 키 및 유료 결제 없이, **공개 RSS(`.rss`)** 엔드포인트를 통해 실시간 여론 수집.
   - 로컬 LLM(`mistral:latest` / `qwen2.5:7b`)으로 네티즌들의 감정(Sentiment) 및 주요 비판 대상 분석.
4. **트럼프 인텔리전스 연계 기반 마련**:
   - 향후 3단계(트럼프 정책 예측)를 위한 공식 연설 자막 텍스트 마이닝(`youtube-transcript-api`) 연계 규격 준비.

---

## 2. 🔑 외부 연동 엔드포인트 명세 (API 키 불필요, 100% 무료)

| 소스 | 연동 방식 | 엔드포인트 URL | 비용 및 키 |
| :--- | :--- | :--- | :---: |
| **Reddit Geopolitics** | 공개 RSS 2.0 | `https://www.reddit.com/r/geopolitics/.rss` | **무료 / 키 불필요** |
| **Reddit WorldNews** | 공개 RSS 2.0 | `https://www.reddit.com/r/worldnews/.rss` | **무료 / 키 불필요** |
| **Chatham House** | 공식 RSS 2.0 | `https://www.chathamhouse.org/rss` | **무료 / 키 불필요** |
| **Crisis Group** | 공식 RSS 2.0 | `https://www.crisisgroup.org/rss` | **무료 / 키 불필요** |
| **38 North** | 공식 RSS 2.0 | `https://www.38north.org/feed/` | **무료 / 키 불필요** |

*참고: Reddit RSS 요청 시 `User-Agent: InternationalAnalysisBot/1.0` 헤더를 반드시 넣어야 429 차단을 방지할 수 있습니다.*

---

## 3. 🏗️ 다음 세션에서 구현할 핵심 파일 상세

### 1) 신규 파일: `scripts/fetch_reddit_opinion.py`
미국 최대 커뮤니티인 Reddit의 지정학 토론방에서 실시간 여론을 텍스트 마이닝하고 감정 분석을 수행합니다.

* **CLI 실행 인터페이스**:
  ```bash
  python scripts/fetch_reddit_opinion.py                  # geopolitics, worldnews 기본 10건 수집 및 분석
  python scripts/fetch_reddit_opinion.py --subreddit geopolitics --limit 15
  python scripts/fetch_reddit_opinion.py --with-llm       # 로컬 Mistral/Qwen으로 톤/감정 분석 실행
  ```

* **구현 로직**:
  1. `requests.get("https://www.reddit.com/r/{subreddit}/.rss", headers={"User-Agent": "..."})`로 피드 파싱.
  2. 글 제목(`title`), 작성일(`updated`), 내용/댓글 요약(`content`), 링크(`link`) 추출.
  3. LLM 톤 분석 프롬프트:
     - 대중의 감정 상태: `favorable` (낙관/지지), `neutral` (관망/사실토론), `critical/anxious` (불안/비난/우려).
     - 핵심 논란 키워드 3개 추출.
  4. 저장 경로: `data/reddit_signals/reddit_opinion_latest.csv` 및 `reddit_opinion_summary.json`.

---

### 2) 기존 파일 개선: `scripts/prototype_local_expert_sources.py` → 정식 파이프라인 승격
* 이미 Chatham House, Crisis Group, 38 North 파싱 로직이 완성되어 있으므로:
  1. `scripts/run_pipeline.py`의 `steps`에 싱크탱크 수집 단계를 정식 추가:
     ```python
     steps.append(("글로벌 싱크탱크 전문가 분석 수집", "prototype_local_expert_sources.py", []))
     ```
  2. `scripts/build_database.py`에서 `load_expert_analysis_extractions()`가 이미 MySQL에 적재 중이므로, 대시보드(`scripts/generate_dashboard_v2.py`)의 피드 상단에 **[전문가 분석 (Think Tank)] 뱃지**를 최우선 노출하도록 정렬 쿼리 보정.

---

## 4. 🚀 다음 세션 작업 체크리스트 (Action Items)

새 세션이 열리면 아래 3단계를 순서대로 진행해 달라고 요청하시면 됩니다:

- [ ] **작업 1**: `scripts/fetch_reddit_opinion.py` 작성 및 `r/geopolitics/.rss` 수집 테스트 (`python scripts/fetch_reddit_opinion.py`).
- [ ] **작업 2**: `scripts/run_pipeline.py`에 싱크탱크 수집기(`prototype_local_expert_sources.py`)를 정식 파이프라인 단계로 등록.
- [ ] **작업 3**: `output/dashboard/index.html` 대시보드에 싱크탱크 및 Reddit 여론 요약 카드가 정상 노출되는지 검증.
- [ ] **작업 4**: `git add . && git commit -m "feat: implement Phase 2 think tank promotion and reddit opinion mining" && git push origin main`.
