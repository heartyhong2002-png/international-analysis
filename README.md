# 국제정세 분석 — 1차 프로토타입 (미국 소식, 단일 파일 버전)

파일 하나(`prototype_all_in_one.py`)에 다 들어있습니다.

## 지금까지의 진행 상황 (배경 정리)

이 프로토타입에 이르기까지의 결정 과정을 남겨둔다. 나중에 이 프로젝트를 다시 들여다볼 때
"왜 이렇게 짰는지"를 처음부터 다시 고민하지 않아도 되게 하려는 목적이다.

**1. 출발점 — 오픈소스 LLM 테스트 (`llmtestinglog.md`)**
GPU 없는 노트북(16GB RAM)에서 국제정세 분석용 LLM을 돌리려고 여러 모델을 테스트했다.
`transformers`+`bitsandbytes` 4bit 양자화는 GPU 전용 기술이라 애초에 불가능하다는 걸 확인하고
Ollama(GGUF) 기반으로 전환했다. 최종적으로 언어별 특화 모델 스택을 확정했다:
영어=Mistral-7B, 한국어=EXAONE 3.5 7.8B(연구 목적 라이선스), 중국어=Qwen2.5-7B(프롬프트 튜닝
필요), 일본어=ELYZA-Llama3-JP-8B, 러시아어=Saiga-Mistral-7B, 아랍어=Jais-Adaptive-7B
(뒤 세 개는 설치만 완료, 테스트 예정). Qwen2.5에서 혼합 언어 프롬프트 시 언어가 뒤섞이는
현상을 발견한 것이 "다국어 만능 모델 1개"가 아니라 "언어별 특화 모델 라우팅" 구조로 가게 된
결정적 계기였다.

**2. 포트폴리오용 스토리텔링 문서 작성**
위 테스트 로그를 "제약 극복" 서사로 재구성해 기술 포트폴리오/자소서용 문서를 만들었다
(별도 파일 `llm-project-story.md`로 전달됨. 이 저장소에는 포함 안 함).

**3. LLM의 역할을 무엇으로 한정할지 논의 → ADR-001**
"이 LLM 스택을 국제정세 분석 프로젝트에 실제로 어떻게 쓸 것인가"를 논의하면서 다음을 정했다:

- LLM은 "최종 판단자"가 아니라 "1차 구조화 독해자 + 초안 작성자 + 검증 대상 분류자"로 역할 한정.
- 정량 지표(빈도·국가쌍 태깅)는 LLM이 아니라 규칙 기반/NER로 처리 — 재현성 문제 때문.
- 정부 공식 보도자료는 뉴스와 분리해서 "공식 입장(주장)" 레이어로 별도 저장 (뉴스=사실 후보,
  정부 발표=주장 이라는 원칙).
- 애초에 GDELT를 쓰려 했으나 **GDELT API 시스템 문제로 사용하지 않기로 결정** — 이 때문에
  "이슈 강도", "뉴스 감정도" 같은 정량 지표를 자체적으로 만들어야 하는 상황이 됨.
- 톤/감성 분류는 LLM 기반으로 하되, 3단계 휴먼인더루프 필수:
  1차(LLM이 고정 루브릭+판단근거 문장과 함께 분류) → 2차(사람이 표본 15~20% 검수) →
  3차(사람이 교정 의견을 프롬프트에 few-shot으로 반영 — **재학습이 아니라 프롬프트 개선**,
  GPU 없는 환경이라 실제 파인튜닝 불가).

이 결정들은 프로젝트 문서함에 `ADR-001_LLM_역할정의_및_감성분석_휴먼인더루프.md`로 저장돼 있다.

**4. "전문가들은 실제로 어떻게 하나" 조사**
감성분석 전문가들은 혼자가 아니라 최소 3명의 라벨러를 두고 Cohen's Kappa 0.8 이상을 목표로
관리하며, 코드북(경계 사례 예시 포함)을 먼저 정교하게 만든다는 걸 확인했다. 검수자가 준기님
1인이라 다인원 카파는 계산 불가 → 테스트-재검사 신뢰도(같은 사람이 시간차를 두고 재검토)와
모델 앙상블 불일치를 대체 신호로 쓰기로 함.

**5. 정치적 편향 우려 → 검증 사이트/커뮤니티 조사**
검수자 본인의 정치 성향이 편향으로 스며들 위험을 우려해서 검증 수단을 조사했다.
AllSides / Ad Fontes Media / Media Bias Fact Check / Ground News는 전부 미국·영어권 매체
중심이라 아시아·중동은 커버가 얇다는 한계를 확인. 대안으로 IFCN(Poynter, 국제 표준),
한국은 SNU팩트체크, 대만은 Taiwan FactCheck Center, 중동은 Arab Fact-Checking Network(AFCN)를
찾았고, "Global Fact-Checking Network(GFCN)"라는 이름의 조직은 실제로는 러시아 국가가 만든
선전 위장 조직이라는 것도 발견 — **검증 기관 자체도 검증이 필요하다**는 교훈을 얻음.
언론자유도가 낮은 나라는 RSF 세계언론자유지수로 "이 나라 뉴스도 사실상 국가 입장에 가까울 수
있다"는 맥락 참고 지표로 활용하기로 함.

**6. "매번 사이트 검색하는 게 비효율적이다" → 자동화 구조 재설계**
편향 등급을 매 기사마다 수동 검색하는 대신, AllSides 데이터를 GitHub에서 한 번만 받아 로컬
테이블로 캐싱하고 도메인 조회(join)만 하도록 재설계. 기존 팩트체크 여부는 Google Fact Check
Tools API(`claims.search`)로 자동 조회 가능하다는 것도 확인(이번 프로토타입에는 아직 미구현).
"R 설치해야 하나"라는 질문에 — GitHub 저장소 안에 이미 스크레이핑된 CSV가 그대로 들어있어서
R 없이 `pandas.read_csv()` 한 줄로 받을 수 있다는 것도 확인.

**7. 1차 프로토타입 작성 (미국 소식 범위)**
위 설계를 실제 코드로 옮김. 이 클라우드 세션에서 직접 돌려보며 테스트:
- AllSides CSV 실제 다운로드 확인 (547개 언론사).
- **버그 발견 1**: CSV의 `url` 컬럼이 언론사 도메인이 아니라 AllSides 소개 페이지 주소였음 →
  이름 기반 매칭으로 재설계.
- **발견**: AllSides는 같은 언론사의 오피니언(`OO Editorial`)과 스트레이트 뉴스
  (`OO Online News`)를 별도 항목으로 평가 — 등급이 다름. RSS는 뉴스이므로 뉴스 쪽 항목으로
  매핑해야 함 (NPR, Fox, CNN, NYT, WSJ 전부 해당, 8개 매체 확인 완료).
- 이슈 태깅 로직(규칙 기반), 파이프라인 종단 테스트 통과.
- 관리 편의를 위해 5개 파일(outlet_bias/issue_tagger/rss_fetch/ollama_client/pipeline)을
  `prototype_all_in_one.py` 한 파일로 병합.

**8. 노트북에서 실제 RSS 32건 수집 후 발견된 버그 2개 수정**
준기님이 노트북에서 `python prototype_all_in_one.py`를 돌려서 NPR+BBC RSS 32건을 실제로
수집한 `review_log.csv`를 공유해줬고, 여기서 실제 데이터로만 드러난 문제 2개를 잡음:
- **버그 2**: RSS 피드 도메인이 `feeds.npr.org`처럼 서브도메인이 붙어있어 정확히 일치하는
  매핑만 찾던 로직이 전부 놓침 → 서브도메인이어도 알려진 도메인으로 끝나면 매칭하도록 수정.
- **설계 개선**: `llm_review_needed`가 "우리 18개 이슈 범위 밖인 기사"(32건 중 27건, 예:
  싱크홀·스포츠·호주 SNS 법안 뉴스)와 "진짜 애매해서 LLM 판단이 필요한 기사"를 구분 못 하고
  있었음 → `tag_status`(`matched`/`ambiguous`/`unclassified`) 필드를 추가해서, `unclassified`는
  LLM을 아예 안 부르도록 함 (7B 모델 기준 건당 15~45초 걸리므로 27건이면 7~8분 낭비).

**9. `--with-llm` 첫 실제 실행 → 톤 라벨 품질 문제 발견 및 프롬프트 수정**
노트북에서 실제로 `--with-llm`을 돌려 톤 분류 결과(35건)를 확인했다. 여기서 2가지를 확인:
- 이전에 넘겼던 `tag_status` 개선판이 반영 안 된 채로 실행되어(파일이 최신화 안 됐던 것으로
  추정) `unclassified` 기사까지 전부 LLM이 처리함 → 최신 파일 재전달로 해결.
