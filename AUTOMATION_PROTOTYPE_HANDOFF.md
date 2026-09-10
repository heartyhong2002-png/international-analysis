# 자동화 프로토타입 인수인계 문서

> 컨트롤타워 세션이 만든 프로토타입입니다. "수집→분석→결과물"을 전부
> 자동으로 돌아가게 만들어달라는 요청에 대해, 아이디어를 검증 가능한
> 형태로 먼저 만들어봤습니다. 실제 로컬 환경(Ollama, 스케줄러 등)에서의
> 최종 검증/다듬기는 이어받는 세션(또는 준기님 직접)이 해주세요.

## 배경

기존에 있던 `generate_dashboard.py`는 완전히 하드코딩된 가짜 데이터만
그리는 죽은 코드였고(삭제함), `monthly_update.py`도 존재하지 않는 함수를
import하다 바로 에러 나는 고장난 오케스트레이터였습니다(삭제함). 그래서
"자동화"를 하려면 이 둘을 그냥 스케줄만 걸어서는 안 되고, 진짜 작동하는
걸 새로 만들어야 했습니다.

## 만든 것 3가지

### 1. `scripts/generate_dashboard_v2.py` — ✅ 실제 DB로 검증 완료

예전 것과 다르게, MySQL(`international_analysis`)에 실제로 쿼리해서
`output/dashboard/dashboard_{시각}.html`을 생성합니다. 가짜 샘플 데이터
없음 — 데이터가 없으면 "데이터 없음"이라고 정직하게 표시합니다.

**검증 방법:** 클라우드 샌드박스에 테스트용 MariaDB를 띄우고, 가짜가
아닌 "실제 스키마 + 실제 예시 데이터"(Iran_Nuclear intensity 78.5, IRNA
기사 1건 매칭 등)를 넣은 뒤 이 스크립트를 실제로 실행해서, 생성된 HTML
안에 그 숫자들이 정확히 반영되는지 확인했습니다. 🔴 표시(관심도 높은데
정부 발표 없는 이슈) 로직도 North_Korea_Nuclear로 정확히 잡히는 것까지
확인함.

**이어서 다듬을 부분:**
- 지금은 순수 CSS 막대그래프뿐 — `dataviz` 스킬이나 Chart.js로 업그레이드
- `collected_date`별 시계열 추이(트렌드) 없음 — 최신 스냅샷만 보여줌
- 대륙/지역별 그룹핑 없음
- **실제 준기님 컴퓨터의 진짜 DB로 한 번 더 실행해서 눈으로 확인 필요**
  (저는 클라우드의 가짜 테스트 DB로만 검증했습니다)

```powershell
cd scripts
python generate_dashboard_v2.py
```

### 2. `scripts/run_pipeline_scheduled.bat` — ⚠️ 로컬 검증 필요

Windows 작업 스케줄러(Task Scheduler)에 등록해서 매일 자동으로
`run_pipeline.py` → `generate_dashboard_v2.py`를 실행하는 배치 파일입니다.

**등록 명령어:**
```powershell
schtasks /create /tn "국제정세분석_자동수집" ^
  /tr "C:\Users\홍준기\Desktop\international-analysis\scripts\run_pipeline_scheduled.bat" ^
  /sc daily /st 07:00
```

**검증 못 한 부분 (반드시 확인 필요):**
- 배치 파일 안의 `PYTHON_EXE=python`이 실제 필요한 패키지(pandas,
  mysql-connector-python 등)가 설치된 그 인터프리터를 가리키는지 —
  이번 세션에서 인터프리터 불일치로 `ModuleNotFoundError`가 여러 번
  났었기 때문에, 예약 실행 시점에도 같은 문제가 날 수 있습니다.
  `where python`으로 확인한 전체 경로를 직접 넣는 걸 추천합니다.
- 사용자가 로그오프한 상태에서도 스케줄이 실행되는지(작업 스케줄러
  등록 시 "사용자가 로그온했는지 여부에 관계없이 실행" 옵션 필요할 수 있음)
- MySQL 서버가 컴퓨터 부팅 시 자동으로 켜지는 서비스로 등록되어 있는지
  (아니면 예약 실행 시점에 DB 접속 자체가 실패함)

### 3. `analyze_signals.py`를 파이프라인에 연결하는 방법 — 제안만, 미적용

`analyze_signals.py`는 이미 실제로 작동하는 스크립트입니다(Ollama +
Qwen2.5로 한국어 분석 리포트 생성). 근데 로컬 Ollama 서버가 필요해서
클라우드 샌드박스에서는 실행/검증이 불가능했습니다 — 그래서 코드를
직접 고치지 않고, `run_pipeline.py`에 추가할 패치만 제안합니다:

```python
# run_pipeline.py의 main() 함수, steps 리스트 구성 부분에 추가:
parser.add_argument("--with-analysis", action="store_true",
                     help="analyze_signals.py(Ollama 분석 리포트)까지 마지막에 실행")
...
if args.with_analysis:
    steps.append(("분석 리포트 생성 (Ollama)", "analyze_signals.py", []))
```

**이어서 할 일:** 로컬에서 `python scripts/analyze_signals.py`가 단독으로
잘 도는지 먼저 확인 → 위 패치를 `run_pipeline.py`에 직접 적용 → `--with-analysis`
플래그로 전체 파이프라인에 잘 물리는지 테스트.

## 우선순위 제안

1. `generate_dashboard_v2.py`를 진짜 로컬 DB로 한 번 돌려서 결과 확인 (제일 쉬움, 이미 검증됨)
2. `run_pipeline_scheduled.bat`의 `PYTHON_EXE` 경로 확정하고 수동으로 한 번 실행해보기
3. 문제없으면 `schtasks`로 등록
4. `analyze_signals.py` 연결은 그 다음 — 로컬 LLM 세션(②번 트랙)과 상의해서
   최종 리포트 포맷을 `model_router.py` 쪽과 합칠지 먼저 정하고 진행하는 게
   나을 수 있음 (안 그러면 리포트 포맷이 두 번 나올 위험)

## 컨트롤타워 세션이 이 작업에서 확인/보장한 것

- ✅ `generate_dashboard_v2.py`가 실제 MySQL 쿼리 결과를 정확히 렌더링하는지 (테스트 DB로 end-to-end 검증)
- ✅ `.bat` 파일 문법 자체는 이상 없음 (단, 실제 스케줄 실행 환경 검증은 못 함)
- ❌ `analyze_signals.py` 연동은 코드 제안만 했고 실행 검증은 안 함 (Ollama 필요)
- ❌ 실제 준기님 컴퓨터의 진짜 DB/데이터로는 아직 안 돌려봄 — 반드시 한 번 실행해서 확인 필요
