# 📊 데이터 수집 가이드

국제정세 분석 프로젝트의 데이터를 효율적으로 수집하고 관리하는 방법을 설명합니다.

---

## 1. 데이터 수집 흐름

```
매주 금요일
   ↓
fetch_data.py 실행
   ├─ World Bank API → 경제 데이터
   └─ 템플릿 생성 → manual_*.csv
   ↓
수동으로 데이터 입력
   ├─ manual_usa_west.csv (미국/서방 지표)
   ├─ manual_middle_east.csv (중동 긴장도)
   └─ manual_trade_economics.csv (무역/환율)
   ↓
데이터 병합 및 검증
   ↓
generate_charts.py 실행
   ↓
차트 생성 & CSV 업데이트
   ↓
GitHub에 Push
```

---

## 2. 자동화 데이터 수집 (API)

### 2.1 World Bank API

**어떤 데이터?**
- GDP (국내 총생산)
- GDP per capita (1인당 GDP)
- 인플레이션 율
- 도시 인구 비율

**언제?**
- 분기별 업데이트 (매 분기 첫째 주)
- 약 2-3개월 지연됨

**실행 방법**

```bash
cd C:\Users\홍준기\Desktop\international-analysis
source venv/Scripts/activate  # 가상환경 활성화

python scripts/fetch_data.py
```

**결과**
```
data/
├── usa_west.csv
├── middle_east.csv
└── trade_economics.csv
```

### 2.2 NewsAPI (선택사항)

**설정 방법**

1. https://newsapi.org 접속
2. 무료 API 키 발급
3. 프로젝트 최상단에 있는 `.env` 파일에 API 키 추가

```env
NEWSAPI_API_KEY=your_api_key_here
```
*(참고: 스크립트 실행 시 `.env` 파일의 키를 안전하게 자동으로 불러오도록 구현되어 있습니다.)*

**수집 키워드**
- "USA international policy"
- "Middle East conflict"
- "US-China trade war"

### 2.3 Reddit 공개 RSS(Atom 1.0) 기반 실시간 여론 텍스트 마이닝

**어떤 데이터?**
- 글로벌/미국 최대 온라인 커뮤니티 Reddit의 지정학·국제뉴스 전문 서브레딧(`r/geopolitics`, `r/worldnews`) 실시간 토론 글 및 주요 반응.
- 외교 현안에 대한 영미권 대중의 여론 감정(favorable / neutral / critical_anxious) 및 핵심 논란 키워드 3개.

**수집 원리 및 법적/기술적 준수성 (100% 합법 & 비용 0원)**
- **공개 웹 표준 엔드포인트 활용**: Reddit 서버가 뉴스 리더기 및 외부 공개 구독을 위해 자체 배포하는 공식 공개 URL(`https://www.reddit.com/r/{subreddit}/.rss`)을 사용.
- **법적 안전성**:
  - 비밀번호나 비공개 회원 데이터를 탈취하는 방식이 아닌, **누구나 브라우저로 접근 가능한 100% 공개 포럼**의 데이터를 읽기 전용으로 수집 (*hiQ Labs v. LinkedIn* 미국 연방 항소법원 판례에 부합).
  - 2023년 이후 Reddit이 일반 사용자의 신규 개발자 API 키 발급을 전면 차단함에 따라, 복잡한 서류 심사나 유료 결제 없이도 합법적으로 실시간 여론을 수집할 수 있는 공식 개방 통로를 활용.
- **예의 있는 수집(Gentle Crawling)**:
  - 서버 과부하를 주지 않도록 파이프라인 1회당 최신 5~10건 내외의 헤더만 수집.
  - 헤더에 명확한 식별용 봇 이름(`User-Agent: InternationalAnalysisBot/1.0`)을 투명하게 명시.
  - (선택 사항) 공식 OAuth 개발자 키를 보유한 사용자는 `.env`에 `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET`을 입력하면 초고속 공식 API 모드(분당 100회)로 자동 승격되며, 키가 없으면 공개 RSS로 안전하게 자동 동작함.

**실행 방법**
```bash
# 기본 수집 (r/geopolitics, r/worldnews 각 10건)
python scripts/fetch_reddit_opinion.py

# 로컬 LLM(mistral-nemo:12b)으로 감정분석 및 논란 키워드 추출까지 원스톱 실행
python scripts/fetch_reddit_opinion.py --with-llm
```

