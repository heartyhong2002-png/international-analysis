"""
rematch_gov_issues.py — 이미 수집된 정부 발표 JSON을 새 키워드 로직으로 재매칭
================================================================================

gov_announcements_collector.py를 돌릴 때마다 matched_issues가 그 시점의
ISSUE_MATCH_KEYWORDS로 계산돼서 all_announcements_{date}.json / by_issue_{date}.json
안에 그대로 박제됩니다. 그래서 키워드 로직을 나중에 고쳐도(예: Iran_Nuclear에서
bare "iran" 제거), 이미 저장된 예전 JSON 파일들은 자동으로 안 고쳐집니다.

이 스크립트는 RSS를 다시 안 받아오고(=네트워크 필요 없음), 이미 저장된
JSON 파일들의 title/description을 현재 gov_announcements_collector.py의
match_issue()로 다시 돌려서 matched_issues만 새로 계산 + 덮어씁니다.
by_issue_{date}.json도 그 결과로 다시 만듭니다.

사용법:
    python scripts/rematch_gov_issues.py            # 실제로 덮어씀
    python scripts/rematch_gov_issues.py --dry-run   # 뭐가 바뀌는지 미리보기만 (파일 안 건드림)

이 스크립트 실행 후에는 build_database.py(또는 run_pipeline.py --only-db)를
다시 돌려서 DB에 반영해야 합니다. build_database.py의 issue_gov_match 적재
로직은 이미 "매번 TRUNCATE 후 재적재" 방식이라, JSON만 고쳐두면 다음 DB
적재 때 자동으로 깨끗하게 반영됩니다.
"""

import argparse
import glob
import json
import os

from gov_announcements_collector import match_issue, DATA_DIR


def main():
    parser = argparse.ArgumentParser(description="저장된 정부 발표 JSON을 현재 키워드 로직으로 재매칭")
    parser.add_argument("--dry-run", action="store_true",
                         help="파일을 실제로 덮어쓰지 않고, 바뀌는 내용만 미리 보여줌")
    args = parser.parse_args()

    files = sorted(glob.glob(f"{DATA_DIR}/all_announcements_*.json"))
    if not files:
        print(f"✗ {DATA_DIR} 안에 all_announcements_*.json 파일이 없습니다.")
        return

    print("\n" + "=" * 60)
    print(f"🔄 재매칭 시작 ({'미리보기 모드' if args.dry_run else '실제 반영 모드'})")
    print("=" * 60)

    grand_before, grand_after = {}, {}

    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            items = json.load(f)

        changed = 0
        for item in items:
            before = item.get("matched_issues", [])
            after = match_issue(item.get("title", ""), item.get("description", ""))
            for issue in before:
                grand_before[issue] = grand_before.get(issue, 0) + 1
            for issue in after:
                grand_after[issue] = grand_after.get(issue, 0) + 1
            if before != after:
                changed += 1
            item["matched_issues"] = after

        print(f"\n📄 {os.path.basename(path)} — {len(items)}건 중 {changed}건 매칭 결과 변경")

        if not args.dry_run:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)

            # by_issue_{date}.json도 같은 날짜 기준으로 재생성
            by_issue = {}
            for item in items:
                for issue in item["matched_issues"]:
                    by_issue.setdefault(issue, []).append(item)
            by_issue_path = path.replace("all_announcements_", "by_issue_")
            with open(by_issue_path, "w", encoding="utf-8") as f:
                json.dump(by_issue, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("📊 전체 이슈별 매칭 건수 비교 (수정 전 → 수정 후)")
    print("=" * 60)
    all_issues = sorted(set(grand_before) | set(grand_after), key=lambda k: -grand_before.get(k, 0))
    for issue in all_issues:
        b, a = grand_before.get(issue, 0), grand_after.get(issue, 0)
        mark = "  ⬅ 변경됨" if b != a else ""
        print(f"   {issue:<25} {b:>4}건 → {a:>4}건{mark}")

    if args.dry_run:
        print("\n(미리보기 모드라 파일은 그대로입니다. 실제로 반영하려면 --dry-run 빼고 다시 실행하세요.)")
    else:
        print("\n✓ JSON 파일에 반영 완료. 이제 build_database.py를 다시 돌려서 DB에 반영하세요")
        print("  (issue_gov_match 테이블은 매번 자동으로 TRUNCATE 후 재적재되니, 그냥 다시 실행하면 됩니다):")
        print("     python scripts/build_database.py")
        print("  또는: python scripts/run_pipeline.py --only-db")


if __name__ == "__main__":
    main()
