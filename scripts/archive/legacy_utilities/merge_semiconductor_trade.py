"""Merge USITC (US-China, US-Korea) and Korea Customs API (Korea-China)
semiconductor (HS 8541/8542) trade data into one unified monthly dataset.
"""
import json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "semiconductor_trade"

usitc = json.loads((DATA_DIR / "usitc_us_china_korea.json").read_text(encoding="utf-8"))
customs = json.loads((ROOT / "data" / "customs_korea" / "korea_china_semiconductor_trade.json").read_text(encoding="utf-8"))

unified = []

# --- USITC records: already one row per (reporter, partner, direction, year, month) ---
for r in usitc:
    unified.append({
        "reporter": r["reporter"],
        "partner": r["partner"],
        "direction": r["direction"],
        "year": r["year"],
        "month": r["month"],
        "value_usd": r["value_usd"],
        "hs_scope": "8541+8542",
        "source": "USITC_DataWeb",
    })

# --- Korea Customs API records: one row per (hs subcode, month), need to aggregate ---
# skip the yearly "총계" rows; keep only real "YYYY.MM" rows
agg_export = defaultdict(float)
agg_import = defaultdict(float)
for r in customs:
    year_field = r.get("year", "")
    if "." not in str(year_field):
        continue  # skip "총계" (period-total) rows
    y_str, m_str = str(year_field).split(".")
    try:
        year = int(y_str)
        month = int(m_str)
        exp_val = float(r.get("expDlr") or 0)
        imp_val = float(r.get("impDlr") or 0)
    except (ValueError, TypeError):
        continue
    key = (year, month)
    agg_export[key] += exp_val
    agg_import[key] += imp_val

for (year, month), val in agg_export.items():
    unified.append({
        "reporter": "KOR", "partner": "CHN", "direction": "export",
        "year": year, "month": month, "value_usd": val,
        "hs_scope": "8541+8542", "source": "Korea_Customs_OpenAPI",
    })
for (year, month), val in agg_import.items():
    unified.append({
        "reporter": "KOR", "partner": "CHN", "direction": "import",
        "year": year, "month": month, "value_usd": val,
        "hs_scope": "8541+8542", "source": "Korea_Customs_OpenAPI",
    })

unified.sort(key=lambda r: (r["reporter"], r["partner"], r["direction"], r["year"], r["month"]))

out_file = DATA_DIR / "all_semiconductor_trade_merged.json"
out_file.write_text(json.dumps(unified, ensure_ascii=False, indent=2), encoding="utf-8")

# summary totals per series
totals = defaultdict(float)
for r in unified:
    totals[(r["reporter"], r["partner"], r["direction"])] += r["value_usd"]

print(f"Unified records: {len(unified)}")
print(f"Saved to: {out_file}")
print("\n--- Totals by series (18-21 months, USD) ---")
for k, v in sorted(totals.items()):
    print(f"{k[0]} -> {k[1]} ({k[2]}): ${v:,.0f}")