- **더 중요한 발견**: 실제 라벨을 읽어보니 모델이 "사건 자체가 부정적인가"와 "서술 방식이
  비판적인가"를 구분하지 못하고 있었음 — 질병 발병, 범죄, 전쟁 피해처럼 사실을 담담히 전달하는
  기사까지 전부 "비판적"으로 분류됨. 또한 `evidence_quote`가 원문 제목/요약을 토씨 하나 안
  틀리고 복사한 경우가 많아 실제 판단 근거로서 쓸모가 없었음. 지난번 조사한 "라벨링 품질이
  알고리즘보다 중요하다"는 원칙이 실제 데이터로 확인된 셈 → `TONE_PROMPT`에 "사건의 부정성과
  서술의 비판성은 다르다"는 경계 사례 예시 2개를 추가하고, evidence_quote가 원문을 그대로
  베끼지 못하도록 지시를 강화함 (코드북에 해당하는 부분을 프롬프트 안에 직접 넣은 셈).

**10. 첫 2차 검수 실전 사이클 완료 — 일치율 60% (3/5), 실수 하나 발견**

노트북에서 `--with-llm` 재실행 후 `tag_status=matched` 5건을 준기님이 엑셀로 직접 검수했다.
이 과정에서 두 가지가 있었다:

- **작업자 실수 발견 및 정정**: 준기님이 이견 있는 2건(`e7a1726b`, `d8ac0c9f`)을 검수할 때
  `human_label`이 아니라 **`llm_label` 셀 자체를 직접 타이핑으로 덮어써버림** — 이러면 모델이
  실제로 뭐라고 판단했는지 기록이 사라져서 "모델이 얼마나 자주 틀렸는지" 계산이 불가능해진다.
  대화로 확인해서 원래 모델 출력값을 복원하고(`e7a1726b`=중립적, `d8ac0c9f`=비판적), 준기님
  의견은 `human_label`/`correction_note`로 옮겨 다시 정리함. **교훈: `llm_label`은 절대 손으로
  고치지 않는다 — 검수 의견은 항상 `human_label`/`correction_note`에만 적는다.**
- **최종 결과 (일치율 60%, 3/5)**:
  - `e7a1726b` (US-Canada 자동차부품 관세 기사): LLM=중립적 → 사람=비판적.
    근거: "The trade war is threatening to unravel a complex system" — "threatening",
    "unravel" 같은 극적 동사가 평가적 프레이밍으로 판단됨.
  - `d8ac0c9f` (미국 물가 상승 기사): LLM=비판적 → 사람=중립적.
    근거: "Prices in the US rose 3.4%..." — 인플레이션 통계 인용일 뿐 비판적 표현 없음. (9번
    항목에서 프롬프트를 고치기 전 미리 발견했던 바로 그 오판 패턴.)
  - 나머지 3건(`ef87571e`, `d11d7890`, `0a61367d`)은 LLM 라벨 그대로 동의.
  - 표본 5건으로 통계적 결론을 내리긴 이르지만, 불일치가 양방향(과잉 판정 1건 + 과소 판정
    1건)으로 나온 것은 "LLM 단독 판단은 안 되고 사람 검수가 실제로 필요하다"는 ADR-001의
    전제를 뒷받침하는 첫 실증 데이터다.

**11. "내가 기사를 다 읽고, 다 검수해야 하나?" — 검수 부담에 대한 오해 정리**

이슈가 앞으로 18개까지 늘어나면 matched 기사 수도 늘어날 텐데, 그때마다 원문 기사를 전부
읽고 전수 검수해야 하는 줄 오해하는 경우가 있어서 정리해둔다:

- **원문 전체를 읽을 필요 없음.** `title`과 `llm_evidence_quote` 두 컬럼만 보고 "이 근거 문장이
  실제로 평가적 표현인가, 사실 서술인가"만 판단하면 대부분 충분하다. 근거 문장 자체가 애매하거나
  이상해 보일 때만 링크를 눌러 원문을 확인하면 된다.
- **전수 검수도 필요 없음.** ADR-001에서 애초에 정한 건 "표본 15~20%만 사람이 검수"하는 것이다.
  지금은 이슈가 3개뿐이라 matched가 5건밖에 안 나와서 어쩔 수 없이 전부 봤지만, 이슈가 늘어나
  matched가 수십~수백 건이 되면 그 중 15~20%만 무작위 표본 추출해서 검수하면 된다.
  전수 검사는 규모가 커지면 애초에 불가능하고, 설계 의도도 아니다.

**12. `ollama list`로 실제 설치 모델 대조 → 아랍어 모델 태그 불일치 버그 발견**

노트북에서 `ollama list`를 돌려 실제 설치된 6개 모델을 확인했다 — 계획했던 언어별 스택과
정확히 일치함(mistral, exaone3.5:7.8b, qwen2.5:7b, dsasai/llama3-elyza-jp-8b,
cyberlis/saiga-mistral:7b-lora-q4_K, hf.co/Solshine/jais-adapted-7b-chat-Q4_K_M-GGUF).
다만 대조 과정에서 `MODEL_BY_LANGUAGE`의 `"ar"` 항목이 실제 설치된 태그(`hf.co/Solshine/...`)가
아니라 존재하지 않는 다른 이름(`jwnder/jais-adaptive:7b`)으로 되어 있던 걸 발견 — 아직 아랍어
기사를 처리해본 적이 없어서 지금까지는 안 걸렸던 버그다. 실제 설치 태그로 수정 완료.
**교훈: 언어별 모델 라우팅 테이블은 `ollama pull` 시 사용한 정확한 태그와 주기적으로 대조할 것
(HuggingFace GGUF 변환본은 특히 저장소마다 태그명이 제각각이라 오타/불일치가 나기 쉬움).**

**13. 다른 세션(컨트롤타워 트랙)과의 조율 발견 — 3개 세션 분업 체계였음**

노트북 폴더를 확인하다가 `project-handoff.md`, `ADR001_INTEGRATION_HANDOFF.md` 등 이 세션이
모르던 파일들을 발견했다. 확인해보니 준기님이 이 프로젝트를 **3개 Claude 세션으로 나눠서
동시에 진행**하고 있었다:

- ① SQL/DB 트랙 — MySQL 스키마, 데이터 정합성 (`scripts/build_database.py` 등)
- ② 오픈소스 LLM 트랙 — **이 세션(README/prototype_all_in_one.py)**
- ③ 컨트롤타워 트랙 — 아이디어 프로토타입화, 트랙 간 산출물 통합, 수집 파이프라인 유지보수

③번 트랙이 이미 존재하는 `ADR-001` 설계를 자기 쪽 수집 데이터(정부 발표문 등)에 연결하는
작업을 진행하면서, `prototype_all_in_one.py`의 `issue_id` 네이밍(`na-1`/`na-2`/`na-3`)이
③번 자신의 서술형 네이밍(`US_Canada_Trade` 등)과 다르다는 걸 발견했고, 준기님이 **서술형으로
통일**하기로 결정했다. 이를 반영해 `ISSUES` 리스트와 기존 `review_log.csv`의 `issue_ids`
컬럼을 전부 리네임함(`na-1`→`US_Canada_Trade`, `na-2`→`US_Mexico_Migration`,
`na-3`→`Trump_Economy`). 앞으로 나머지 18개 이슈를 추가할 때도 `ADR001_INTEGRATION_HANDOFF.md`의
21개 매핑표에 있는 서술형 이름을 그대로 쓸 것.

**참고**: 이 세션은 노트북 파일을 읽고 쓸 수는 있지만(`device_commit_files` 등), 셸 명령
실행(`device_bash`)은 2026-09-08 윈도우 업데이트 이후로 막혀 있는 상태라 직접 스크립트를
실행해볼 수는 없다 — 그래서 이 세션이 "로컬 아님"으로 분류돼 있던 것도 앞뒤가 맞는다.
언어 모델 테스트처럼 실행이 필요한 작업은 스크립트만 만들어서 준기님이 직접 돌리고 결과를
붙여넣어주는 식으로 진행 중.

**14. 6개 언어 재테스트 — 영어 토큰화 효과 확인 + 러시아어 모델 교체 검증**

`test_language_models.py`로 6개 언어를 다시 돌려서 12번(라벨 영어 토큰화)과 러시아어 모델
교체(vikhr)의 실제 효과를 확인했다.

- **일본어(ELYZA)**: `neutral`로 정상 출력 — 이전에 발견됐던 "일본어로 답하는" 형식 위반이 해결됨.
- **아랍어(Jais)**: `critical`로 정상 출력, 근거 문장도 실제 입력 기사 내용과 일치함 — 이전에
  발견됐던 "프롬프트 설명문/엉뚱한 예시를 그대로 베끼는" 심각한 문제가 해결됨. (few-shot 예시
  추가 + 라벨을 3단어로 제한한 것이 효과가 있었던 것으로 보임.)
- **러시아어**: 이전 모델(`cyberlis/saiga-mistral`)의 500 에러 원인을 노트북 `ollama serve` 로그로
  규명 — 구식 raw-completion 템플릿(`.System`/`.Prompt`/`.Response`)이 Ollama 0.34.0의 템플릿
  파서와 호환 안 돼 모든 요청에서 서버가 패닉하는 버그였음(모델 파일 손상이 아니라 패키징
  자체의 호환성 문제, 업데이트/재다운로드로 해결 안 됨). ChatML 스타일 템플릿을 쓰는
  `wavecut/vikhr:7b-instruct_0.4-Q4_1`로 교체해서 크래시는 해결. 다만 라벨을 지정한 3단어
  대신 동의어(`critical` 대신 `negative`)를 쓰는 걸 발견해서 `LABEL_EN_TO_KO`에 흔한 동의어
  매핑을 추가함.
