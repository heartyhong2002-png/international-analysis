# 🌐 자동화 공인 벤치마크 검증 리포트 (Verified Intelligence Report)

- **생성 일시**: 2026-09-18 19:31:31
- **데이터 출처**: AllSides Official RSS (`allsides.com`) & 글로벌 뉴스
- **검증 엔진**: 3대 오픈소스 LLM 앙상블 (`mistral:latest`, `qwen2.5:7b`, `exaone3.5:7.8b`)
- **팩트체크 연동**: Google Fact Check Tools API (IFCN 공인 네트워크)

---

## 1. 📊 일일 검증 종합 지표
- **총 검증 기사 수**: 2건
- **외부 공인 편향(AllSides) 일치율**: **50.0%**
- **3대 모델 상호 합의율 (Consensus Rate)**: **100.0%** (만장일치 2건, 다수결 0건)

---

## 2. 📝 상세 검증 대조 카드
### [기사 1] Zelensky's strategy is national suicide
- **원문 링크**: [기사 원문 바로가기](https://www.allsides.com/news/2026-09-18-0700/ukraine-war-zelenskys-strategy-national-suicide)
- **출처 언론사**: `The Spectator World` | **AllSides 공인 편향**: `Center`
- **3대 모델 합의 판정**: **[비판적]** (상태: `UNANIMOUS`, 합의율: `100%`)
  - `mistral:latest`: **비판적** (판단 근거: "Ukraine is facing a $27 billion shortfall in defense funding.")
  - `qwen2.5:7b`: **비판적** (판단 근거: "Zelensky's strategy is national suicide")
  - `exaone3.5:7.8b`: **비판적** (판단 근거: "Zelensky's strategy is national suicide")
- **공인 기준 부합 여부**: ⚠️ 불일치 (중립 매체이나 모델이 비판으로 판정)
- **🚨 IFCN 팩트체크 결과**: 🚨 AFP Fact Check: 'Fabricated / False' (Leaked document shows Ukraine secretly agreed to c...)

### [기사 2] Zelensky sanctions press secretary who accused him of using drugs
- **원문 링크**: [기사 원문 바로가기](https://www.allsides.com/news/2026-09-18-0700/ukraine-war-zelensky-sanctions-press-secretary-who-accused-him-using-drugs)
- **출처 언론사**: `The Telegraph - UK` | **AllSides 공인 편향**: `Right`
- **3대 모델 합의 판정**: **[비판적]** (상태: `UNANIMOUS`, 합의율: `100%`)
  - `mistral:latest`: **비판적** (판단 근거: "sanctioned his former press secretary")
  - `qwen2.5:7b`: **비판적** (판단 근거: "Zelensky has sanctioned his former press secretary")
  - `exaone3.5:7.8b`: **비판적** (판단 근거: "sanctioned his former press secretary, who claimed without evidence that he had a drug habit")
- **공인 기준 부합 여부**: ✅ 일치 (당파적/비판적 프레임 부합)
- **🚨 IFCN 팩트체크 결과**: 🚨 Reuters Fact Check: 'False' (Iran has officially announced it assembled an acti...)

---

## 3. 🔍 엔지니어링 분석 및 고찰
1. **객관성 확보**: 개인 검수자의 주관적 판단을 배제하고, 미국 공인 언론 감시 기구(AllSides)의 Ground Truth 레이블과 직접 대조하여 편향 없는 성능 평가를 달성했습니다.
2. **다자간 상호 검증**: 단일 모델의 환각(Hallucination) 및 문화적 편향을 프랑스(Mistral), 중국(Qwen), 한국(EXAONE) 3개 독립 아키텍처의 다수결 합의로 완화했습니다.
3. **허위정보 차단**: IFCN 공인 팩트체크 네트워크를 연동하여 검증되지 않은 가짜 뉴스가 정세 분석 지표에 오염되는 것을 사전에 방지했습니다.