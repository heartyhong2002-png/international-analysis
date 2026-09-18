# AllSides 공인 벤치마크 및 Google Fact Check 자동 연동 파이프라인 인수인계 가이드
(AUTO_BENCHMARK_VERIFICATION_HANDOFF.md)

> **문서 목적**: 다른 Claude 세션(또는 개발자)이 이 문서를 보고 즉시 `scripts/auto_benchmark_verifier.py`를
> 구현하고 실행할 수 있도록, 아키텍처·수집 엔드포인트·검증 알고리즘·보고서 템플릿을 완벽히 정리한 지침서입니다.

---

## 1. 🎯 개발 배경 및 목표

* **문제점**: 개인이 수동으로 기사를 복사·붙여넣기 하거나 주관적으로 톤(비판/중립/우호)을 라벨링하면 전문성 시비가 발생하고 유지보수가 불가능함.
* **해결책**:
  1. 외부 공인 기관인 **AllSides의 공식 RSS**에서 이미 [Left / Center / Right]로 공인 분류된 기사를 매일 자동 수집.
  2. 수집된 기사를 로컬 **3대 오픈소스 LLM 앙상블(Mistral, Qwen, EXAONE)**에 입력하여 다수결 합의(Consensus) 도출.
  3. AllSides의 공인 편향과 우리 모델의 톤 판정이 일치하는지 자동 채점 (Accuracy 계산).
  4. **Google Fact Check Tools API**를 실시간 조회하여 해당 이슈에 대한 허위정보/루머 판정 결과 자동 첨부.
  5. 최종 결과를 마크다운 검증 보고서(`reports/verified_intelligence_YYYYMMDD.md`)로 자동 발행.

---

## 2. 🔑 외부 서비스 연동 명세 (API 키 & 가입 여부)

| 소스 | 연동 엔드포인트 | API 키 필요 여부 | 가입 필요 여부 | 비고 |
| :--- | :--- | :---: | :---: | :--- |
| **AllSides RSS** | `https://www.allsides.com/rss/news` | ❌ **불필요 (무료)** | ❌ **불필요** | 각 기사 태그에 언론사명 및 Bias(Left, Center, Right) 포함 |
| **글로벌 싱크탱크** | `https://www.chathamhouse.org/rss`<br>`https://www.crisisgroup.org/rss`<br>`https://www.38north.org/feed/` | ❌ **불필요 (무료)** | ❌ **불필요** | 전문가 정세 분석 칼럼 실시간 수집 |
| **Google Fact Check** | `https://factchecktools.googleapis.com/v1alpha1/claims:search` | ⚠️ **선택 사항**<br>(무료 API 키) | ⚠️ **선택 사항**<br>(Google 계정) | 키가 없어도 기존 `scripts/verify_factcheck_api.py`의 고신뢰 오프라인 캐시 모드로 100% 정상 작동 |

---

## 3. 🏗️ 구현할 파일 및 아키텍처: `scripts/auto_benchmark_verifier.py`

### 1) 입력 및 인자 정의 (CLI)
```bash
python scripts/auto_benchmark_verifier.py                # AllSides 수집 -> 3대 모델 검증 -> 리포트 생성 (기본 5건)
python scripts/auto_benchmark_verifier.py --limit 10     # 검증 기사 수 지정
python scripts/auto_benchmark_verifier.py --with-factcheck # Google Fact Check 연동 포함
python scripts/auto_benchmark_verifier.py --self-test    # 모의 데이터로 파이프라인 무결성 단위 테스트
```

### 2) 파이프라인 단계별 구현 상세

#### 1단계: AllSides RSS 자동 수집 (`fetch_allsides_feed()`)
- `feedparser` 또는 `urllib.request` + `xml.etree.ElementTree` 사용.
- RSS 항목에서 추출할 필드:
  - `title`: 기사 제목
  - `link`: 원문 URL
  - `summary` or `description`: 요약문
  - `source_outlet`: AllSides에서 명시한 언론사 (예: National Review, CNN, BBC)
  - `allsides_bias`: AllSides의 공인 편향 태그 (Left / Lean Left / Center / Lean Right / Right)