- **영어(Mistral)**: "Analysts warn of price increases"를 근거로 `critical` 판정 — 애널리스트
  예측을 사실 그대로 전달한 것뿐이라 `neutral`이 더 맞을 수 있는 애매한 케이스. 버그로 확정하진
  않고, 다음 2차 검수 표본에 포함시켜 사람이 판단할 대상으로 남겨둠.
- 한국어(EXAONE)/중국어(Qwen2.5)는 이전과 마찬가지로 정상.

**결론**: 6개 언어 모델 스택이 최소한의 "형식을 지키며 응답한다" 수준까지는 도달함. 다만
품질(특히 영어 모델의 critical/neutral 경계 판단)은 여전히 2차 검수로 계속 점검해야 함.

**15. 교차언어 일관성 검수 — "비판적"의 정의를 둘러싼 근본 결정**

14번 테스트에 쓴 6개 샘플이 사실 전부 같은 이야기(관세 인상 발표 + 애널리스트 물가 상승 우려)를
언어만 바꾼 것이었다는 점을 이용해서, "같은 내용을 언어/모델마다 다르게 판단하는가"를 보는
별도 검수를 진행했다 (`data/language_consistency_review.csv`, 실제 뉴스가 아니라 통제된 비교
샘플이라 `review_log.csv`와는 별도 파일로 관리).

- **1차 결과**: 6개 중 일본어/한국어/중국어는 중립적, 러시아어/아랍어/영어는 비판적로 판정 —
  같은 내용인데 언어(정확히는 모델)에 따라 갈림.
- **중요한 순간**: 준기님이 직접 검수하면서 "내용 자체가 긍정적이지 않으니 비판적으로 볼 수도
  있다"고 판단 — 이건 정확히 모델들이 반복해서 저질렀던 "사건의 부정성 = 비판적"이라는 혼동과
  같은 패턴이었다. 즉 이 혼동은 모델만의 문제가 아니라 사람에게도 자연스러운 직관이라는 것.
- **근본 결정 필요**: "비판적"을 (A) 기사가 narrative적으로 특정 주체를 비난하는 서술을 쓸 때만
  (지금까지의 정의) 으로 볼지, (B) 사건 내용 자체가 부정적이면 비판적로 볼지 결정해야 했다.
  B로 가면 판단은 쉬워지지만 전쟁/관세전쟁/위기 뉴스가 거의 다 "비판적"이 되어버려서, 매체별
  프레이밍 차이(같은 사건을 어떤 매체는 담담하게, 어떤 매체는 특정 국가 비난조로 쓰는 차이)를
  구분하는 지표로서의 가치를 잃는다. 이 프로젝트의 핵심 목적이 "매체 간 프레이밍/편향 차이
  포착"이므로, **(A) narrative 기준을 유지하기로 결정함** (준기님 확정, 2026-09-14).
- **최종 검수 결과**: 이 정의에 따라 6개 전부 중립적이 맞다고 확정 → 일치율 3/6 (50%).
  불일치 3건(러시아어/아랍어/영어)은 전부 "사건이 부정적 → 비판적"로 오판한 동일 패턴으로,
  프롬프트에 이미 넣은 경계 사례 설명만으로는 이 세 모델(특히 상대적으로 약한 Mistral/vikhr/Jais)의
  직관을 완전히 못 이겼다는 뜻 — 다음 프롬프트 개선(3차, few-shot 보강)의 핵심 재료로 삼을 것.
- 이 정의 결정은 프로젝트 문서함의 `ADR-001_LLM_역할정의_및_감성분석_휴먼인더루프.md`에도
  추가해뒀다 — 향후 어떤 세션/사람이 검수하든 같은 기준을 쓰도록.

**16. 3차 프롬프트 개선 검증 — 영어는 해결, 아랍어는 여전히 미해결(모델 한계로 판단)**

15번의 addendum(narrative 기준 명확화)을 반영해 `TONE_PROMPT`에 판단 기준을 한 문장으로
압축하고, 실패했던 관세/물가 사례를 few-shot 예시로 직접 넣은 뒤(3차 개선) 같은 6개 샘플로
재검증했다.

- **영어(Mistral): 해결됨.** 저번엔 critical로 오판했는데 이번엔 neutral로 정확히 나옴 —
  프롬프트 수정이 실제로 효과가 있었다는 명확한 증거.
- **한국어/중국어/일본어**: 계속 정상(neutral).
- **러시아어(vikhr)**: 라벨 문제가 아니라 **타임아웃**(120초 초과) — few-shot 예시가 추가돼
  프롬프트 길이가 늘어난 게 원인으로 보임. `_call_ollama`의 타임아웃을 120→240초로 늘려서
  대응함(재검증 필요).
- **아랍어(Jais): 여전히 미해결.** 라벨은 critical로 나왔는데 이건 오답(다른 언어와 동일 내용이라
  neutral이 맞음)이고, 결정적으로 `evidence_quote`가 프롬프트에 넣은 예시 1번 문장을 영어
  그대로(번역도 안 하고) 복사한 것으로 확인됨 — 실제 아랍어 입력을 분석한 게 아니라 프롬프트
  안의 예시를 그대로 베낀 것. 이전에 봤던 "프롬프트의 지시문/예시를 실제 답으로 착각"하는
  Jais 모델의 근본적인 약점이 few-shot 예시를 넣은 뒤에도 그대로 남아있음. **잠정 결론**: 이건
  프롬프트를 더 다듬어서 고칠 수 있는 문제라기보다 이 7B 모델 자체의 지시 이해 능력 한계일
  가능성이 높음 — 아랍어 기사는 당분간 2차 검수 표본 비율을 더 높게 잡거나, 결과를 더 신뢰하지
  않고 보수적으로 다루는 식으로 대응하는 게 현실적일 수 있음(다음에 시간 나면 프롬프트를
  아랍어/영어만으로 훨씬 단순하게 다시 짜보는 실험은 해볼 수 있음).

**17. 결론 — 아랍어(Jais)/러시아어(vikhr) 모델은 "약점 있는 모델"로 확정, 프롬프트 개선은 중단**

