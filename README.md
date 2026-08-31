# 국제정세 분석 (International Affairs Analysis)

현재의 국제정세를 분석하고 그에 미치는 영향을 분석합니다.

## 📊 주요 분석 영역

- **미국/서방 (USA & Western Powers)**: 미국 정책, NATO, 유럽 정세
- **중동 (Middle East)**: 이스라엘-팔레스타인, 이란, 걸프 지역
- **경제/무역 (Economics & Trade)**: 무역 분쟁, 환율, 경제 제재

## 📁 폴더 구조

```
international-analysis/
├── data/                    # 원본 데이터 (CSV, JSON)
├── scripts/                 # 분석 및 시각화 스크립트
│   ├── generate_charts.py   # 차트 자동 생성
│   └── fetch_data.py        # 데이터 수집
├── reports/                 # 월별/주별 분석 리포트
├── output/
│   └── charts/              # 생성된 차트 이미지
└── README.md
```

## 🚀 시작하기

### 필수 설정

```bash
# 1. 저장소 클론
git clone https://github.com/yourusername/international-analysis.git
cd international-analysis

# 2. Python 가상환경 생성
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 3. 필요한 패키지 설치
pip install -r requirements.txt
```

### 차트 생성

```bash
python scripts/generate_charts.py
```

생성된 차트는 `output/charts/` 폴더에 저장됩니다.

## 📈 최신 분석

(매월 업데이트됩니다)

- [최신 리포트](./reports/)
- [데이터](./data/)

## 🛠️ 기여하기

1. 새로운 데이터 추가: `data/` 폴더에 CSV 파일 추가
2. 분석 스크립트 개선: `scripts/` 폴더의 파이썬 파일 수정
3. Pull Request 제출

## 📝 라이선스

MIT License

## 📧 연락

준기 - heartyhong2002@naver.com