#### 2단계: 3대 오픈소스 LLM 다자간 교차 판정 (`evaluate_multi_model_consensus()`)
- 기존에 검증 완료된 `scripts/verify_model_consensus.py`의 로직 및 함수 재사용:
  - `mistral:latest` (서방 시각)
  - `qwen2.5:7b` (아시아/글로벌 시각)
  - `exaone3.5:7.8b` (한국 시각)
- 동일한 ADR-001 프롬프트(Narrative 비난 여부)로 판정 후 다수결 합의(`consensus_label`, `agreement_ratio`) 산출.

#### 3단계: 공인 성향 vs 모델 판정 자동 대조 (Match Scoring)
- **비교 규칙**:
  - AllSides가 `Right` 또는 `Left`이고 공격적인 어조인 경우 → 모델 합의가 `비판적(critical)`이면 정답(Match).
  - AllSides가 `Center`이고 정책/통계 전달인 경우 → 모델 합의가 `중립적(neutral)`이면 정답(Match).
  - 외교 협정/성과 찬사인 경우 → 모델 합의가 `우호적(positive)`이면 정답(Match).
- 최종 **"외부 공인 벤치마크 일치율(Benchmark Accuracy %)"** 계산.

#### 4단계: Google Fact Check 자동 대조 (`check_factcheck_claims()`)
- 기존 `scripts/verify_factcheck_api.py`의 `search_google_factcheck(query)` 함수를 호출하여, 기사 제목의 핵심 키워드로 등록된 IFCN 판정(False, Misleading 등)이 있는지 조회 후 첨부.

#### 5단계: 마크다운 검증 보고서 자동 생성 (`generate_verification_report()`)
- 저장 경로: `reports/verified_intelligence_YYYYMMDD.md`
- 저장 데이터: `data/auto_benchmark_results.csv`

---

## 4. 📄 출력 보고서 템플릿 (`reports/verified_intelligence_YYYYMMDD.md`)

```markdown
# 🌐 자동화 공인 벤치마크 검증 리포트 (Verified Intelligence Report)

- **생성 일시**: YYYY-MM-DD HH:MM:SS
- **데이터 출처**: AllSides Official RSS (`allsides.com`) & 글로벌 싱크탱크
- **검증 엔진**: 3대 오픈소스 LLM 앙상블 (`mistral:latest`, `qwen2.5:7b`, `exaone3.5:7.8b`)
- **팩트체크 연동**: Google Fact Check Tools API (IFCN 공인 네트워크)

---

## 1. 📊 일일 검증 종합 지표
- **총 검증 기사 수**: N건
- **외부 공인 편향(AllSides) 일치율**: **XX.X%**
- **3대 모델 상호 합의율 (Consensus Rate)**: **XX.X%** (만장일치 XX%, 다수결 XX%)

---

## 2. 📝 상세 검증 대조 카드
### [기사 1] {기사 제목}
- **출처 언론사**: {언론사} | **AllSides 공인 편향**: `{Left / Center / Right}`
- **3대 모델 합의 판정**: `[{우호적 / 중립적 / 비판적}]` (합의율: {3/3 or 2/3})
  - `mistral`: {라벨} (근거: "{인용구}")
  - `qwen2.5`: {라벨} (근거: "{인용구}")
  - `exaone`: {라벨} (근거: "{인용구}")
- **공인 기준 부합 여부**: ✅ 일치 (외부 공인 기준 검증 성공)
- **🚨 IFCN 팩트체크 결과**: {없음 or "FALSE - FactCheck.org 검증"}
```

---

## 5. 🚀 다음 세션 작업 체크리스트 (Action Items)

새 세션에서 이 작업을 진행할 때는 아래 순서로 실행하면 됩니다:
1. `scripts/auto_benchmark_verifier.py` 파일 생성 및 구현.
   - `urllib.request`로 `https://www.allsides.com/rss/news` 파싱 구현.
   - `scripts/verify_model_consensus.py` 및 `scripts/verify_factcheck_api.py` 함수 임포트 연동.
2. `python scripts/auto_benchmark_verifier.py --limit 3`으로 소량 테스트 실행.
3. 생성된 `reports/verified_intelligence_YYYYMMDD.md` 확인.
4. Git 커밋 및 푸시.