**산출물**
```
data/reddit_signals/
├── reddit_opinion_latest.csv      # 수집 게시물 원문, 감정 라벨, 논란 키워드
└── reddit_opinion_summary.json     # 서브레딧별 여론 감정 분포 및 상위 키워드 요약
```

### 2.4 RealClearPolling 여론조사 (Playwright 자동 수집)

**어떤 데이터?**
- 미국 대통령 국정 지지율 (RCP Average)
- 각 여론조사 기관별 지지율 수치 (미국의 국제 영향력, 즉 `USA_Influence_Index` 평가를 위한 객관적 지표로 활용)

**수집 원리 및 합법성**
- 봇 차단(Cloudflare)을 우회하기 위해 `Playwright`라는 헤드리스 브라우저(Headless Browser) 기술을 사용합니다. 백그라운드에서 가상의 크롬 브라우저를 띄워 사람처럼 사이트에 접속한 뒤, 표(Table) 데이터를 파이썬으로 긁어옵니다.
- **합법성**: 로그인 없이 누구나 볼 수 있는 웹사이트의 '공개된 수치(사실 데이터)'를 수집하는 것은 저작권 침해나 해킹에 해당하지 않습니다. 악의적인 디도스(DDoS) 공격이나 상업적 재판매 목적이 아닌, 개인의 정세 분석 및 학술/연구를 위해 주 1~2회 스크립트를 통해 접근하는 것은 데이터 사이언스 분야에서 널리 쓰이는 합법적인 '공정 이용(Fair Use)'입니다.

**사전 설치 방법**
스크립트를 처음 실행하기 전 터미널에 아래 명령어를 한 번 입력해야 합니다. (현재 환경에는 이미 설치 완료됨)
```bash
python -m pip install --upgrade pip
pip install playwright lxml html5lib
playwright install chromium
```

**수집 결과**
- `data/rcp_approval_polls.csv`

### 2.5 글로벌 실증 여론조사 자동 수집 (Pew Research Center · ECFR · Ipsos Global)

**어떤 데이터?**
- 전 세계 최고 수준의 공신력을 지닌 여론조사 기관들의 실증 설문조사 데이터:
  1. **Pew Research Center (미국/글로벌)**: 국제관계(`topic/international-affairs`), 미국 정치·대외정책(`topic/politics-policy`) 정기 설문조사 (표본 수, 세부 찬반 비율, 신뢰도 등).
  2. **ECFR (European Council on Foreign Relations, 유럽)**: 우크라이나 군사 지원, 대러 제재 찬반, 유럽 방위비 증액 등 유럽 연합 시민들의 지정학적 인식 조사.
  3. **Ipsos Global (글로벌 어드바이저)**: 주요 30여 개국 시민들의 글로벌 정세 신뢰도, 군사적 갈등 및 경제 불안 인식 지표.
- 로컬 경량 LLM(`mistral-nemo:12b` 또는 규칙 기반 파서)을 통해 설문 표본(demographics), 핵심 수치(key_percentages), 대중 기저 심리(sentiment), 한국 안보/통상에 미치는 함의(korean_implications)를 정밀 추출.

**수집 원리 및 비용/법적 준수성 (100% 무료 & 합법)**
- **공식 공개 RSS/XML 배포 채널 활용**: 각 기관이 학술 및 언론 공공 배포를 목적으로 제공하는 공식 공개 피드를 호출하므로 API 키나 유료 결제가 필요 없음.
- **봇 차단 없음 & 영구 안정성**: Cloudflare Turnstile 인터랙티브 캡차나 비공개 회원 로그인을 요구하지 않는 순수 공개 웹 표준 규격.
- **규칙 기반 + LLM 하이브리드 파싱**: 네트워크 요청만으로 핵심 수치를 즉시 추출하며, 필요 시 로컬 오픈소스 LLM을 가동하여 100% 로컬 오프라인 환경에서 지정학적 함의를 추출(비용 0원, 데이터 외부 유출 없음).

**실행 방법**
```bash
# 기본 수집 (Pew 2종, ECFR, Ipsos 각 5건 수집 및 규칙 기반 수치 파싱)
python scripts/fetch_polling_data.py

# 로컬 LLM(mistral-nemo:12b)으로 지정학적 함의 및 감정 지표 구조화까지 원스톱 실행
python scripts/fetch_polling_data.py --with-llm

# 특정 기관만 수집 또는 수집 개수 지정
python scripts/fetch_polling_data.py --source pew_intl --limit 10

# 네트워크/LLM 없이 파이프라인 무결성 자체 검증
python scripts/fetch_polling_data.py --self-test
```

