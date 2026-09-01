# 🏛️ 패권국 공식 정부 API 통합 가이드

국제정세 분석을 위해 미국, 중국, 러시아, EU, 일본, 인도의 공식 정부 데이터 API를 활용하는 방법을 설명합니다.

---

## 📊 국가별 API 현황 요약

| 국가 | API 개발 수준 | 주요 API | 인증 | 비용 |
|------|-------------|--------|------|------|
| 🇺🇸 **미국** | ⭐⭐⭐⭐⭐ | Treasury, BEA, BLS | API Key | 무료 |
| 🇪🇺 **EU** | ⭐⭐⭐⭐⭐ | Eurostat | 없음 | 무료 |
| 🇯🇵 **일본** | ⭐⭐⭐⭐ | e-Stat | API Key | 무료 |
| 🇮🇳 **인도** | ⭐⭐⭐⭐ | OGD Platform | API Key | 무료 |
| 🇨🇳 **중국** | ⭐⭐⭐ | China Data Portal | 제3자 | 무료 |
| 🇷🇺 **러시아** | ⭐⭐ | 없음 | - | - |

---

## 1️⃣ 미국 (United States)

### 1.1 Treasury Fiscal Data API ⭐ **최우선**

**용도**: 미국 재정, 부채, 세수 현황

```
공식 사이트: https://fiscaldata.treasury.gov/api-documentation/
인증: 필요 없음 (완전 공개)
데이터: 국가 부채, 세수, 지출, 적자
업데이트: 일일
```

**Python 예시**
```python
import requests

# 미국 국가 부채
url = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/debt_to_penny"
response = requests.get(url)
data = response.json()
print(data)
```

### 1.2 Bureau of Economic Analysis (BEA) API

**용도**: GDP, 국제 무역, 소득 통계

```
공식 사이트: https://apps.bea.gov/api/
등록: UserID 발급 필요 (무료)
데이터: GDP, GNI, 국가 간 무역
업데이트: 분기별
```

**주요 지표**
```
- Real GDP by Industry
- International Trade in Services
- Personal Income and Outlays
```

### 1.3 Bureau of Labor Statistics (BLS) API

**용도**: 실업률, 임금, 물가 지수

```
공식 사이트: https://www.bls.gov/bls/api_features.htm
등록: 이메일 등록 (무료)
데이터: CPI, 실업률, 임금, 고용
업데이트: 월간
```

### 1.4 Commerce Consolidated Screening List API

**용도**: 제재 대상, 무역 제한 기업/개인 추적

```
공식 사이트: https://data.commerce.gov/consolidated-screening-list-api
인증: API Key (발급 필요)
데이터: OFAC 제재 대상자, 거래 제한 기업
업데이트: 실시간
```

**활용**
```python
# 제재 대상 검색
search_term = "Iran"
url = f"https://api.trade.gov/consolidated_screening_list/search"
params = {'q': search_term, 'api_key': 'YOUR_API_KEY'}
response = requests.get(url, params=params)
```

### 1.5 State Department Open Data

**용도**: 외교 정책, 국제 원조

```
공식 사이트: https://www.state.gov/u-s-department-of-state-open-data-plan/
형식: 데이터셋 다운로드 (API 미지원)
데이터: 외교관, 원조, 조약
```

---

## 2️⃣ 유럽연합 (EU)

### 2.1 Eurostat API ⭐ **최우선**

**용도**: EU 경제, 사회, 환경 통계

```
공식 사이트: https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-introduction
인증: 필요 없음 (완전 공개)
표준: SDMX (국제 표준)
업데이트: 월간/분기별
```

**주요 데이터**
```
- GDP & National Accounts
- Employment & Unemployment
- Inflation (HICP)
- Trade (Intra/Extra EU)
- Government Finance
```

**Python 예시**
```python
import requests

# EU GDP 데이터
url = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/NAMQ_10_GDP"
params = {'format': 'json', 'lang': 'en'}
response = requests.get(url, params=params)
data = response.json()
```

### 2.2 European External Action Service (EEAS)

**용도**: EU 외교, 제재 정책

```
공식 사이트: https://www.eeas.europa.eu/
형식: 웹사이트 기반 (API 미지원)
데이터: 외교 선언, 제재 목록
```

---

## 3️⃣ 일본 (Japan)

### 3.1 e-Stat API ⭐ **추천**

**용도**: 일본 통계청 경제/인구 데이터

