import streamlit as st
import pandas as pd
import mysql.connector
import os
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go

# Load environment variables
load_dotenv()

# Streamlit Page Config
st.set_page_config(
    page_title="글로벌 조기경보 대시보드 | Signal Gap",
    page_icon="🚨",
    layout="wide"
)

# Initialize DB connection
@st.cache_resource
def init_connection():
    return mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', ''),
        database=os.getenv('MYSQL_DATABASE', 'international_analysis')
    )

try:
    conn = init_connection()
except Exception as e:
    st.error(f"데이터베이스 연결 실패: {e}")
    st.stop()

# Query Data
@st.cache_data(ttl=600)
def load_attention_gap():
    query = "SELECT * FROM v_signal_attention_gap ORDER BY analysis_date DESC"
    df = pd.read_sql(query, conn)
    df['analysis_date'] = pd.to_datetime(df['analysis_date'])
    return df

@st.cache_data(ttl=600)
def load_tone_gap():
    query = "SELECT * FROM v_signal_tone_gap ORDER BY analysis_date DESC, signal_tone_gap_score DESC"
    df = pd.read_sql(query, conn)
    df['analysis_date'] = pd.to_datetime(df['analysis_date'])
    return df

# Load datasets
attention_df = load_attention_gap()
tone_df = load_tone_gap()

# --- HEADER ---
st.title("🚨 글로벌 조기경보 대시보드 (Global Early-Warning)")
st.markdown("**신호 괴리율(Signal Gap) 분석:** 정부의 공식 발표와 민간(독립 언론, 대중 여론) 간의 정보량 및 논조(Tone) 차이를 정량화하여 공급망 리스크와 지정학적 위기를 조기 탐지합니다.")

st.divider()

# --- KPI METRICS ---
st.subheader("📌 오늘의 리스크 현황 (Today's Red Alerts)")
col1, col2, col3 = st.columns(3)

# Metrics calculation based on latest date
if not attention_df.empty:
    latest_date = attention_df['analysis_date'].max()
    latest_attention = attention_df[attention_df['analysis_date'] == latest_date]
    latest_tone = tone_df[tone_df['analysis_date'] == latest_date] if not tone_df.empty else pd.DataFrame()
    
    red_alerts = len(latest_attention[latest_attention['gap_status'].str.contains('RED ALERT|CRITICAL')]) + \
                 len(latest_tone[latest_tone['tone_gap_status'].str.contains('CRITICAL')]) if not latest_tone.empty else 0
    
    warning_alerts = len(latest_attention[latest_attention['gap_status'].str.contains('WARNING')]) + \
                     len(latest_tone[latest_tone['tone_gap_status'].str.contains('WARNING')]) if not latest_tone.empty else 0
    
    col1.metric("🔴 크리티컬 알럿 (Critical Alerts)", f"{red_alerts} 건", "신호 괴리 붕괴", delta_color="inverse")
    col2.metric("🟠 주의 단계 (Warnings)", f"{warning_alerts} 건", "주시 필요", delta_color="inverse")
    col3.metric("📅 분석 기준일", latest_date.strftime('%Y-%m-%d'))
else:
    st.info("데이터가 부족합니다.")

st.divider()

# --- SECTION 1: ATTENTION GAP ---
st.subheader("📊 1. 정보량 괴리율 (Signal Attention Gap)")
st.markdown("정부 통신사의 보도량(Total Official)과 독립 매체/여론의 보도량(Total Independent) 간의 볼륨 차이를 추적합니다.")

if not attention_df.empty:
    # Line chart for volumes over time
    fig_vol = go.Figure()
    fig_vol.add_trace(go.Scatter(x=attention_df['analysis_date'], y=attention_df['total_official_signals'], mode='lines+markers', name='정부 공식 발표 (Official)'))
    fig_vol.add_trace(go.Scatter(x=attention_df['analysis_date'], y=attention_df['total_independent_signals'], mode='lines+markers', name='민간/독립 언론 (Independent)'))
    fig_vol.update_layout(title="시계열 정보량 추이", xaxis_title="날짜", yaxis_title="시그널 수집량", hovermode="x unified")
    st.plotly_chart(fig_vol, use_container_width=True)
    
    # Table of alerts
    st.markdown("**상세 주의보 현황**")
    alert_df = attention_df[attention_df['gap_status'] != 'NORMAL']
    if not alert_df.empty:
        st.dataframe(alert_df[['analysis_date', 'total_official_signals', 'total_independent_signals', 'signal_gap_score', 'gap_status']])
    else:
        st.success("현재 발령된 정보량 괴리 주의보가 없습니다.")

st.divider()

# --- SECTION 2: TONE GAP ---
st.subheader("🌡️ 2. 논조 온도차 (Signal Tone Gap)")
st.markdown("동일한 글로벌 이슈에 대해 정부와 민간이 내는 목소리의 뉘앙스(우호적 +1, 비판적 -1) 차이를 분석합니다.")

if not tone_df.empty:
    # Scatter or Bar for latest date
    latest_tones = tone_df[tone_df['analysis_date'] == tone_df['analysis_date'].max()]
    
    if not latest_tones.empty:
        fig_tone = px.bar(
            latest_tones, 
            x='issue_ids', 
            y=['avg_gov_tone', 'avg_indep_tone'], 
            barmode='group',
            title=f"이슈별 논조 온도차 (기준일: {tone_df['analysis_date'].max().strftime('%Y-%m-%d')})",
            labels={'value': '논조 점수 (1=우호, -1=비판)', 'variable': '출처', 'issue_ids': '글로벌 이슈'}
        )
        st.plotly_chart(fig_tone, use_container_width=True)
        
        st.markdown("**논조 온도차 주의보**")
        tone_alerts = latest_tones[latest_tones['tone_gap_status'] != 'NORMAL']
        if not tone_alerts.empty:
            st.dataframe(tone_alerts[['issue_ids', 'avg_gov_tone', 'avg_indep_tone', 'signal_tone_gap_score', 'tone_gap_status']])
        else:
            st.success("현재 논조가 크게 충돌하는 이슈가 없습니다.")
    else:
        st.info("최신 논조 데이터가 없습니다.")
else:
    st.info("논조 괴리(Tone Gap) 데이터가 없습니다.")

st.divider()
st.caption("데이터 출처: MySQL DB (international_analysis) | 렌더링: Streamlit & Plotly")
