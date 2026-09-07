"""
Interactive Global Geopolitical Issues Dashboard Generator
국제정세 대시보드 생성 스크립트

Generates an interactive HTML dashboard showing:
- Continental issue status by continent
- Key economic indicators
- Global tension index
- Recent major events timeline
"""

import sys
import pandas as pd
import json
from datetime import datetime
from pathlib import Path

# Windows 콘솔의 기본 인코딩(cp949)이 이모지/특수문자를 표현하지 못해
# UnicodeEncodeError가 나는 것을 방지하기 위해 UTF-8로 강제 설정합니다.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

class IssueDashboard:
    def __init__(self):
        self.data_dir = Path("data/issues")
        self.output_dir = Path("output/dashboard")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Sample data for demonstration
        self.issues_data = {
            "North America": {
                "count": 3,
                "risk_level": "MEDIUM",
                "risk_color": "#FFA500",
                "issues": [
                    "US-Canada Trade War",
                    "US-Mexico Migration",
                    "Trump Economic Policy"
                ]
            },
            "South America": {
                "count": 3,
                "risk_level": "MEDIUM",
                "risk_color": "#FFA500",
                "issues": [
                    "Venezuela Crisis",
                    "Brazil Politics",
                    "Argentina Inflation"
                ]
            },
            "Europe": {
                "count": 3,
                "risk_level": "HIGH",
                "risk_color": "#FF4444",
                "issues": [
                    "Ukraine War",
                    "EU-Russia Relations",
                    "Baltic Security"
                ]
            },
            "Middle East": {
                "count": 3,
                "risk_level": "HIGH",
                "risk_color": "#FF4444",
                "issues": [
                    "Iran Nuclear",
                    "Israel-Palestine",
                    "OPEC Energy Policy"
                ]
            },
            "Africa": {
                "count": 3,
                "risk_level": "MEDIUM",
                "risk_color": "#FFA500",
                "issues": [
                    "Sudan Conflict",
                    "Ethiopia Crisis",
                    "Congo Minerals"
                ]
            },
            "Asia-Pacific": {
                "count": 6,
                "risk_level": "HIGH",
                "risk_color": "#FF4444",
                "issues": [
                    "North Korea Nuclear",
                    "Taiwan Strait",
                    "India-Pakistan",
                    "South China Sea",
                    "Japan-Korea",
                    "Myanmar Crisis"
                ]
            }
        }

        self.economic_indicators = {
            "WTI Oil Price": {"value": 75.2, "change": "+2.1%", "status": "↑"},
            "USD/EUR": {"value": 1.095, "change": "+0.5%", "status": "↑"},
            "USD/CNY": {"value": 7.28, "change": "-0.3%", "status": "↓"},
            "S&P 500": {"value": 5420, "change": "+1.2%", "status": "↑"},
            "US 10Y Yield": {"value": "4.25%", "change": "+0.15%", "status": "↑"},
            "VIX Index": {"value": 14.2, "change": "-2.1%", "status": "↓"}
        }

        self.recent_events = [
            {"date": "2026-08-29", "event": "Iran nuclear enrichment accelerates", "region": "Middle East", "severity": "HIGH"},
            {"date": "2026-08-27", "event": "US-Canada tariff negotiations begin", "region": "North America", "severity": "MEDIUM"},
            {"date": "2026-08-25", "event": "Taiwan strait military exercises", "region": "Asia-Pacific", "severity": "HIGH"},
            {"date": "2026-08-23", "event": "OPEC+ production cuts extended", "region": "Middle East", "severity": "MEDIUM"},
            {"date": "2026-08-20", "event": "Ukraine receives new military aid", "region": "Europe", "severity": "MEDIUM"},
        ]

    def generate_html(self):
        """Generate complete interactive HTML dashboard"""
        html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Global Geopolitical Issues Dashboard | 글로벌 국제정세 대시보드</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}

        header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 30px 0;
            border-bottom: 2px solid #0f3460;
        }}

        h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #00d4ff 0%, #0099ff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .subtitle {{
            color: #a0a0a0;
            font-size: 1.1em;
            margin-bottom: 10px;
        }}

        .update-time {{
            color: #4CAF50;
            font-size: 0.9em;
        }}

        .dashboard {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}

        .continent-card {{
            background: linear-gradient(135deg, #0f3460 0%, #16213e 100%);
            border: 2px solid #0099ff;
            border-radius: 10px;
            padding: 25px;
            transition: all 0.3s ease;
            cursor: pointer;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
        }}

        .continent-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0, 153, 255, 0.3);
            border-color: #00d4ff;
        }}

        .continent-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}

        .continent-name {{
            font-size: 1.5em;
            font-weight: bold;
            color: #00d4ff;
        }}

        .issue-count {{
            background: #0099ff;
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }}

        .risk-level {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 5px;
            font-weight: bold;
            margin-bottom: 15px;
            font-size: 0.95em;
        }}

        .risk-high {{
            background: rgba(255, 68, 68, 0.2);
            color: #FF4444;
            border: 1px solid #FF4444;
        }}

        .risk-medium {{
            background: rgba(255, 165, 0, 0.2);
            color: #FFA500;
            border: 1px solid #FFA500;
        }}

        .risk-low {{
            background: rgba(76, 175, 80, 0.2);
            color: #4CAF50;
            border: 1px solid #4CAF50;
        }}

        .issues-list {{
            list-style: none;
        }}

        .issues-list li {{
            padding: 8px 0;
            border-bottom: 1px solid #0f3460;
            color: #b0b0b0;
            font-size: 0.95em;
        }}

        .issues-list li:last-child {{
            border-bottom: none;
        }}

        .issues-list li:before {{
            content: "→ ";
            color: #0099ff;
            margin-right: 8px;
        }}

        .indicators-section {{
            margin-bottom: 40px;
        }}

        .section-title {{
            font-size: 1.8em;
            color: #00d4ff;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #0f3460;
        }}

        .indicators {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}

        .indicator-card {{
            background: linear-gradient(135deg, #0f3460 0%, #16213e 100%);
            border: 1px solid #0099ff;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.2);
        }}

        .indicator-name {{
            font-size: 0.9em;
            color: #a0a0a0;
            margin-bottom: 10px;
        }}

        .indicator-value {{
            font-size: 1.8em;
            color: #00d4ff;
            font-weight: bold;
            margin-bottom: 8px;
        }}

        .indicator-change {{
            font-size: 0.95em;
            padding: 5px 10px;
            border-radius: 5px;
            display: inline-block;
        }}

        .change-up {{
            background: rgba(76, 175, 80, 0.2);
            color: #4CAF50;
        }}

        .change-down {{
            background: rgba(255, 68, 68, 0.2);
            color: #FF4444;
        }}

        .timeline {{
            background: linear-gradient(135deg, #0f3460 0%, #16213e 100%);
            border-left: 4px solid #0099ff;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
        }}

        .timeline-item {{
            margin-bottom: 25px;
            padding-bottom: 25px;
            border-bottom: 1px solid #0f3460;
            position: relative;
        }}

        .timeline-item:last-child {{
            border-bottom: none;
        }}

        .timeline-date {{
            color: #0099ff;
            font-weight: bold;
            font-size: 0.95em;
        }}

        .timeline-event {{
            color: #e0e0e0;
            margin: 8px 0;
            font-size: 1em;
        }}

        .timeline-region {{
            display: inline-block;
            background: #0099ff;
            color: white;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.8em;
            margin-right: 8px;
        }}

        .timeline-severity {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: bold;
        }}

        .severity-high {{
            background: rgba(255, 68, 68, 0.2);
            color: #FF4444;
        }}

        .severity-medium {{
            background: rgba(255, 165, 0, 0.2);
            color: #FFA500;
        }}

        footer {{
            text-align: center;
            margin-top: 60px;
            padding-top: 20px;
            border-top: 1px solid #0f3460;
            color: #707070;
            font-size: 0.9em;
        }}

        @media (max-width: 768px) {{
            h1 {{
                font-size: 1.8em;
            }}

            .dashboard {{
                grid-template-columns: 1fr;
            }}

            .indicators {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🌍 Global Geopolitical Issues Dashboard</h1>
            <h2 style="color: #00d4ff; font-size: 1.3em; font-weight: normal;">글로벌 국제정세 분석 대시보드</h2>
            <p class="subtitle">Tracking 21 Major Issues Across 6 Continents</p>
            <p class="subtitle">6개 대륙, 21개 주요 이슈 추적</p>
            <p class="subtitle">Analysis Period: 2025.01 (Trump Inauguration) ~ Present</p>
            <p class="update-time">Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}</p>
        </header>

        <section class="dashboard">
"""

        # Add continent cards
        for continent, data in self.issues_data.items():
            risk_class = f"risk-{data['risk_level'].lower()}"
            html += f"""
            <div class="continent-card">
                <div class="continent-header">
                    <span class="continent-name">{continent}</span>
                    <span class="issue-count">{data['count']} Issues</span>
                </div>
                <div class="risk-level {risk_class}">
                    Risk Level: {data['risk_level']}
                </div>
                <ul class="issues-list">
"""
            for issue in data['issues']:
                html += f"                    <li>{issue}</li>\n"

            html += """
                </ul>
                <div style="margin-top: 15px; text-align: center;">
                    <button style="background: #0099ff; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; font-weight: bold;">
                        📊 Detailed Analysis
                    </button>
                </div>
            </div>
"""

        html += """
        </section>

        <section class="indicators-section">
            <h2 class="section-title">📈 Key Economic Indicators</h2>
            <div class="indicators">
"""

        # Add economic indicators
        for indicator, info in self.economic_indicators.items():
            change_class = "change-up" if "+" in info["change"] else "change-down"
            html += f"""
                <div class="indicator-card">
                    <div class="indicator-name">{indicator}</div>
                    <div class="indicator-value">{info['value']}</div>
                    <div class="indicator-change {change_class}">{info['status']} {info['change']}</div>
                </div>
"""

        html += """
            </div>
        </section>

        <section class="indicators-section">
            <h2 class="section-title">📋 Recent Major Events Timeline</h2>
            <div class="timeline">
"""

        # Add timeline events
        for event in self.recent_events:
            severity_class = f"severity-{event['severity'].lower()}"
            html += f"""
                <div class="timeline-item">
                    <div class="timeline-date">📅 {event['date']}</div>
                    <div class="timeline-event">{event['event']}</div>
                    <div>
                        <span class="timeline-region">{event['region']}</span>
                        <span class="timeline-severity {severity_class}">{event['severity']}</span>
                    </div>
                </div>
"""

        html += """
            </div>
        </section>

        <footer>
            <p>🌐 Global Geopolitical Issues Analysis System</p>
            <p>데이터 기반 국제정세 분석 플랫폼</p>
            <p>Data Sources: GDELT, FRED, OpenSanctions, UN Comtrade</p>
            <p style="margin-top: 10px; color: #505050;">© 2026 International Affairs Analysis Project | Trump Era (2025.01 ~ Present)</p>
        </footer>
    </div>
</body>
</html>
"""
        return html

    def save_dashboard(self):
        """Save dashboard HTML to file"""
        html_content = self.generate_html()

        output_file = self.output_dir / "index.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"✅ Dashboard saved: {output_file}")
        return output_file


def main():
    print("\n" + "="*60)
    print("🎨 Generating Global Issues Dashboard...")
    print("="*60)

    dashboard = IssueDashboard()
    output_file = dashboard.save_dashboard()

    print(f"\n✅ Dashboard Generation Complete!")
    print(f"📂 Location: {output_file}")
    print(f"📖 Open in browser: file://{output_file.absolute()}")
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