```
공식 사이트: https://www.e-stat.go.jp/en/developer
등록: API Key 발급 (무료, 이메일 필수)
형식: JSON/XML/CSV
업데이트: 월간/분기별
```

**주요 데이터**
```
- GDP & National Accounts
- Labor Statistics
- Trade Statistics
- Population & Household
```

**Python 예시**
```python
import requests

# 일본 GDP 데이터
api_key = "YOUR_API_KEY"
url = "https://www.e-stat.go.jp/api/1.0/json/getSimpleData"
params = {
    'lang': 'J',
    'statsDataId': '0003355077',  # GDP 예시
    'appId': api_key
}
response = requests.get(url, params=params)
data = response.json()
```

### 3.2 METI Statistics (Ministry of Economy, Trade and Industry)

**용도**: 무역, 산업 통계

```
공식 사이트: https://www.meti.go.jp/english/statistics/
형식: 데이터셋 다운로드
데이터: 무역, 제조업, 에너지
```

---

## 4️⃣ 인도 (India)

### 4.1 Open Government Data (OGD) Platform ⭐ **추천**

**용도**: 인도 통합 정부 데이터 포탈

```
공식 사이트: https://www.data.gov.in/
등록: API Key 발급 (무료)
형식: JSON/XML/CSV
정부 부처: 모든 인도 정부 부처 데이터 포함
```

**주요 API**
```
- Ministry of Commerce & Industry
- Ministry of Statistics
- Reserve Bank of India
- NITI Aayog (정책 싱크탱크)
```

### 4.2 TRADESTAT

**용도**: 인도 무역 통계

```
공식 사이트: https://tradestat.commerce.gov.in/
형식: 웹 기반 (API 지원 예정)
데이터: 인도 수출입, HS 코드별 분석
```

---

## 5️⃣ 중국 (China)

### 5.1 공식 API 현황

❌ **중국은 공식 정부 API를 제공하지 않습니다.**

**대체 방안:**

### 5.2 China Data Portal (제3자 통합)

```
공식 사이트: https://chinadata.live/
인증: 필요 없음
데이터: 중국 국가통계청, 상무부 등 공식 데이터 수집
업데이트: 월간
```

**주요 지표**
```
- GDP & Growth Rate
- Industrial Production
- Retail Sales
- Trade (Export/Import)
- Foreign Direct Investment
```

### 5.3 State Administration of Foreign Exchange (SAFE)

**용도**: 외환보유액, 국제 수지

```
공식 사이트: https://www.safe.gov.cn/en/
형식: 월간 보도자료 (웹 크롤링)
데이터: 외환보유액, 국제 수지, 환율
```

### 5.4 China National Bureau of Statistics

**용도**: 경제 통계

```
공식 사이트: https://www.stats.gov.cn/english/
형식: 데이터셋 다운로드 + 보도자료
데이터: GDP, 산업, 무역, 인구
```

**웹 크롤링 예시**
```python
from bs4 import BeautifulSoup
import requests

# 중국 통계청 데이터 (웹 크롤링)
url = "https://www.stats.gov.cn/english/"
response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')
# 필요한 데이터 추출
```

---

## 6️⃣ 러시아 (Russia)

### 6.1 공식 API 현황

❌ **러시아는 공식 정부 API를 제공하지 않습니다.**

**대체 방안:**

### 6.2 Bank of Russia (중앙은행)

```
공식 사이트: https://www.cbr.ru/eng/statistics/
형식: 월간 보도자료 + 데이터 다운로드
데이터: 환율, 금리, 금융 통계
```

### 6.3 Federal State Statistics Service (Rosstat)

```
공식 사이트: https://rosstat.gov.ru/
형식: 웹 기반 (API 미지원)
데이터: 경제, 인구, 사회 통계
언어: 러시아어
```

### 6.4 Ministry of Foreign Affairs

```
공식 사이트: https://mid.ru/
형식: 공식 성명 (웹 크롤링)
데이터: 외교 정책, 국제 관계
```

**웹 크롤링 예시**
```python
from bs4 import BeautifulSoup
import requests

# 러시아 외교부 공식 성명
url = "https://mid.ru/"
response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')
# 공식 성명 추출
```

---

## 🔧 Python 통합 전략

### 단계별 구현

