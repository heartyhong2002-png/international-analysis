# 🌐 자동화 공인 벤치마크 검증 리포트 (Verified Intelligence Report)

- **생성 일시**: 2026-09-19 00:14:35
- **데이터 출처**: AllSides Official RSS (`allsides.com`)
- **검증 엔진**: 3대 오픈소스 LLM 앙상블 (`mistral-nemo:latest`, `qwen2.5:7b`, `exaone3.5:7.8b`)
- **팩트체크 연동**: 미실행 (--with-factcheck 옵션 필요)

> ⚠️ **컨트롤타워 주석**: "외부 공인 편향(AllSides) 일치율"은 매체 성향과 개별 기사 논조 간의
> 느슨한 상관관계 지표이며, 모델 정확도를 보장하는 엄밀한 정답률이 아닙니다. 세부 근거는
> `scripts/auto_benchmark_verifier.py` 상단 docstring 참고.

---

## 1. 📊 일일 검증 종합 지표
- **총 검증 기사 수**: 4건
- **외부 공인 편향(AllSides) 일치율**: **100.0%** (4/4건, 채점불가 0건 제외)
- **3대 모델 상호 합의율 (Consensus Rate)**: **100.0%** (만장일치 100.0%, 다수결 0.0%)

---

## 2. 📝 상세 검증 대조 카드
### [기사 1] Opposition slams administration's chaotic handling of border crisis
- **출처 언론사**: National Review | **AllSides 공인 편향**: `Right`
- **3대 모델 합의 판정**: `[비판적]` (합의율: 100%, 상태: UNANIMOUS)
  - `mistral-nemo`: 비판적 (근거: "blasted / condemned")
  - `qwen2.5`: 비판적 (근거: "blasted / condemned")
  - `exaone3.5`: 비판적 (근거: "blasted / condemned")
- **공인 기준 부합 여부**: ✅ 일치 (외부 공인 기준 검증 성공)
- **원문 링크**: https://example.com/article-1

### [기사 2] US inflation data released, Fed signals rates to remain steady
- **출처 언론사**: Reuters | **AllSides 공인 편향**: `Center`
- **3대 모델 합의 판정**: `[중립적]` (합의율: 100%, 상태: UNANIMOUS)
  - `mistral-nemo`: 중립적 (근거: "특별한 편향 표현 없음, 사실 전달형")
  - `qwen2.5`: 중립적 (근거: "특별한 편향 표현 없음, 사실 전달형")
  - `exaone3.5`: 중립적 (근거: "특별한 편향 표현 없음, 사실 전달형")
- **공인 기준 부합 여부**: ✅ 일치 (외부 공인 기준 검증 성공)
- **원문 링크**: https://example.com/article-2

### [기사 3] South Korea and US celebrate landmark trade partnership agreement
- **출처 언론사**: Yonhap | **AllSides 공인 편향**: `Center`
- **3대 모델 합의 판정**: `[우호적]` (합의율: 100%, 상태: UNANIMOUS)
  - `mistral-nemo`: 우호적 (근거: "praised / historic")
  - `qwen2.5`: 우호적 (근거: "praised / historic")
  - `exaone3.5`: 우호적 (근거: "praised / historic")
- **공인 기준 부합 여부**: ✅ 일치 (외부 공인 기준 검증 성공)
- **원문 링크**: https://example.com/article-3

### [기사 4] Editorial: opposition party's reckless spending betrays working families
- **출처 언론사**: MSNBC | **AllSides 공인 편향**: `Left`
- **3대 모델 합의 판정**: `[비판적]` (합의율: 100%, 상태: UNANIMOUS)
  - `mistral-nemo`: 비판적 (근거: "blasted / condemned")
  - `qwen2.5`: 비판적 (근거: "blasted / condemned")
  - `exaone3.5`: 비판적 (근거: "blasted / condemned")
- **공인 기준 부합 여부**: ✅ 일치 (외부 공인 기준 검증 성공)
- **원문 링크**: https://example.com/article-4