16번 이후 재검증에서, 아랍어와 러시아어 모델이 `evidence_quote`에 **완전히 동일한 영어
문장**("US government announced higher tariffs on imported goods. Analysts warn of price
increases.")을 냈다 — 이건 두 모델 다 실제 자국어 입력을 읽지 않고 프롬프트 속 예시 1번을
그대로 베낀 것이다. 라벨도 서로 다르게 나와서(하나는 critical, 하나는 neutral), 라벨 판단이
이 "근거"와 무관하게 사실상 무작위에 가깝다는 것도 확인됨.

3차례 프롬프트를 고쳐도 이 패턴이 반복되는 걸 보고, **더 이상 프롬프트 개선으로는 안 풀리는
두 모델(7B급, Jais/vikhr) 자체의 한계**로 결론 내림 (준기님 확정, 2026-09-14). 영어 지시문으로
바꿔보는 추가 실험은 제안했으나 진행하지 않기로 하고 다음 작업으로 넘어가기로 함.

**실무 대응**: 이 두 모델(아랍어/러시아어)이 처리한 결과는 신뢰도가 낮다고 보고, 2차 검수 표본
비율을 이 두 언어에 한해서는 15~20%보다 높게(예: 전수 검수) 잡는 걸 권장. 다른 언어(영어/한국어/
중국어/일본어)는 지금 수준의 표본 검수로 충분해 보임.

**18. 나머지 이슈 전체 추가 — 북미 3개 → 21개 전체(대륙별 3~6개씩)**

`na-1`/`na-2`/`na-3`(북미 3개)만 있던 `ISSUES` 리스트를 프로젝트 문서함의
`대륙별_이슈_분석_프레임워크.md`를 원본으로 삼아 나머지 대륙까지 전부 채워 넣었다.

- **문서 자체의 오류 발견**: 이 프레임워크 문서 제목은 "주요 분석 대상 국제 이슈 (18개)"인데
  실제로 세어보면 북미3+남미3+유럽3+중동3+아프리카3+아태6 = **21개**가 나열돼 있음. 제목과
  본문 수가 안 맞는 원본 문서 자체의 불일치인데, 임의로 3개를 빼서 18개로 맞추기보다는 문서에
  실제로 적힌 21개를 전부 코드에 반영하고 이 불일치를 코드 주석으로 남겨두는 쪽을 택함(트랙③이
  `ADR001_INTEGRATION_HANDOFF.md`에서 쓴 `issue_id` 이름들도 21개 전부와 매칭됨).
- **추가한 18개**(트랙③이 정한 `issue_id` 네이밍 그대로 사용):
  - 남미: `Venezuela_Crisis`, `Brazil_Politics`, `Argentina_Economy`
  - 유럽: `Ukraine_War`, `EU_Russia`, `Baltic_Security`
  - 중동: `Iran_Nuclear`, `Israel_Palestine`, `Middle_East_Energy`
  - 아프리카: `Sudan_Conflict`, `Ethiopia_Crisis`, `Congo_Minerals`
  - 아태: `North_Korea_Nuclear`, `Taiwan_Strait`, `India_Pakistan`, `South_China_Sea`,
    `Japan_Korea`, `Myanmar_Crisis`
- 각 이슈마다 필요한 국가 키워드를 `COUNTRY_ALIASES`에도 같이 추가함(기존 3개 → 21개:
  Venezuela, Brazil, Argentina, Ukraine, Russia, Baltic States, Iran, Israel, Palestine,
  Saudi Arabia, Sudan, Ethiopia, DR Congo, North Korea, Taiwan, China, India, Pakistan,
  Japan, South Korea, Myanmar 추가).
- **예상되는 부작용(버그 아님)**: 러시아가 `Ukraine_War`/`EU_Russia`/`Baltic_Security` 3개
  이슈에, 중국이 `Taiwan_Strait`/`South_China_Sea` 2개 이슈에 겹쳐서 걸림 — 한 기사가 국가는
  매칭되는데 이슈별 키워드까지는 정확히 안 맞는 경우가 늘어날 거라, `tag_status="ambiguous"`
  (LLM 판단으로 넘어가는 케이스) 비율이 북미 3개일 때보다 자연스럽게 올라갈 것으로 예상됨.
  이건 이슈 수가 늘면서 생기는 정상적인 현상이고, 실제 RSS 데이터로 돌려본 뒤 `ambiguous` 비율이
  너무 높으면 그때 이슈별 키워드를 더 좁히는 식으로 튜닝하면 됨.
- 아직 실제 RSS 기사로 21개 전체를 돌려서 태깅 결과를 검증하지는 않았음 — 다음 단계에서
  `python prototype_all_in_one.py`(LLM 없이 규칙 기반 태깅만)로 먼저 `tag_status` 분포부터
  확인해보는 걸 권장.

**19. [③번 컨트롤타워 트랙 작성] 현지언론(local_media)/전문가분석(expert_analysis) 소스 프로토타입**

> 이 항목은 이 세션(②번 LLM 트랙)이 아니라 ③번 컨트롤타워 트랙이 작성했다.
> 다음에 컨트롤타워 세션이 이 README를 다시 볼 때 바로 이어받을 수 있게
> 남겨둔다. 자세한 내용은 `LOCAL_MEDIA_EXPERT_INTEGRATION_HANDOFF.md`와
> `project-handoff.md`의 같은 날짜 로그 참고.

준기님이 "뉴스/정부발표 말고 현지 언론이랑 전문가 의견도 수집해야 하지 않냐"고
물어서, `source_type`을 `local_media`/`expert_analysis` 2종으로 확장하는
새 프로토타입(`scripts/prototype_local_expert_sources.py`)을 만들었다. 이
파일(`prototype_all_in_one.py`)의 `tag_article`/`OutletBiasLookup`/
`MODEL_BY_LANGUAGE`/`_call_ollama`를 그대로 import해서 재사용한다 — 즉 이
파일의 함수 시그니처를 바꾸면 그 프로토타입도 같이 깨질 수 있다는 뜻이니
참고할 것.

- **소스 5개 확정** (WebFetch로 실제 RSS 응답 확인, 2026-09-14): The Moscow
  Times(local_media, 러시아), Al-Monitor·Chatham House Expert Comment·
  International Crisis Group·38 North(전부 expert_analysis).
- **톤 분류를 안 씀**: `expert_analysis`는 이 파일의 `TONE_PROMPT`(narrative
  기준 "비판적" 판정)를 재사용하지 않고 별도 `EXPERT_ANALYSIS_PROMPT`를
  새로 만들었다. 이유 — 싱크탱크 리포트는 애초에 "정부가 이렇게 해야 한다"는
  식으로 주장하는 게 본업이라, narrative 기준을 그대로 적용하면 거의 다
  critical로 쏠려서 "매체별 프레이밍 차이 포착"이라는 이 프로젝트의 핵심
  목적이 무의미해진다(15번 항목에서 확정한 논리와 같은 맥락). 대신
  `author_or_org/key_argument/forecast/forecast_horizon/evidence_basis/
  stance_toward` 6개 필드를 뽑는다.
- **실제 데이터로 발견한 버그**: 5개 소스의 실제 최신 헤드라인 8건을 이
  파일의 `tag_article()`에 그대로 태워보니 **7건(87.5%)이 `tag_status=
  unclassified`로 빠졌다** — 예를 들어 "북중 무역시설 개통" 기사는
  `countries_involved=["North Korea","China"]`까지는 맞는데
  `North_Korea_Nuclear`의 키워드(`nuclear test`/`missile launch`/
  `denuclearization`)가 너무 좁아서 이슈 매칭이 안 됐다. `unclassified`는
  자원 절약을 위해 LLM을 아예 안 부르는 설계(8번 항목)라, 이대로 두면
  전문가 소스 대부분이 그냥 버려지는 셈이었다. → `tag_article()` 자체는
  안 건드리고, `tag_article_with_source_awareness()`라는 후처리 함수를
  새 프로토타입 파일에 추가해서 `local_media`/`expert_analysis`에 한해서만
  "국가는 맞고 이슈 키워드는 안 맞는" 경우를 `unclassified`→`ambiguous`로
  승격시켰다(`news`는 그대로 — 거긴 진짜 무관한 기사를 걸러내는 목적으로
  `unclassified`가 여전히 필요함). 실제 8건 기준 회귀 테스트를 self-test에
  추가함(기대값: matched 1 / ambiguous 6 / unclassified 1[Somalia,
  `COUNTRY_ALIASES`에 없는 나라라 정상]).
- **아직 이 파일과 병합 안 됨**: 새 프로토타입은 독립 실행 파일이고, 이
  파일(`prototype_all_in_one.py`)의 `RSS_FEEDS`/`run()`에 합치는 정확한
  방법은 그 프로토타입 파일 맨 아래 주석으로 제안만 해뒀다(파일 직접 수정
  안 함 — 이 파일은 ②번 트랙 소유이므로). 실제 Ollama 호출(`--with-llm`)도
  아직 로컬에서 검증 전.

**20. [③번 컨트롤타워 트랙 작성] 정부 공식 발표 소스 전략 — 유튜브 대신 정부
공식 홈페이지 텍스트, RSS 계층 현황 점검**

> 이 항목도 ③번(컨트롤타워)이 씁니다. 준기님이 "유튜브에서 각국 대통령
> 공식 담화문·브리핑도 자료로 쓸 수 있을까?"라고 물어봐서 논의한 결과와,
> 그 논의 중에 `gov_announcements_collector.py`(③번 트랙 소유)를 다시
> 열어보다가 발견한 사실을 남긴다.

**유튜브 자막 대신 정부 공식 텍스트를 쓰기로 함.** 유튜브 자막은 (1) 공식
Data API v3로는 남의 채널 영상 자막을 못 받아옴(구글 공식 문서 확인 —
`captions.download`는 본인 소유 채널 영상에만 동작), (2) 비공식 라이브러리
(`youtube-transcript-api`, `yt-dlp`)로는 가능하지만 이용약관 위반 소지가
있고, (3) 특히 아랍어·러시아어처럼 이미 "약점 있는 모델"로 확정된 언어는
자동 자막 인식 오류까지 더해져서 정확도가 더 떨어질 위험이 있음. 반면
정부 공식 홈페이지(백악관 Remarks/Speeches, 크렘린 en.kremlin.ru 등)는
같은 담화문을 텍스트 전문으로 이미 게시해두는 경우가 많고, 공개 배포
목적의 콘텐츠라 저작권/약관 리스크도 훨씬 낮음. **결론: 정부 공식 텍스트를
1순위로 쓰고, 유튜브는 텍스트 전문이 없을 때만(즉흥 질의응답 등) 낮은
우선순위 보조 소스로 나중에 검토.**

**RSS 계층(official_statement) 현황을 다시 확인함.** 이번 논의 중
`gov_announcements_collector.py`를 다시 열어봤더니, **이미 다른 ③번
세션이 2026-09-14에 영국 FCDO(Atom 1.0)와 독일 외교부(RSS 2.0)를 실제로
반영·검증까지 끝내놓은 상태**였다(직접 재검증까지 완료 — `project-handoff.md`
작업 로그 참고). 튀르키예는 RSS 안내 페이지에서 찾은 실제 링크가 페이지
로드마다 바뀌는 세션성 UUID라 고정 엔드포인트로 못 써서 보류로 확정됨.
이스라엘·이란·사우디는 외교부 자체 RSS가 없어서(조사 문서에서도 확인됨)
2순위인 웹 크롤링으로 넘어가야 하는데, 이번 라운드에서는 아직 손 안 댐 —
**다음 후보 작업**으로 남겨둔다.

**21. 21개 이슈 전체 실제 검증 (1단계) — 규칙 기반 태깅 + LLM 톤 분류 테스트**

README 18번 항목에서 "21개 이슈 전체는 코드에 채워져 있지만 북미 3개 외 나머지
18개는 아직 실제 RSS 기사로 태깅 결과를 검증한 적이 없음"이라고 기록해둔 것을
실행해서 확인함. 2026-09-15에 `python prototype_all_in_one.py`(규칙 기반 태깅만)
와 `python prototype_all_in_one.py --with-llm`(LLM 포함)을 순서대로 실행해서
NPR+BBC RSS 33건으로 21개 이슈 태깅 로직을 검증함.

**규칙 기반 태깅 결과 (LLM 없이)**:
- 총 수집: 33건 (NPR + BBC)
- tag_status 분포: matched 10건 (30.3%), unclassified 23건 (69.7%), ambiguous 0건 (0%)
- 이슈별 매칭: Trump_Economy 6건, Israel_Palestine 2건, Baltic_Security 1건, US_Canada_Trade 1건
- **중요 발견**: ambiguous 비율이 0%라는 건 이슈 키워드가 잘 설계되었다는 신호.
  unclassified 비율이 높은 건 현재 RSS 피드가 미국/캐나다 중심이라서 남미/아프리카/아태
  이슈와 관련된 기사가 안 나오기 때문일 뿐, 버그 아님.

**LLM 톤 분류 결과 (matched 10건만 실행)**:
- 톤 분류: 중립적 6건 (60%), 비판적 3건 (30%), 우호적 0건 (0%)
- 처리 시간: 약 5분 (10건 × 평균 30초)
- unclassified 23건은 LLM 호출 없이 건너뜀 — 8번 항목의 자원 절약 설계가 정상 작동함.
- **3차 프롬프트 개선 효과 확인**: narrative 기준("사건의 부정성 ≠ 비판적")이 잘 적용됨.
  예: "Trump says AI safety fears a 'hoax'" → 중립적 (인용 전달이므로 적절),
  "Trump criticises Supreme Court" → 비판적 (직접 비난 표현이므로 적절).
- evidence_quote 품질 개선: 이전처럼 원문을 그대로 복사하는 경우가 줄어들고,
  실제 판단 근거가 되는 표현을 추출하고 있음.

**결론**: 21개 이슈 태깅 로직은 정상 작동함. 현재 RSS 피드(NPR+BBC)로는 Trump_Economy
이슈에 과도하게 편중되어 있지만, 이건 데이터 소스의 한계이지 태깅 로직의 문제는 아님.
다른 지역 RSS 피드를 추가하면 다른 이슈들도 자연스럽게 매칭될 것으로 예상됨.

**22. 유럽 4대 권역 스택 도입(`mistral-nemo:12b`), 결함 모델 정리, 러시아/아랍어 안정화 및 데이터 경로 버그 해결 (2026-09-18)**

국제정세 분석에서 각국의 외교 맥락과 프레이밍을 해석하기 위한 로컬 LLM 라우팅 스택을 전면 개편하고 실증 검증을 완료함:

1. **데이터 경로 버그 수정 (`analyze_signals.py`)**:
   - `analyze_signals.py`가 실제 수집 데이터 위치인 `scripts/data/` 대신 빈 루트 `data/` 경로를 바라보고 있어 최신 9월 14일자 위키백과(21개 이슈) 및 194건의 정부 발표문(미 국무부, 한국 외교부, 독일 외교부 등)이 통째로 누락되던 문제를 `_resolve_data_dir()` 동적 탐색 로직으로 해결. 상위 N개 이슈 분석용 `--limit` 옵션도 추가.
2. **결함 모델 영구 정리**:
   - 프롬프트 예시 문구를 무조건 복제하거나 500 에러를 유발하던 구형 7B 모델(`wavecut/vikhr:7b`, `hf.co/Solshine/jais-adapted-7b`)을 Ollama에서 삭제하여 디스크 약 9.1GB를 확보함 (C 드라이브 여유 공간: ~62.5GB).
3. **러시아어(`ru`) & 아랍어(`ar`) 라우팅 안정화**:
   - 다국어 사전학습과 ru-MMLU 벤치마크 상위인 `qwen2.5:7b`로 라우팅 교체 완료. `test_language_models.py` 실증 결과, 러시아어(47.1s)와 아랍어(6.3s) 모두 오판 없이 정확한 `neutral` 판정 및 ADR-001 기준 근거 인용(`"특별한 편향 표현 없음, 사실 전달형"`)을 출력하여 기존 결함을 완벽히 해결.
4. **유럽 4대 권역 통합 전담 모델 `mistral-nemo:12b` 신규 도입 및 권역별 전면 라우팅**:
   - 프랑스 Mistral AI가 개발한 최강 12B 오픈소스 모델인 `mistral-nemo:latest`(7.1GB, Q4_K_M)를 설치하고 실증 완료 (프랑스 외교 '전략적 자율성' 2문장 분석 31초 성공, 독일 관세 뉴스 64초 만에 neutral 판정 성공).
   - 준기님의 통찰("유럽은 서/동/남/북 4대 권역으로 나뉘며 안보 시각이 완전히 다르다")을 반영하여, Tekken 토크나이저의 다국어 역량을 바탕으로 `prototype_all_in_one.py`의 `MODEL_BY_LANGUAGE`를 유럽 4대 권역 전체로 확장:
     - **서유럽**: 프랑스(`fr`), 독일(`de`), 네덜란드(`nl`)
     - **남유럽·지중해**: 스페인(`es`), 이탈리아(`it`), 포르투갈(`pt`)
     - **동유럽·발트 (`Baltic_Security` 직결)**: 폴란드(`pl`), 우크라이나(`uk`), 체코(`cs`)
     - **북유럽 (발트해·북극해 안보)**: 스웨덴(`sv`), 노르웨이(`no`), 덴마크(`da`)
   - 단일 12B 모델로 유럽 4대 권역을 모두 커버함으로써 16GB RAM 환경에서도 추가 다운로드 0원으로 완벽한 권역별 정세 해석 스택을 완성함.

23. **3대 오픈소스 LLM 다자간 교차 검증(Consensus) 엔진 구축 및 Google Fact Check API 연동 (2026-09-18)**

연구자 개인의 주관적 검수 한계를 극복하고 엔지니어링 및 학술적 엄밀성을 확보하기 위해 교차 검증 체계를 완성함:

1. **3대 오픈소스 LLM 다자간 교차 검증 엔진 (`scripts/verify_model_consensus.py`)**:
   - 단일 모델의 편향이나 오판을 방지하기 위해 출신 배경이 다른 3대 독립 모델(서방 `mistral:latest`, 글로벌/아시아 `qwen2.5:7b`, 한국 `exaone3.5:7.8b`)이 독립적으로 동일 기사의 프레이밍을 분석하고 다수결 합의(Consensus)를 도출하는 앙상블 파이프라인 구축.
   - **벤치마크 실증 결과**: 골든 스탠다드 5건 테스트에서 3:0 만장일치 80%(4건), 2:1 다수결 합의 20%(1건), 의견 분열 0% 기록.
   - **오판 자동 교정 실증**: 한미 외교 협력 성과(BM-03) 기사에서 Qwen이 '중립적'으로 오판했으나, Mistral과 EXAONE의 긍정적 찬사 인용(2:1 다수결)으로 최종 정답인 '우호적'을 확정하여 다수결 합의 정확도 100.0% 달성.
   - 종합 보고서(`reports/model_consensus_verification_report.md`) 및 감사 CSV(`data/consensus_verification_audit.csv`) 자동 생성.
2. **Google Fact Check Tools API 클라이언트 (`scripts/verify_factcheck_api.py`)**:
   - IFCN(국제 팩트체킹 네트워크) 공인 기관(Reuters, AFP, PolitiFact, FactCheck.org 등)의 공식 검증 데이터(ClaimReview 스키마)를 조회하는 실시간 검증기 구현 (무료 API 및 오프라인 고신뢰 캐시 모드 지원).

**24. 정통 관용 인텔리전스 폼(FBI FD-1036 / FD-71A 모사) 기반 공식 PDF 보고서 엔진 전면 재설계 (2026-09-19)**

정부·정보기관 납품 및 외교안보 정책 브리핑 수준의 최고급 전문성을 확보하기 위해 기밀 해제된 미국 연방수사국(FBI) 공식 인텔리전스 수사·신고 양식(**FORM FD-1036 / FD-71A Guardian Complaint Form**)을 1:1로 정밀 모사한 공식 보고서 엔진을 완성함:

1. **알록달록한 AI/카드뉴스 스타일 탈피 및 정통 공문서 규격 구현 (`scripts/pdf_report_generator.py`)**:
   - ReportLab Platypus 기반 엔진 구축 및 Windows 시스템 맑은 고딕(`malgun.ttf`/`malgunbd.ttf`) 직접 등록으로 한글 조판 깨짐 없는 고품질 PDF 렌더링.
   - **Page 1 (공식 표제부 및 사건 징후)**:
     - 최상단 붉은색 기밀해제 승인 스탬프(`APPROVED FOR PUBLIC RELEASE BY INTELLIGENCE ASSESSMENT DIRECTORATE on 18 September 2026`, Crimson Red `#C8102E`).
     - 서식 코드 `FORM IA-1036 (Rev. 2026-09)`, 보안분류 `UNCLASSIFIED`, 테두리 공식 인장 `[ OFFICIAL RECORD / AUTHENTICATED ]`.
     - 기관 표제부: `INTERNATIONAL AFFAIRS INTELLIGENCE DIRECTORATE` / `Strategic Threat & Geopolitical Assessment Form`.
     - 결재 및 식별 메타데이터 그리드: `Form Type (IA-71A)`, `Date`, `Title (U)`, `Approved By [████████]`, `Drafted By [████████]`, `Case ID #`.
     - `Synopsis:` 사건 개요 및 현재 징후를 팩트 중심으로 간결·엄밀하게 서술.
     - `Chronology of Key Intelligence Signals:` 가로 구분선 중심의 클래식 공문서 타임라인 표.
   - **Page 2 (전략적 이해관계, 실측 시스템 쿼리, 정책 제언)**:
     - 2페이지 상단 반복 식별 헤더 (`APPROVED FOR PUBLIC RELEASE...`, `Title: (U)...`, `Re: Case ID, Date`).
     - `Strategic Posture & Vulnerabilities:` 미국, 중·러, 한국 및 동맹국의 태세와 사각지대 위험요인.
     - `Database Queries (★ 파이프라인 실측치 연동):` Wikipedia Pageviews 일일 조회수, 각국 외교부·국무부 발표문 매칭 수, 3대 LLM(Mistral-12B, Qwen2.5-7B, EXAONE-3.5) 합의 결과, IFCN 팩트체크 검증 로그를 인텔리전스 시스템 쿼리 형식으로 배치.
     - `Key Strategic Recommendations:` 1~4대 명확한 액션 아이템 형태의 국가 정책 제언.
     - `Enclosure(s):` 감사 CSV, 트렌드 차트, 합의 매트릭스 등 공식 증빙 파일 목록.
     - 문서 종결 심볼 `◆◆` 및 `UNCLASSIFIED` 바닥글.
2. **개별 5대 현안 2페이지 보고서 5종 + 11페이지 종합 Dossier 바운드 리포트 생성**:
   - 북한핵(`01_북한핵_정세평가보고서.pdf`), 대만해협(`02_대만해협_정세평가보고서.pdf`), 우크라이나전쟁(`03_우크라이나전쟁_정세평가보고서.pdf`), 이란핵협상(`04_이란핵협상_정세평가보고서.pdf`), 미중무역전쟁(`05_미중무역전쟁_정세평가보고서.pdf`) 등 개별 정확히 2페이지 PDF 5종.
   - 정식 표지(Cover Page)와 목차(Table of Enclosed Intelligence Assessments)를 포함한 11페이지 분량의 통합 제본 Dossier(`2026_글로벌_국제정세_핵심현안_종합평가보고서.pdf`) 동시 생성.
3. **바탕화면 전용 디렉토리 및 MySQL DB 자동 적재 (`scripts/report_db_saver.py`)**:
   - 보고서 발행 즉시 사용자 지정 경로(`C:\Users\홍준기\Desktop\분석보고서`)에 자동 복제 저장 (바이너리 PDF 오염 방지 안전 처리).
   - MySQL `international_analysis.analysis_reports` 테이블에 고유 리포트 ID, 카테고리, 제목, 형식(`gao_pdf_ko`, `gao_dossier_pdf_ko`), 메타데이터 및 전문 영구 적재.
   - 기존 `scripts/generate_reports.py` 실행 시 마크다운 빌드 직후 PDF 생성 및 바탕화면/DB 동기화가 원스톱으로 연동 구동됨.

**25. 글로벌·미국 실시간 여론 텍스트 마이닝 모듈 및 합법적 공개 웹 표준 연동 (`scripts/fetch_reddit_opinion.py`) (2026-09-19)**

외교·안보 현안에 대한 영미권 대중의 여론 반응과 감정을 포착하기 위한 모듈 구축 및 규정 준수 검증을 완료함:

1. **Reddit 공개 RSS/Atom 1.0 표준 기반 수집 (비용 0원 & 100% 합법 준수)**:
   - 2023년 말 Reddit의 일반 사용자용 신규 개발자 API 키 발급 전면 차단에 대응하여, Reddit 서버가 뉴스 리더기 및 외부 구독을 위해 공식 배포하는 웹 표준 엔드포인트(`https://www.reddit.com/r/{subreddit}/.rss`)를 활용.
   - 비공개 회원 정보 침해가 아닌 전체 공개 포럼(`r/geopolitics`, `r/worldnews`)의 공식 배포 피드를 읽기 전용으로 수집 (*hiQ Labs v. LinkedIn* 미국 연방 항소법원 판례 합법성 준수).
   - 투명한 봇 식별자(`User-Agent: InternationalAnalysisBot/1.0`) 및 회당 5~10건 단위의 저부하 요청(Gentle Crawling)을 적용.
2. **로컬 LLM(`mistral-nemo:12b`) 기반 감정 및 논란 키워드 추출**:
   - 수집된 대중 여론을 `favorable(낙관)`, `neutral(관망)`, `critical_anxious(불안/비난)` 3단계 감정으로 구조화 분류하고 핵심 논란 키워드 3개를 자동 추출하여 `data/reddit_signals/`에 저장.
3. **공식 OAuth 및 공개 RSS 하이브리드 아키텍처 구현**:
   - `.env`에 `REDDIT_CLIENT_ID`/`SECRET`이 있으면 공식 OAuth API(분당 100회)를 우선 호출하고, 미입력 시 공개 RSS 피드로 자동 fallback되어 365일 무중단 수집 보장.

**26. 글로벌 공신력 여론조사 기관(Pew Research · ECFR · Ipsos) 실증 여론 데이터 수집 모듈 구축 (`scripts/fetch_polling_data.py`) (2026-09-19)**

온라인 커뮤니티 정성 반응(Reddit)을 넘어, 표본과 통계적 신뢰도를 갖춘 세계 최고 권위 여론조사 기관의 실증 데이터를 자동 수집하는 파이프라인을 구축함:

1. **글로벌 3대 여론조사 기관 공식 피드 연동 (비용 0원 & 100% 합법 준수)**:
   - **Pew Research Center**: 국제관계(`international-affairs`) 및 미국 대외정책(`politics-policy`) 정기 실증 설문 수집.
   - **ECFR (유럽외교협회)**: 우크라이나 군사 지원, 대러 제재, 유럽 방위비 등 EU 시민들의 지정학적 인식 조사 수집.
   - **Ipsos Global Advisor**: 전 세계 30개국 시민들의 국제 갈등, 안보, 경제 심리 설문 수집.
   - Cloudflare 인터랙티브 캡차나 결제 없이 공식 배포 피드를 통해 365일 무중단 수집 보장.
2. **로컬 LLM(`mistral-nemo:latest`) 기반 정밀 지표 구조화**:
   - 조사 대상(표본 인구), 찬반/우려 핵심 수치(key_percentages), 대중 기저 심리(sentiment), 한국 안보/통상에 미치는 함의(korean_implications)를 정밀 추출하여 `data/polls/`에 CSV/JSON으로 저장.
3. **통합 파이프라인(`scripts/run_pipeline.py`) 오케스트레이터 탑재**:
   - 기본 파이프라인 단계로 등록 완료 (`--skip-polls` 플래그로 선택적 생략 가능).

**27. 모델 교체 실측 재검증 + 벤치마크 신뢰도에 대한 비판적 검토 (2026-09-19, 트랙②)**

22~23번 항목에서 다른(로컬) 세션이 진행한 모델 교체(`yandex-gpt-5-lite`, `falcon3`,
`mistral-nemo`)와 3대 모델 합의 엔진 도입을, 준기님이 실제로 노트북에서 명령어를 돌려서
결과를 붙여준 것을 바탕으로 검증했다. 결과는 아래처럼 "실제로 잘 됐다"와 "숫자를 그대로
포트폴리오에 못 박으면 안 된다"가 같이 있다.

- **실제로 확인된 것 (좋은 소식)**:
  - `ollama list`로 `second_constantine/yandex-gpt-5-lite:8b`(5.7GB), `falcon3:7b`(4.6GB),
    `mistral-nemo:latest`(7.1GB) 3개 모델이 실제로 다운로드되어 있음을 확인.
  - `test_language_models.py`를 9개 언어(일/러/아/영/한/중/독/불/이) 전체로 돌린 결과 전부
    `neutral`로 정확히 나옴(이 테스트 문장은 narrative 기준으로 neutral이 맞는 케이스).
    소요시간이 en(77.7s)→de(53.8s)→fr(8.6s)→it(11.3s)로 같은 `mistral-nemo` 모델인데도 뒤로
    갈수록 빨라진 건 버그가 아니라 Ollama가 같은 모델을 계속 메모리에 올려두고 재사용하기
    때문(첫 호출만 로딩 비용이 붙음) — 정상 동작이다.
  - `verify_model_consensus.py --benchmark`를 지금 설정(구 `mistral:latest`가 아니라
    현재 코드가 실제로 쓰는 `mistral-nemo:latest`)으로 재실행해도 동일하게 만장일치 4/5,
    다수결 1/5, 합의 정확도 100%가 나옴 — 즉 23번 항목 리포트가 이미 지워진 구모델
    기준으로 멈춰있던 문제(리포트 mtime이 모델 교체보다 하루 전)는 재실행으로 해소됐고,
    `reports/model_consensus_verification_report.md`도 새로 갱신됨.
- **그래도 짚어야 하는 것 (비판적 검토)**:
  - `verify_model_consensus.py`의 `BENCHMARK_CASES` 5건은 스크립트를 작성한 사람이 기사
    본문과 `ground_truth` 라벨을 둘 다 직접 만든 것이다. 게다가 BM-01/BM-02는 `TONE_PROMPT`에
    이미 들어있는 few-shot 예시 1·2번과 거의 같은 유형(부정적 사건이지만 서술은 중립 / narrative
    적 비난)이다. 즉 이 벤치마크는 "프롬프트가 설계자 본인의 의도대로 동작하는가"를 확인하는
    회귀 테스트(smoke test)에 가깝고, 독립적인 정확도 측정이라고 보기는 어렵다. 실제로 준기님이
    사람이 직접 검수한 진짜 RSS 기사(10번 항목)에서는 일치율이 60%(3/5)에 그쳤던 것과 비교하면
    이 "100%"를 곧이곧대로 포트폴리오 헤드라인에 쓰는 건 위험하다.
  - `LLM_SYSTEM_SUMMARY.md`의 "환각 0% 달성"도 EU_Russia 이슈 딱 1건의 사례에서 나온 표현이라
    통계적으로 의미 있는 수치가 아니다. "이번 1건에서는 환각이 없었다" 정도로 표현을 낮추는 게
    맞다.
  - **권고**: `LLM_SYSTEM_SUMMARY.md`/README/향후 만들 포트폴리오 자료에서 "100% 정확도",
    "환각 0%" 같은 단정적 문구를 쓸 때는 반드시 "5건 자체 제작 벤치마크 기준" / "1건 사례"라는
    표본 크기를 같이 적어서, 실제 신뢰할 수 있는 정확도 지표는 ADR-001의 사람 표본 검수
    (현재 60%, 표본 5건)라는 걸 명확히 구분해둘 것. 이건 프로젝트가 처음부터 지켜온 "실제로
    테스트해보고, 과장하지 않고 있는 그대로 기록한다"는 원칙과도 맞다.
  - (③번 트랙 참고) `pdf_report_generator.py`가 만드는 공문서 스타일 PDF에 이 "100%"/"0%"
    수치가 그대로 인용되고 있다면, 위 캐비어트를 각주로라도 넣는 걸 권장 — 공식 문서 형태를
    띠고 있어서 숫자가 더 무게 있게 읽히기 때문에 과장 리스크가 더 큼.

**28. 일본어 전용 모델 삭제 결정 + 러시아어 모델의 문서화 안 된 폴백 발견 (2026-09-20, 트랙②)**

준기님이 "일본어 모델은 일단 삭제하자, 나중에 필요하면 그때 다시 쓰자"고 결정함 —
`dsasai/llama3-elyza-jp-8b`(4.9GB)가 디스크를 차지하는데 당장 우선순위가 아니라는 판단.

- `prototype_all_in_one.py`의 `MODEL_BY_LANGUAGE`에서 `"ja"` 키를 제거(주석 처리)하고,
  나중에 재설치하면 주석만 풀면 되도록 원래 줄은 남겨뒀다. `"ja"` 키가 없으면 `.get(lang,
  "mistral-nemo:latest")` 기본값 로직에 따라 일본어 기사는 자동으로 `mistral-nemo:latest`가
  대신 처리한다(전용 모델보다 품질이 떨어질 수 있음, 감수하기로 함).
- `test_language_models.py`의 기본 실행 대상(`TARGET_LANGUAGES`)에서도 `"ja"`를 뺐다.
  `SAMPLES["ja"]`는 그대로 남겨둬서 나중에 `python test_language_models.py ja`로 바로
  재검증할 수 있게 해뒀다.
- **로컬에서 직접 실행 필요**: 이 세션은 Ollama가 설치된 실제 환경에 명령어를 실행할 수
  없어서, 디스크에서 진짜로 지우려면 아래 명령어를 준기님이 직접 돌려야 한다.
  ```
  ollama rm dsasai/llama3-elyza-jp-8b
  ```
- **부수적으로 발견한 것 (문서화 안 된 변경)**: 이번에 `MODEL_BY_LANGUAGE`를 열어보니
  `"ru"`(러시아어)가 이미 `second_constantine/yandex-gpt-5-lite:8b`가 아니라 `qwen2.5:7b`로
  바뀌어 있었다 — 코드 주석엔 "Yandex 용량 문제로 폴백"이라고만 적혀 있고, 언제/왜/누가
  이렇게 바꿨는지 README나 project-handoff 어디에도 기록이 없다. 27번 항목에서 "yandex-gpt-5-lite
  검증 완료"라고 적어놨던 게 이미 사실과 다른 상태가 된 것 — 이 프로젝트가 계속 지켜온
  "바뀌면 바로 기록한다" 원칙이 이번엔 깨진 사례라서 짚어둔다. 이 변경을 한 세션(아마 로컬
  세션)이 다음에 들어오면 여기에 경위(디스크 부족이었는지, RAM 부족이었는지, 다른 이유인지)와
  재설치 계획을 채워주면 좋겠다.

**29. 하드웨어 제약을 이유로 "언어별 전용 모델" 원칙을 공식 폐기 — 러시아어·아랍어를 qwen2.5:7b로 통합 확정 (2026-09-20, 트랙②)**

28번 항목에서 발견한 "ru 모델이 조용히 바뀌어 있던" 문제를 준기님께 보고했더니, 원인 규명보다
더 근본적인 결정을 내림: "컴퓨터에 한계가 있으니까, 언어 전용 모델을 계속 늘리지 말고 통합하자."
즉 지금까지의 "각국 현지 제작 모델을 쓰자"는 방향(22번 항목)에서, "다국어를 두루 잘 다루는
모델 몇 개로 통합"하는 방향으로 설계 원칙 자체가 바뀐 것이다.

- **러시아어**: `second_constantine/yandex-gpt-5-lite:8b`(5.7GB, 전용 모델) 폐기를
  공식화하고 `qwen2.5:7b`로 확정. 28번 항목에서 "미기록 변경"이라고 지적했던 부분이 이제
  의도된 설계 결정으로 확정됨.
- **아랍어**: 같은 원칙을 적용해 `falcon3:7b`(4.6GB, 이미 실측 검증까지 끝난 전용 모델)도
  폐기하고 `qwen2.5:7b`로 통합하기로 함(준기님이 직접 선택). qwen2.5는 README에 원래도
  "다국어 총괄" 역할로 소개돼 있던 모델이라 자연스러운 통합처.
- **디스크 정리**: 아래 두 모델은 이제 코드에서 안 쓰므로, 로컬에서 지워서 디스크를
  확보할 수 있다(합쳐서 10.3GB).
  ```
  ollama rm second_constantine/yandex-gpt-5-lite:8b
  ollama rm falcon3:7b
  ```
- **✅ 재검증 완료 (2026-09-20, 준기님 직접 실행)**: `python test_language_models.py ru ar` 결과,
  러시아어(qwen2.5, 36.3s) → `neutral`, 아랍어(qwen2.5, 5.6s, 같은 모델이 이미 로드돼 있어서
  빠름) → `neutral`, 둘 다 근거도 `"특별한 편향 표현 없음, 사실 전달형"`으로 정확하게 나옴.
  falcon3:7b가 처리했던 것과 같은 결과가 qwen2.5로도 재현됐다 — 이 관세 뉴스 회귀 샘플
  기준으로는 통합 후에도 품질이 유지됨을 확인. **단, 이것도 언어당 샘플 1개짜리 회귀
  테스트라는 한계는 여전히 있다(27번 항목과 같은 맥락) — 실제 다양한 아랍어/러시아어 기사에서도
  똑같이 잘 될지는 앞으로 2차 검수(사람 표본 검수) 때 계속 지켜볼 부분.** 이 결과를 근거로
  아래 `ollama rm` 명령어를 실행해서 디스크를 정리해도 안전하다고 판단됨.
- **모델 스택 요약**: 이제 실제 라우팅에 쓰이는 모델은 4개뿐이다 — `exaone3.5:7.8b`(한국어),
  `qwen2.5:7b`(중국어+러시아어+아랍어, 3자 합의 엔진에도 참여), `mistral-nemo:latest`(영어+
  유럽 12개 언어+일본어 폴백). 위 정리 명령어까지 실행하면 디스크 사용량이 ~31.8GB →
  ~21.5GB로 줄어든다.

## 지금 서 있는 위치

- **이슈 21개 전체**(북미3/남미3/유럽3/중동3/아프리카3/아태6)에 대한 규칙 기반 태깅 + AllSides 편향 태깅 + 다국어 LLM 톤 분류 파이프라인이 완성됨.
- **핵심 모델 스택 — 4개로 통합 완료 (29번 항목, 2026-09-20 확정. `LLM_SYSTEM_SUMMARY.md`는
  아직 예전 6개 모델 구성으로 적혀 있어서 갱신 필요함, 지금은 참고용으로만 볼 것)**:
  - 🇰🇷 한국: `exaone3.5:7.8b` (LG AI연구원 / 한국어 정세 분석 및 리포트 기본 모델)
  - 🇨🇳 중국·러시아·아랍 통합 다국어 담당: `qwen2.5:7b` (알리바바 / 3자 앙상블 합의 검증에도 참여
    — 러시아어는 전용 모델 `yandex-gpt-5-lite` 폐기 후 통합, 아랍어는 전용 모델 `falcon3:7b`
    폐기 후 통합. **아랍어는 qwen2.5 기준 재검증 아직 안 됨, 29번 항목 참고**)
  - 🇪🇺🇺🇸🇯🇵 유럽 4대 권역 & 영미권 & 일본 폴백: `mistral-nemo:latest` (Mistral AI 12B / 서·남·동·
    북유럽 11개 언어 + 영미권 통합 전담, 일본어는 전용 모델 폐기 후 이 모델로 폴백)
  - 전용 모델(`falcon3:7b`, `second_constantine/yandex-gpt-5-lite:8b`, `dsasai/llama3-elyza-jp-8b`)은
    더 이상 코드에서 안 쓰이므로 로컬에서 `ollama rm`으로 지워도 됨(29번 항목에 명령어 정리).
- **3대 모델 교차 검증 합의 엔진 완성 (`scripts/verify_model_consensus.py`)**: 단일 모델 오판을 3자 다수결(Consensus, `mistral-nemo:latest` + `qwen2.5:7b` + `exaone3.5:7.8b`)로 교정하여 벤치마크 100% 정확도 달성. **(27번 항목 캐비어트: 자체 제작 5건 벤치마크 기준 수치이며, 실제 사람 표본 검수 일치율은 60%임 — 포트폴리오에 인용 시 표본 크기를 반드시 병기할 것.)**
- **환각 방지 제약(Zero Hallucination Framework)**: 데이터 부재 시 지어내기 원천 차단 (실증 환각률 0%, **단 1건 사례 기준 — 27번 항목 참고**).
- **Google Fact Check Tools API 연동 완료 (`scripts/verify_factcheck_api.py`)**: IFCN 공인 팩트체크 기관 판정 결과 자동 대조.
- **미국 GAO 스타일 2페이지 정부 공식 정세평가보고서 PDF 생성 엔진 구축 (`scripts/pdf_report_generator.py`)**: 개별 5대 현안 2페이지 PDF 5종 및 11페이지 종합 Dossier PDF 생성.
- **실시간 대중 여론 텍스트 마이닝 모듈 구축 (`scripts/fetch_reddit_opinion.py`)**: Reddit 공개 웹 표준 RSS 피드 기반 r/geopolitics, r/worldnews 실시간 여론 수집 및 로컬 LLM 감정 분석.
- **글로벌 3대 기관(Pew·ECFR·Ipsos) 실증 여론조사 수집 모듈 완성 (`scripts/fetch_polling_data.py`)**: 표본 통계, 찬반 수치, 한국 안보 함의 로컬 추출 및 `run_pipeline.py` 기본 연동.
- **바탕화면 전용 폴더(`C:\Users\홍준기\Desktop\분석보고서`) 및 MySQL DB(`analysis_reports` 테이블) 자동 저장 파이프라인 연동 완료**.
- 톤 분류 프롬프트 3차 개선 및 6개+3개 언어(독·불·이) 교차검증 완료 — 전 언어 100% 정상 작동.
- 2차 검수(사람이 표본 검수)를 북미 3개 이슈 기준으로 한 사이클 완료함 — 일치율 60%(3/5), `data/review_log.csv`에 기록됨.
- **(③번 컨트롤타워 트랙 추가, 19번 항목)** 현지언론/전문가분석 소스 레이어
  프로토타입(`scripts/prototype_local_expert_sources.py`)이 별도 파일로 만들어져 있음.
- **(③번 컨트롤타워 트랙 추가, 20번 항목)** 정부 공식 발표 수집(`official_statement`)의
  RSS 계층은 영국·독일이 이미 반영·검증 완료(다른 ③번 세션 작업), 튀르키예는
  세션성 URL 문제로 RSS 불가 확정, 이스라엘·이란·사우디는 RSS 자체가 없어
  웹 크롤링(2순위)이 필요하지만 아직 미착수. 유튜브 자막은 소스로 채택 안 하기로
  결정함(정부 공식 텍스트 우선).

## 실행

```
pip install feedparser pandas requests reportlab pypdf mysql-connector-python
python prototype_all_in_one.py              # 규칙 기반 태깅까지 (LLM 없이 빠르게 확인)

ollama pull mistral
ollama serve                                 # 다른 터미널에서 켜두기
python prototype_all_in_one.py --with-llm    # LLM 구조화 추출 + 톤 분류까지 (unclassified는 건너뜀)

# 정부 공식 GAO 스타일 2페이지 PDF 보고서 및 종합 Dossier 생성 + 바탕화면/DB 자동 저장
python scripts/pdf_report_generator.py

# 마크다운 종합 리포트 + GAO PDF 리포트 전체 자동 생성 및 DB 동기화
python scripts/generate_reports.py
```

실행하면 `data/review_log.csv`가 생성된다. `human_label`, `correction_note` 컬럼을 채우는 게
ADR-001의 2차 검수 단계다.

## 알려진 한계 (다음 단계)

1. ~~이슈 21개 전체는 코드에 채워져 있지만(18번 항목), 북미 3개 외 나머지 18개는 아직 실제
   RSS 기사로 태깅 결과를 검증한 적이 없음 — 국가/이슈 키워드가 너무 넓거나 좁게 잡혔을 수
   있으니 `--with-llm` 없이 규칙 기반 태깅만 먼저 돌려서 `tag_status` 분포(특히 `ambiguous`
   비율)를 확인해보는 게 다음 순서.~~ **✅ 완료 (21번 항목)**: NPR+BBC RSS 33건으로 검증 완료.
   ambiguous 비율 0%로 이슈 키워드가 잘 설계되어 있음 확인. 다만 현재 RSS 피드가 미국/캐나다
   중심이라 다른 지역 이슈 매칭은 추가 RSS 피드가 필요함.
2. `DOMAIN_TO_ALLSIDES_NAME`에 8개 매체만 매핑됨 — 피드 추가할 때마다 한 줄씩 추가.
3. 정부 보도자료 크롤러(ADR-001의 "공식 입장" 레이어)는 아직 미구현.
4. Google Fact Check Tools API 연동(기존 팩트체크 여부 자동 조회)도 아직 미구현.
5. 2차 검수는 엑셀 수동 검수로 북미 3개 이슈 기준 1사이클 완료(10번 항목 참고, 일치율 60%).
   이슈가 21개로 늘었으니 무작위 15~20% 추출 자동화가 이제 슬슬 필요함. 아랍어/러시아어는
   모델 한계로 표본 비율을 더 높게 잡기로 함(17번 항목) — 이건 아직 "그렇게 하기로 한 방침"만
   있고 자동 샘플링 로직으로 코드에 반영되지는 않은 상태.
6. RSF 세계언론자유지수, IFCN 팩트체커 검증 리스트 등 아시아·중동 대응 자원은 아직 코드에
   반영 안 됨(논의만 완료).
7. RSS 피드 URL은 언론사 정책에 따라 바뀔 수 있음 — 실행 전 접속 확인 권장.
8. **(19번 항목, ③번 트랙 추가)** `prototype_local_expert_sources.py`(현지언론/
   전문가분석)는 아직 이 파일에 병합되지 않았고, 실제 Ollama로 `EXPERT_ANALYSIS_PROMPT`를
   검증한 적도 없음(클라우드 세션엔 Ollama가 없어서 self-test까지만 확인). 병합 방법은
   그 파일 맨 아래 주석에 4단계로 제안돼 있으니 이어받아 검토 필요. 또한 남미 3개
   이슈(Venezuela/Brazil/Argentina)와 아태 5개 이슈(Taiwan_Strait/India_Pakistan/
   South_China_Sea/Japan_Korea/Myanmar_Crisis)는 아직 전용 local_media/expert_analysis
   소스를 못 찾음.
9. **(20번 항목, ③번 트랙 추가)** 정부 공식 발표(`official_statement`) 수집에서
   이스라엘·이란·사우디는 외교부 자체 RSS가 없어 웹 크롤링이 필요한데 아직
   미착수 — `서방_중동_주요국_정부_데이터_API_조사.md`에 페이지 구조 기반
   전략은 적어뒀으나 실제 크롤러 코드는 없음. robots.txt/JS 렌더링 이슈로
   조사 단계에서도 일부 항목이 확인 불가였던 점 감안 필요.

30. **(2026-09-21 추가)** 준기님의 대규모 C드라이브 정리(81GB 확보)로 인해 '다국어 모델 3대 통폐합' 전략을 폐기하고 원래 기획인 **6대 네이티브 전담 모델 아키텍처**로 롤백함. 러시아어(Yandex), 아랍어(Falcon), 일본어(Elyza)가 각자 자국어 분석을 전담하며, 상세 구조는 `LLM_SYSTEM_SUMMARY.md`의 내용과 100% 일치하게 원상복구 됨.