**1단계: API Key 등록 (무료)**
```
미국:
- Treasury Fiscal Data: 인증 불필요
- BEA: https://apps.bea.gov/api/ → UserID 등록
- BLS: https://www.bls.gov/bls/api_features.htm → 이메일 등록

EU:
- Eurostat: 인증 불필요

일본:
- e-Stat: https://www.e-stat.go.jp/en/developer → API Key 발급

인도:
- OGD Platform: https://www.data.gov.in/ → API Key 발급

중국/러시아:
- 웹 크롤링만 가능
```

**2단계: 통합 fetch_data.py 개선**
```python
# scripts/advanced_fetch_data.py

# 미국 API
def fetch_us_treasury():
    pass

def fetch_us_bea():
    pass

def fetch_us_bls():
    pass

def fetch_us_sanctions():
    pass

# EU API
def fetch_eurostat():
    pass

# 일본 API
def fetch_japan_estat():
    pass

# 인도 API
def fetch_india_ogd():
    pass

# 중국 크롤링
def scrape_china_stats():
    pass

# 러시아 크롤링
def scrape_russia_stats():
    pass

# 메인 실행
def main():
    all_data = {}
    all_data['us'] = {fetch_us_treasury(), fetch_us_bea(), ...}
    all_data['eu'] = {fetch_eurostat()}
    all_data['japan'] = {fetch_japan_estat()}
    all_data['india'] = {fetch_india_ogd()}
    all_data['china'] = {scrape_china_stats()}
    all_data['russia'] = {scrape_russia_stats()}
    
    # 통합 저장
    save_to_csv(all_data)
```

**3단계: 자동화 스케줄링**
```
GitHub Actions를 이용한 일일 자동 수집
.github/workflows/fetch_government_data.yml
```

---

## 📋 데이터 수집 우선순위

### Phase 1 (즉시) ⭐⭐⭐
1. **미국 Treasury Fiscal Data** - 가장 간단, 인증 불필요
2. **EU Eurostat** - 완전 공개, 국제 표준
3. **일본 e-Stat** - API 잘 정리됨

### Phase 2 (1개월) ⭐⭐
4. **미국 BEA/BLS** - API Key 등록 필요
5. **인도 OGD Platform** - 많은 부처 데이터
6. **중국 웹 크롤링** - 공식 API 없음

### Phase 3 (3개월) ⭐
7. **미국 Sanctions API** - 복잡한 필터링
8. **러시아 웹 크롤링** - 러시아어 처리 필요

---

## 📝 사용 예시: 종합 국제정세 지표

```python
# 종합 경제 지표 수집
us_gdp = fetch_us_bea('GDP')           # 미국 GDP
eu_unemployment = fetch_eurostat('UNE') # EU 실업률
jp_trade = fetch_japan_estat('TRADE')  # 일본 무역
in_gdp = fetch_india_ogd('GDP')        # 인도 GDP
cn_gdp = scrape_china_stats('GDP')     # 중국 GDP (크롤링)

# 제재 현황
sanctions = fetch_us_sanctions()        # OFAC 제재 목록

# 금융 안정
us_debt = fetch_us_treasury('DEBT')    # 미국 국가 부채
ru_forex = scrape_russia_stats('FX')   # 러시아 외환보유액

# 종합 분석
analyze_global_economy({
    'us': us_gdp,
    'eu': eu_unemployment,
    'japan': jp_trade,
    'india': in_gdp,
    'china': cn_gdp,
    'sanctions': sanctions,
    'debt': us_debt
})
```

---

## 🚨 주의사항

1. **Rate Limiting 준수**
   - API 호출 횟수 제한 확인
   - 동시 요청 수 제한
   - Sleep 시간 삽입

2. **데이터 라이선스**
   - 모든 정부 데이터는 공개 라이선스
   - 출처 표기 필수 (대부분 CC-BY 또는 유사)

3. **데이터 시간 차이**
   - 각 국가별 발표 일정 다름
   - 지연 시간 고려 (예: 중국 2-3개월)

4. **인증 정보 관리**
   - API Key는 절대 GitHub에 올리지 않기
   - `.env` 파일 사용 또는 환경변수 설정

---

## 📚 추가 자료

- [API Documentation Index](./API_DOCUMENTATION.md)
- [Data Collection Schedule](./data_collection_schedule.csv)
- [Python API Examples](./scripts/api_examples/)

---

**마지막 업데이트**: 2026-08-31  
**다음 검토**: 2026-10-31
