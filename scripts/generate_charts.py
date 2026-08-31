"""
국제정세 분석 - 차트 생성 스크립트
데이터를 기반으로 시각화된 차트를 생성합니다.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime

# 한글 폰트 설정
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

# 폴더 설정
DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "charts"

def create_sample_data():
    """샘플 데이터 생성"""
    print("📊 샘플 데이터 생성 중...")
    
    # 샘플: 미국/서방 정세 지수
    usa_data = {
        'Date': pd.date_range('2026-01-01', periods=12, freq='MS'),
        'USA Influence Index': [75, 76, 74, 73, 72, 71, 70, 69, 68, 70, 71, 72],
        'NATO Strength': [85, 85, 86, 87, 86, 85, 84, 84, 85, 86, 87, 88]
    }
    usa_df = pd.DataFrame(usa_data)
    usa_df.to_csv(DATA_DIR / "usa_west.csv", index=False)
    print(f"✓ {DATA_DIR / 'usa_west.csv'} 저장됨")
    
    # 샘플: 중동 정세
    middle_east_data = {
        'Date': pd.date_range('2026-01-01', periods=12, freq='MS'),
        'Tension Level': [72, 74, 75, 76, 77, 76, 75, 74, 73, 72, 71, 70],
        'Stability Index': [45, 44, 43, 42, 41, 42, 43, 44, 45, 46, 47, 48]
    }
    me_df = pd.DataFrame(middle_east_data)
    me_df.to_csv(DATA_DIR / "middle_east.csv", index=False)
    print(f"✓ {DATA_DIR / 'middle_east.csv'} 저장됨")
    
    # 샘플: 경제/무역
    trade_data = {
        'Date': pd.date_range('2026-01-01', periods=12, freq='MS'),
        'Global Trade Index': [100, 102, 104, 103, 101, 100, 99, 98, 99, 101, 103, 105],
        'Tariff Tension': [45, 47, 50, 52, 51, 49, 48, 47, 46, 45, 44, 43]
    }
    trade_df = pd.DataFrame(trade_data)
    trade_df.to_csv(DATA_DIR / "trade_economics.csv", index=False)
    print(f"✓ {DATA_DIR / 'trade_economics.csv'} 저장됨")
    
    return usa_df, me_df, trade_df

def generate_charts(usa_df, me_df, trade_df):
    """차트 생성"""
    print("\n📈 차트 생성 중...")
    
    # 스타일 설정
    sns.set_style("whitegrid")
    
    # 1. USA/Western Influence Trend
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(usa_df['Date'], usa_df['USA Influence Index'], marker='o', label='USA Influence', linewidth=2)
    ax.plot(usa_df['Date'], usa_df['NATO Strength'], marker='s', label='NATO Strength', linewidth=2)
    ax.set_xlabel('Month')
    ax.set_ylabel('Index')
    ax.set_title('USA/Western Powers - Influence & NATO Strength Trend')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "01_usa_western_trend.png", dpi=300, bbox_inches='tight')
    print("✓ 01_usa_western_trend.png 저장됨")
    plt.close()
    
    # 2. Middle East Situation
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.fill_between(me_df['Date'], me_df['Tension Level'], alpha=0.3, label='Tension Level')
    ax.plot(me_df['Date'], me_df['Tension Level'], marker='o', linewidth=2, color='red')
    ax.plot(me_df['Date'], me_df['Stability Index'], marker='s', linewidth=2, color='green', label='Stability Index')
    ax.set_xlabel('Month')
    ax.set_ylabel('Index')
    ax.set_title('Middle East - Tension vs Stability')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "02_middle_east_situation.png", dpi=300, bbox_inches='tight')
    print("✓ 02_middle_east_situation.png 저장됨")
    plt.close()
    
    # 3. Trade & Economics
    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.set_xlabel('Month')
    ax1.set_ylabel('Global Trade Index', color='blue')
    ax1.plot(trade_df['Date'], trade_df['Global Trade Index'], marker='o', color='blue', linewidth=2)
    ax1.tick_params(axis='y', labelcolor='blue')
    
    ax2 = ax1.twinx()
    ax2.set_ylabel('Tariff Tension', color='red')
    ax2.plot(trade_df['Date'], trade_df['Tariff Tension'], marker='s', color='red', linewidth=2)
    ax2.tick_params(axis='y', labelcolor='red')
    
    fig.suptitle('Economics & Trade - Global Trade vs Tariff Tension')
    fig.tight_layout()
    plt.xticks(rotation=45)
    plt.savefig(OUTPUT_DIR / "03_trade_economics.png", dpi=300, bbox_inches='tight')
    print("✓ 03_trade_economics.png 저장됨")
    plt.close()

def main():
    """메인 함수"""
    print("=" * 50)
    print("국제정세 분석 - 차트 생성 시작")
    print(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # 폴더 생성
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        # 샘플 데이터 생성
        usa_df, me_df, trade_df = create_sample_data()
        
        # 차트 생성
        generate_charts(usa_df, me_df, trade_df)
        
        print("\n" + "=" * 50)
        print("✅ 모든 차트 생성 완료!")
        print(f"📁 저장 위치: {OUTPUT_DIR}")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        raise

if __name__ == "__main__":
    main()