**산출물**
```
data/polls/
├── polls_latest.csv      # 기관명, 제목, 설문 URL, 표본/핵심 수치, 감정 라벨, 한국 안보 함의
└── polls_summary.json     # 수집 일시, 총 건수, 기관별 수집 현황 메타데이터
```

---

## 3. 수동 데이터 입력

### 3.1 USA/Western Powers (미국/서방)

**파일**: `data/manual_usa_west.csv`

**작성 방법**

| 컬럼 | 설명 | 범위 | 예시 |
|------|------|------|------|
| Date | 날짜 | YYYY-MM-DD | 2026-08-31 |
| USA_Influence_Index | 미국 국제영향력 | 0-100 | 72 |
| NATO_Strength | NATO 군사력 | 0-100 | 85 |
| EU_Stability | EU 정치 안정도 | 0-100 | 78 |
| Notes | 주요 사건/메모 | 텍스트 | "Biden 방중" |

**예시**
```csv
Date,USA_Influence_Index,NATO_Strength,EU_Stability,Notes
2026-08-31,72,85,78,August geopolitical assessment
2026-09-07,71,84,77,NATO meeting in Brussels
2026-09-14,73,86,79,EU economic recovery plan
```

**데이터 출처**
- Council on Foreign Relations (CFR) 리포트
- NATO 공식 발표
- EU 위원회 통계
- 뉴스 분석

---

### 3.2 Middle East (중동)

**파일**: `data/manual_middle_east.csv`

**작성 방법**

| 컬럼 | 설명 | 범위 | 예시 |
|------|------|------|------|
| Date | 날짜 | YYYY-MM-DD | 2026-08-31 |
| Tension_Level | 지역 긴장도 | 0-100 | 76 |
| Stability_Index | 안정성 지수 | 0-100 | 42 |
| Major_Events | 주요 사건 | 텍스트 | "이란 핵협상 진전" |

**예시**
```csv
Date,Tension_Level,Stability_Index,Major_Events
2026-08-31,76,42,"Israel-Palestine ceasefire talks"
2026-09-07,74,44,"Iran nuclear deal progress"
2026-09-14,72,46,"Gaza humanitarian aid increase"
```

**평가 기준**

**Tension Level (긴장도)**
- 0-20: 평화 상태
- 21-40: 저수준 긴장
- 41-60: 중수준 긴장
- 61-80: 고수준 긴장
- 81-100: 극도 긴장/전쟁

**Stability Index (안정성)**
- 0-20: 극도 불안정
- 21-40: 불안정
- 41-60: 중간 수준
- 61-80: 안정적
- 81-100: 매우 안정적

**데이터 출처**
- UN 보고서
- AFP, Reuters 뉴스
- Middle East Institute 분석
- SIPRI 갈등 데이터

---

### 3.3 Economics & Trade (경제/무역)

**파일**: `data/manual_trade_economics.csv`

**작성 방법**

| 컬럼 | 설명 | 출처 | 빈도 |
|------|------|------|------|
| Date | 날짜 | - | 일일 |
| Global_Trade_Index | 글로벌 무역 지수 | WTO, IMF | 월간 |
| Tariff_Tension | 관세 긴장도 | 관세청 발표 | 주간 |
| Exchange_Rate_USD_CNY | USD/CNY 환율 | Yahoo Finance | 일일 |
| Oil_Price_USD | 유가 (배럴당) | Bloomberg | 일일 |

**예시**
```csv
Date,Global_Trade_Index,Tariff_Tension,Exchange_Rate_USD_CNY,Oil_Price_USD
2026-08-31,104,48,7.15,92
2026-09-07,103,50,7.18,91
2026-09-14,105,47,7.12,93
```

**데이터 출처**
- IMF World Economic Outlook
- WTO 통계
- Yahoo Finance (환율)
- OPEC 유가 정보
- 미국 관세청 (Tariff 정보)

---

## 4. 데이터 입력 팁

### 4.1 효율적 입력 방법

**1단계: 출처 모으기**
- 월요일-수요일: 뉴스/통계 모니터링
- 엑셀에 정보 메모

