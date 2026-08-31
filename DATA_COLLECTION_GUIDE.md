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
3. `scripts/fetch_data.py`에 API 키 추가

```python
NEWS_API_KEY = "your_api_key_here"
```

**수집 키워드**
- "USA international policy"
- "Middle East conflict"
- "US-China trade war"

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
