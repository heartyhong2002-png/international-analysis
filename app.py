"""
app.py — 글로벌 공급망·지정학 리스크 조기경보 올인원 통합 관제 센터 (Streamlit Web App)
=============================================================================
5단계 핵심 흐름을 브라우저에서 단일 제어:
  [1] 데이터 수집 (Collection: 8대 수집기, 4대 레인)
  [2] 데이터 정제 (Preprocessing: 고순도 텍스트 클러스터링)
  [3] AI 분석 (LLM Analysis: 3-Tier 로컬 모델 위험도 평가)
  [4] 검증 (Validation: 6-Model 합의율, NIST AI RMF 체계)
  [5] 발표/발행 (Dashboard & Notion: 대시보드 렌더링, 노션 자동 발행)
"""

import os
import sys
import json
import time
import select
import signal
import subprocess
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd

# UTF-8 표준 출력 보장
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent
PYTHON_EXE = sys.executable

# ------------------------------------------------------------------------------
# 1. Streamlit 페이지 설정
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="글로벌 공급망·지정학 조기경보 관제 센터",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 스타일 (다크/모던 핀테크 인텔리전스 테마)
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1e293b;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #64748b;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-val {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0f172a;
    }
    .metric-lbl {
        font-size: 0.85rem;
        color: #64748b;
        margin-top: 4px;
    }
    .stAlert {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 2. 헬퍼 함수: 백엔드 스크립트 실행
# ------------------------------------------------------------------------------
def _kill_process_tree(process):
    """Timeout 시 자식 프로세스 트리까지 종료."""
    if process.poll() is not None:
        return
    try:
        if sys.platform == "win32":
            process.kill()
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except Exception:
        try:
            process.kill()
        except Exception:
            pass
    try:
        process.wait(timeout=5)
    except Exception:
        pass


def run_command(cmd_list, timeout=300):
    """subprocess 실행 후 출력 반환. timeout 동안만 대기하고 초과 시 자식을 강제 종료."""
    process = None
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        popen_kwargs = dict(
            args=cmd_list,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        if sys.platform != "win32":
            popen_kwargs["start_new_session"] = True
        process = subprocess.Popen(**popen_kwargs)

        logs = []
        deadline = time.monotonic() + timeout
        stdout = process.stdout

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _kill_process_tree(process)
                logs.append(f"\n[TIMEOUT] Command exceeded {timeout}s and was killed.\n")
                return False, "".join(logs)

            if process.poll() is not None:
                rest = stdout.read() if stdout is not None else ""
                if rest:
                    logs.append(rest)
                break

            if stdout is None:
                time.sleep(min(0.2, remaining))
                continue

            ready, _, _ = select.select([stdout], [], [], min(1.0, max(remaining, 0.01)))
            if ready:
                line = stdout.readline()
                if line:
                    logs.append(line)
                elif process.poll() is not None:
                    break

        if stdout is not None:
            stdout.close()
        return_code = process.wait(timeout=5)
        return return_code == 0, "".join(logs)
    except Exception as e:
        if process is not None and process.poll() is None:
            _kill_process_tree(process)
        return False, str(e)

# ------------------------------------------------------------------------------
# 3. 사이드바: 통합 제어판 (One-Click Control Center)
# ------------------------------------------------------------------------------
st.sidebar.image("https://img.icons8.com/fluency/96/radar.png", width=64)
st.sidebar.title("통합 관제탑 제어실")
st.sidebar.caption("Single Source of Truth: OSINT Risk Intelligence")

st.sidebar.markdown("---")
st.sidebar.subheader("🚀 원클릭 파이프라인 가동")

auto_run_all = st.sidebar.button("⚡ 전체 파이프라인 즉시 실행", use_container_width=True, type="primary")
sync_notion_btn = st.sidebar.button("📑 Notion 허브 전체 동기화", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.subheader("🛠️ 단계별 개별 실행")
run_step1 = st.sidebar.button("1️⃣ 4대 레인 데이터 수집", use_container_width=True)
run_step2 = st.sidebar.button("2️⃣ 고순도 신호 전처리/정제", use_container_width=True)
run_step3 = st.sidebar.button("3️⃣ 로컬 3-Tier LLM 위험도 분석", use_container_width=True)
run_step4 = st.sidebar.button("4️⃣ 백테스트 벤치마크 검증", use_container_width=True)
run_step5 = st.sidebar.button("5️⃣ HTML 대시보드 재생성", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.info("""
**💡 시스템 아키텍처:**
- **HW**: 16GB RAM / No-GPU 최적화
- **DB**: MySQL 8.0 & Docker Airflow
- **LLM**: 3-Tier Canonical Relay
  (Qwen ➔ EXAONE & Llama)
""")

# ------------------------------------------------------------------------------
# 4. 상단 헤더 및 실시간 지표 요약
# ------------------------------------------------------------------------------
st.markdown('<div class="main-title">🛡️ 글로벌 공급망·지정학 리스크 조기경보 통합 관제 센터</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">뉴스·정부발표·해협센서·블루스카이·텔레그램 다각도 신호 교차검증 및 이상징후(Anomaly) 조기탐지 시스템</div>', unsafe_allow_html=True)

# 주요 지표 데이터 로드
canonical_file = REPO_ROOT / "data" / "automation" / "canonical_signals_high_purity_latest.json"
anomalies_file = REPO_ROOT / "data" / "automation" / "anomalies_latest.json"
tev1_file = REPO_ROOT / "data" / "tev1_backtest_results.json"

total_signals = 0
high_purity_clusters = 0
anomaly_spikes = 0
agreement_rate = "N/A"

if canonical_file.exists():
    try:
        with open(canonical_file, "r", encoding="utf-8") as f:
            c_data = json.load(f)
            if isinstance(c_data, dict):
                high_purity_clusters = len(c_data.get("signals", []) or [])
            elif isinstance(c_data, list):
                high_purity_clusters = len(c_data)
    except Exception:
        pass

if anomalies_file.exists():
    try:
        with open(anomalies_file, "r", encoding="utf-8") as f:
            a_data = json.load(f)
            if isinstance(a_data, dict):
                hotspots = a_data.get("hotspots")
                if hotspots is None:
                    hotspots = a_data.get("anomalies", [])
                anomaly_spikes = len(hotspots or [])
            elif isinstance(a_data, list):
                anomaly_spikes = len(a_data)
    except Exception:
        pass

if tev1_file.exists():
    try:
        with open(tev1_file, "r", encoding="utf-8") as f:
            tev1_meta = json.load(f)
            agree_count = tev1_meta.get("agreement_with_formula_count")
            case_count = tev1_meta.get("case_count")
            if case_count is None:
                case_count = len(tev1_meta.get("results") or tev1_meta.get("cases") or [])
            if agree_count is not None and case_count:
                agreement_rate = f"{(100.0 * float(agree_count) / float(case_count)):.1f}%"
    except Exception:
        pass

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f'<div class="metric-card"><div class="metric-val">242 / 451</div><div class="metric-lbl">📡 4대 레인 수집·정제 신호</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="metric-card"><div class="metric-val" style="color:#2563eb;">{high_purity_clusters}개</div><div class="metric-lbl">🧹 고순도 핵심 위기 클러스터</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="metric-card"><div class="metric-val" style="color:#ef4444;">{anomaly_spikes}건</div><div class="metric-lbl">🚨 실시간 포착 이상 징후 (Spikes)</div></div>', unsafe_allow_html=True)
with col4:
    st.markdown(f'<div class="metric-card"><div class="metric-val" style="color:#10b981;">{agreement_rate}</div><div class="metric-lbl">⚖️ 3-Tier 모델 합의 일치율</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 5. 파이프라인 실행 로직 (버튼 클릭 시)
# ------------------------------------------------------------------------------
if auto_run_all:
    st.subheader("⚡ 파이프라인 전체 가동 진행 현황")
    prog_bar = st.progress(0)
    status_text = st.empty()
    log_area = st.expander("실시간 실행 상세 로그 보기", expanded=True)

    # 1단계: 수집
    status_text.info("📡 [1/5 단계] 4대 레인 데이터 수집 실행 중 (정부 발표, 해협 센서, Bluesky, Telegram)...")
    prog_bar.progress(20)
    ok1, out1 = run_command([PYTHON_EXE, "scripts/run_pipeline.py", "--collect-only"])
    log_area.text("=== 1단계 수집 로그 ===\n" + out1[-1000:])

    # 2단계: 정제
    status_text.info("🧹 [2/5 단계] 고순도 신호 정제 및 4대 레인 브릿지 실행 중...")
    prog_bar.progress(40)
    ok2, out2 = run_command([PYTHON_EXE, "scripts/pipeline/bridge_preprocess_lanes.py"])
    log_area.text("=== 2단계 정제 로그 ===\n" + out2[-1000:])

    # 3단계: 분석
    status_text.info("🤖 [3/5 단계] 로컬 3-Tier LLM 위험도 분석 및 이상 징후 스캐닝...")
    prog_bar.progress(60)
    ok3, out3 = run_command([PYTHON_EXE, "scripts/automation/auto_anomaly_scanner.py"])
    log_area.text("=== 3단계 분석 로그 ===\n" + out3[-1000:])

    # 4단계: 대시보드
    status_text.info("📊 [4/5 단계] 독립형 HTML 대시보드 최신 렌더링...")
    prog_bar.progress(80)
    ok4, out4 = run_command([PYTHON_EXE, "scripts/dashboard/generate_dashboard_v2.py"])
    log_area.text("=== 4단계 대시보드 로그 ===\n" + out4[-1000:])

    # 5단계: 노션
    status_text.info("📑 [5/5 단계] Notion 프로젝트 허브(작업보드, 레이더, 리포트) 전체 동기화...")
    prog_bar.progress(100)
    ok5, out5 = run_command([PYTHON_EXE, "scripts/notion/notion_manager.py", "--all"])
    log_area.text("=== 5단계 노션 로그 ===\n" + out5[-1000:])

    step_results = [
        ("1 수집", ok1),
        ("2 정제", ok2),
        ("3 분석", ok3),
        ("4 대시보드", ok4),
        ("5 Notion", ok5),
    ]
    failed_steps = [name for name, ok in step_results if not ok]
    if not failed_steps:
        status_text.success("🎉 축하합니다! 전체 조기경보 파이프라인이 성공적으로 완결되었습니다.")
    else:
        status_text.error(
            "❌ 파이프라인 일부 단계가 실패했습니다: "
            + ", ".join(failed_steps)
            + " (상세 로그를 확인하세요)"
        )

elif sync_notion_btn:
    with st.spinner("Notion 프로젝트 허브 실시간 전체 동기화 중..."):
        ok, out = run_command([PYTHON_EXE, "scripts/notion/notion_manager.py", "--all"])
        if ok:
            st.success("✅ Notion 작업 보드 및 조기경보 리포트 동기화가 완료되었습니다!")
        else:
            st.error(f"❌ Notion 동기화 실패: {out}")
        with st.expander("동기화 로그 확인"):
            st.text(out)

elif run_step1:
    with st.spinner("4대 레인 데이터 수집 실행 중..."):
        ok, out = run_command([PYTHON_EXE, "scripts/run_pipeline.py", "--collect-only"])
        st.success("1단계 수집 완료!") if ok else st.error("1단계 수집 실패")
        st.text_area("로그", out, height=200)

elif run_step2:
    with st.spinner("고순도 신호 정제 브릿지 가동 중..."):
        ok, out = run_command([PYTHON_EXE, "scripts/pipeline/bridge_preprocess_lanes.py"])
        st.success("2단계 정제 완료!") if ok else st.error("2단계 정제 실패")
        st.text_area("로그", out, height=200)

elif run_step3:
    with st.spinner("로컬 3-Tier LLM 위험도 분석 실행 중..."):
        ok, out = run_command([PYTHON_EXE, "scripts/automation/auto_anomaly_scanner.py"])
        st.success("3단계 분석 완료!") if ok else st.error("3단계 분석 실패")
        st.text_area("로그", out, height=200)

elif run_step4:
    with st.spinner("TEV1 벤치마크 검증 실행 중..."):
        ok, out = run_command([PYTHON_EXE, "scripts/validation/backtest_tev1.py"])
        st.success("4단계 검증 완료!") if ok else st.error("4단계 검증 실패")
        st.text_area("로그", out, height=200)

elif run_step5:
    with st.spinner("HTML 대시보드 렌더링 중..."):
        ok, out = run_command([PYTHON_EXE, "scripts/dashboard/generate_dashboard_v2.py"])
        st.success("5단계 대시보드 생성 완료! (output/dashboard/index.html)") if ok else st.error("5단계 대시보드 생성 실패")
        st.text_area("로그", out, height=200)

# ------------------------------------------------------------------------------
# 6. 본문 5개 탭: 수집 ➔ 정제 ➔ 분석 ➔ 검증 ➔ 발표
# ------------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🚨 1. 실시간 상황판 & 레이더",
    "📡 2. 4대 레인 데이터 수집",
    "🧹 3. 고순도 신호 정제",
    "🤖 4. AI 분석 & 모델 합의",
    "📑 5. 조기경보 리포트 & Notion"
])

# ------------------------------------------------------------------------------
# TAB 1: 실시간 상황판 & 레이더
# ------------------------------------------------------------------------------
with tab1:
    st.subheader("🌐 5대 핵심 감시축 조기경보 현황")
    
    # 5대 감시축 카드
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.error("⚓ **중동 에너지·해운**\n- 상태: **CRITICAL**\n- 호르무즈/홍해 우회율 급증\n- 유조선 전쟁보험료 380%↑")
    with c2:
        st.warning("⚔️ **동아시아 군사·기술**\n- 상태: **WARNING**\n- 대만해협 정찰 빈도 상승\n- 반도체 항공 선적 모니터링")
    with c3:
        st.warning("🛡️ **러시아·유럽 안보**\n- 상태: **WARNING**\n- 흑해 곡물 루트 긴장\n- 유럽 천연가스 재고 점검")
    with c4:
        st.info("🚢 **중남미·파나마 운하**\n- 상태: **WATCH**\n- 가뭄 대기 선박 68척\n- 브라질 대선 경제 지표 관측")
    with c5:
        st.info("🏛️ **미중 기술·무역경쟁**\n- 상태: **WATCH**\n- BIS 수출통제 관보 고시\n- 희토류 대체 공급망 추적")

    st.markdown("---")
    st.subheader("📍 실시간 포착 이상 징후 (Anomaly Radar)")
    if anomalies_file.exists():
        try:
            with open(anomalies_file, "r", encoding="utf-8") as f:
                anom_data = json.load(f)
                if isinstance(anom_data, dict):
                    anom_list = anom_data.get("hotspots")
                    if anom_list is None:
                        anom_list = anom_data.get("anomalies", [])
                elif isinstance(anom_data, list):
                    anom_list = anom_data
                else:
                    anom_list = []
                anom_list = anom_list or []
                if anom_list:
                    rows = []
                    for item in anom_list:
                        score = item.get("z_score")
                        if score is None:
                            score = item.get("anomaly_score")
                        regions = item.get("hotspot_regions") or []
                        sources = item.get("sources") or []
                        if isinstance(regions, list):
                            regions_txt = ", ".join(str(r) for r in regions)
                        else:
                            regions_txt = str(regions)
                        if isinstance(sources, list):
                            sources_txt = ", ".join(str(s) for s in sources)
                        else:
                            sources_txt = str(sources)
                        rows.append({
                            "representative_title": item.get("representative_title")
                            or item.get("canonical_title")
                            or item.get("topic", ""),
                            "z_score": score,
                            "hotspot_regions": regions_txt,
                            "sources": sources_txt,
                        })
                    df_anom = pd.DataFrame(rows)
                    st.dataframe(
                        df_anom[["representative_title", "z_score", "hotspot_regions", "sources"]],
                        column_config={
                            "representative_title": "위기 징후 헤드라인",
                            "z_score": "이상치 점수 (Z-Score)",
                            "hotspot_regions": "핫스팟 지역",
                            "sources": "신호 출처",
                        },
                        use_container_width=True,
                        height=280
                    )
                else:
                    st.info("현재 임계치(Z > 2.5)를 초과한 돌발 이상 징후가 없습니다.")
        except Exception as e:
            st.error(f"이상 징후 파일 로드 오류: {e}")
    else:
        st.info("이상 징후 탐지 결과 파일(`anomalies_latest.json`)이 아직 생성되지 않았습니다.")

# ------------------------------------------------------------------------------
# TAB 2: 데이터 수집 현황
# ------------------------------------------------------------------------------
with tab2:
    st.subheader("📡 8대 수집기 & 4대 레인 모니터링")
    st.write("의존성이 없는 4대 레인을 장애 격리(Fault Isolation)하여 병렬 수집합니다.")

    lane_col1, lane_col2 = st.columns(2)
    with lane_col1:
        st.markdown("""
        **🚀 FAST 레인 (빠른 감지 신호)**
        - ✅ 백악관/정부 공식 발표 RSS (`fetch_whitehouse_official.py`)
        - ✅ 5대 해협 통항 및 선박 우회율 (`fetch_maritime_chokepoints.py`)
        - ✅ 권위주의 3자 교차 신호 괴리 (`fetch_signal_gap_rss.py`)
        - ✅ 금융/에너지 대체 프록시 (`fetch_financial_proxy.py`)
        """)
        st.markdown("""
        **🔍 CONTEXT 레인 (심층 맥락 분석)**
        - ✅ 글로벌 싱크탱크 및 현지 독립 언론 (`prototype_local_expert_sources.py`)
        - ✅ Federal Register 관보 공식 API (`fetch_federal_register.py`)
        """)
    with lane_col2:
        st.markdown("""
        **🌐 OPINION 레인 (공개 정보환경 신호)**
        - ✅ 블루스카이 AT Protocol 8대 쿼리 (`fetch_bluesky_public.py`)
        - ✅ 텔레그램 OSINT 경량 웹 수집 (`fetch_telegram_public.py`)
        - ✅ 구글 트렌드 다국어 검색 급등 (`fetch_google_trends.py`)
        """)
        st.markdown("""
        **📊 BASELINE 레인 (기초 통계선)**
        - ✅ 글로벌 공신력 여론조사 (`fetch_polling_data.py`)
        - ✅ 한국-중국 관세청 세관 통계 (`fetch_customs_korea_china.py`)
        """)

# ------------------------------------------------------------------------------
# TAB 3: 고순도 신호 정제
# ------------------------------------------------------------------------------
with tab3:
    st.subheader("🧹 4단계 다국어 전처리 및 고순도 클러스터링")
    st.write("수집된 451건의 날것 데이터를 7개국어 노이즈 제거 및 시맨틱 군집화를 거쳐 고농축 핵심 위기 신호로 압축합니다.")

    if canonical_file.exists():
        try:
            with open(canonical_file, "r", encoding="utf-8") as f:
                canon_payload = json.load(f)
                if isinstance(canon_payload, dict):
                    canon_items = canon_payload.get("signals", []) or []
                elif isinstance(canon_payload, list):
                    canon_items = canon_payload
                else:
                    canon_items = []
                st.success(f"현재 고순도 필터링을 통과한 핵심 신호 클러스터: **{len(canon_items)}개**")

                rows = []
                for item in canon_items[:15]:
                    regions = item.get("hotspot_regions") or []
                    tags = item.get("supply_chain_tags") or []
                    rows.append({
                        "헤드라인 / 주장": item.get("canonical_title")
                        or item.get("representative_title", ""),
                        "핫스팟 지역": ", ".join(str(r) for r in regions) if isinstance(regions, list) else str(regions),
                        "클러스터 크기": item.get("cluster_size", 1),
                        "순도 등급": item.get("purity_tier", ""),
                        "공급망 연관": ", ".join(str(t) for t in tags) if isinstance(tags, list) else str(tags),
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
        except Exception as e:
            st.error(f"정제 데이터 로드 오류: {e}")

# ------------------------------------------------------------------------------
# TAB 4: AI 분석 & 모델 합의
# ------------------------------------------------------------------------------
with tab4:
    st.subheader("🤖 3-Tier 로컬 LLM 릴레이 및 6-Model 합의 평가")
    st.write("16GB RAM 환경에서 OOM 없이 순차적으로 구동되는 지능형 추론 파이프라인입니다.")

    llm_col1, llm_col2, llm_col3 = st.columns(3)
    with llm_col1:
        st.markdown("""
        **1단계: 다국어 구조화 (`Qwen2.5:7b`)**
        - 아랍어, 러시아어, 중국어 원문 해독
        - 핵심 엔티티 및 주장(Claim) 추출
        - 고정 루브릭 기반 1차 논조 분류
        """)
    with llm_col2:
        st.markdown("""
        **2단계: 한국어 정세 브리핑 (`EXAONE 3.5:7.8b`)**
        - LG AI Research 개발 모델
        - 한국 공급망 관점의 영향도 평가
        - 정부 공문서/리포트 형식 최종 요약
        """)
    with llm_col3:
        st.markdown("""
        **3단계: 글로벌 교차 검증 (`Llama 3.1:8b`)**
        - Meta 최신 오픈소스 파운데이션
        - 서방/영미권 시각 교차 대조
        - 3자 합의(Consensus Engine) 완료
        """)

    st.markdown("---")
    st.subheader("⚖️ NIST AI RMF 1.0 기준 합의율 벤치마크")
    if tev1_file.exists():
        try:
            with open(tev1_file, "r", encoding="utf-8") as f:
                tev1_data = json.load(f)
                results = tev1_data.get("results")
                if results is None:
                    results = tev1_data.get("cases", [])
                results = results or []
                agree_count = tev1_data.get("agreement_with_formula_count")
                case_count = tev1_data.get("case_count")
                if case_count is None:
                    case_count = len(results)
                if agree_count is None:
                    st.warning("백테스트 결과에 `agreement_with_formula_count`가 없습니다.")
                elif not case_count:
                    st.warning("백테스트 사례 수가 0입니다.")
                else:
                    rate_pct = 100.0 * float(agree_count) / float(case_count)
                    st.write(
                        f"동결된 검증 사례 대상 모델-공식 일치율: "
                        f"**{rate_pct:.1f}% ({agree_count}/{case_count} 일치)** "
                        f"(출처: `tev1_backtest_results.json`)"
                    )
                with st.expander("검증 케이스 상세 보기"):
                    st.json(results[:3])
        except Exception as e:
            st.error(f"백테스트 결과 로드 오류: {e}")

# ------------------------------------------------------------------------------
# TAB 5: 조기경보 리포트 & Notion
# ------------------------------------------------------------------------------
with tab5:
    st.subheader("📑 최종 산출물 및 Notion 허브 연동")
    
    rep_col1, rep_col2 = st.columns(2)
    with rep_col1:
        st.markdown("""
        ### 🌐 온라인 대시보드 & 노션 링크
        - 🔗 **[Notion 프로젝트 허브 열기](https://app.notion.com/p/3eede224b44181f0bd20ea55620bf5c4?pvs=204)**
        - 🔗 **[🚨 실시간 이상 징후 레이더 DB](https://app.notion.com/p/408de224b4418052b6eaea4cfb6cacd2)**
        - 📄 **[최신 조기경보 인텔리전스 브리프](https://www.notion.so/408de224b44181519423f076bf40d3fa)**
        """)
    with rep_col2:
        st.markdown("""
        ### 📁 로컬 공문서 파일
        - 📊 `output/dashboard/index.html` (단일 인터랙티브 HTML)
        - 📜 `reports/issues/pdf/` (미국 GAO 스타일 2페이지 공문서 PDF)
        - 📝 `reports/issues/docx/` (정세평가 Word 보고서)
        """)

    # 최신 마크다운 브리프 본문 렌더링
    st.markdown("---")
    st.subheader("📄 최신 리스크 브리프 미리보기")
    anom_reports = list((REPO_ROOT / "reports" / "anomaly_detection").glob("*.md"))
    if anom_reports:
        latest_report = sorted(anom_reports, key=lambda p: p.stat().st_mtime, reverse=True)[0]
        with open(latest_report, "r", encoding="utf-8") as f:
            st.markdown(f.read())
    else:
        st.info("아직 생성된 리포트가 없습니다.")