**2단계: 데이터 정제**
- 목요일: 수집한 정보 정리
- 이상값 확인

**3단계: CSV 입력**
- 금요일 오전: CSV 파일 편집

**4단계: 검증**
- 금요일 오후: 데이터 검증
- 차트 생성 및 확인

### 4.2 데이터 검증 체크리스트

- [ ] 날짜 형식 확인 (YYYY-MM-DD)
- [ ] 숫자 범위 확인 (0-100 범위 내)
- [ ] 빈 셀 확인
- [ ] 특수문자 이상 없음
- [ ] 출처 기록 (Notes 칼럼)

### 4.3 주의사항

❌ **하지 말 것**
- 추측으로 데이터 입력
- 출처 없는 데이터
- 일관성 없는 데이터
- 미래 예측을 현재 데이터로

✅ **할 것**
- 공신력 있는 출처 사용
- 매주 일관된 시간에 입력
- 출처/메모 기록
- 이전 주 데이터와 비교

---

## 5. 월별/분기별 작업

### 5.1 매월 첫째 주 (월간 보고)

1. **데이터 수집**
   ```bash
   python scripts/fetch_data.py
   ```

2. **수동 데이터 입력**
   - manual_*.csv 파일 편집

3. **차트 생성**
   ```bash
   python scripts/generate_charts.py
   ```

4. **리포트 작성**
   - `reports/2026-09-monthly.md` 작성

5. **Push**
   ```bash
   git add .
   git commit -m "Update: September data and charts"
   git push origin main
   ```

### 5.2 매분기 (심층 분석)

- 3개월 데이터 종합 분석
- 트렌드 분석
- 예측/전망
- `reports/2026-Q3-analysis.md` 작성

---

## 6. 데이터 소스 디렉토리

### 경제 데이터

| 기관 | URL | 주기 | 무료 |
|------|-----|------|------|
| World Bank | https://data.worldbank.org | 월간 | ✅ |
| IMF | https://www.imf.org/data | 월간 | ✅ |
| WTO | https://www.wto.org/statistics | 분기 | ✅ |
| OECD | https://data.oecd.org | 월간 | ✅ |

### 정치/안보 데이터

| 기관 | URL | 주기 | 무료 |
|------|-----|------|------|
| UN | https://data.un.org | 월간 | ✅ |
| SIPRI | https://www.sipri.org | 월간 | ✅ |
| CFR | https://www.cfr.org | 실시간 | ✅ |
| Brookings | https://www.brookings.edu | 실시간 | ✅ |

### 뉴스/시장 데이터

| 소스 | URL | 주기 | 무료 |
|------|-----|------|------|
| Reuters | https://www.reuters.com | 실시간 | ✅ |
| AP News | https://apnews.com | 실시간 | ✅ |
| BBC | https://www.bbc.com | 실시간 | ✅ |
| NewsAPI | https://newsapi.org | 실시간 | ✅ |
| Yahoo Finance | https://finance.yahoo.com | 실시간 | ✅ |

---

## 7. 자주 묻는 질문 (FAQ)

**Q: 데이터가 없으면 어떻게 하나요?**
A: 지난주 데이터를 사용하거나, 관련 보도/분석을 참고하여 추정값을 사용합니다. 출처를 반드시 기록하세요.

**Q: 얼마나 자주 업데이트해야 하나요?**
A: 최소 주간 1회(금요일), 권장은 일일 업데이트입니다.

**Q: 여러 출처의 데이터가 다르면?**
A: 신뢰성 높은 국제기구(UN, IMF, World Bank)의 데이터를 우선합니다.

**Q: 과거 데이터는 어떻게 입력하나요?**
A: 처음 세팅할 때 2-3개월 과거 데이터를 입력하면, 트렌드를 더 정확하게 볼 수 있습니다.

---

## 8. 향후 계획

### Phase 1 (현재)
- ✅ 수동 데이터 수집
- API 연동 (World Bank)

### Phase 2 (3개월)
- 데이터 수집 완전 자동화
- GitHub Actions 스케줄링
- NewsAPI 통합

### Phase 3 (6개월)
- 머신러닝 기반 이상값 탐지
- 자동 예측 모델
- 실시간 대시보드

---

**마지막 업데이트**: 2026-08-31
**다음 검토**: 2026-09-30
