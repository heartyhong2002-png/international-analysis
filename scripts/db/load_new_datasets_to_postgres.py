"""
load_new_datasets_to_postgres.py
신규 수집·전처리 산출물(반도체, 블루스카이, 5W1H 정형 신호, 연방관보, 의회, GovInfo, 공간신호)
및 기존 피드 최신 CSV 증분을 PostgreSQL(Docker pgvector)에 멱등 적재합니다.
"""

import csv
import json
import os
import sys
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
NEW_TABLES_SQL = Path(__file__).resolve().parent / "postgres_new_tables.sql"
load_dotenv(PROJECT_ROOT / ".env")


def get_pg_conn():
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "intl_admin"),
        password=os.getenv("POSTGRES_PASSWORD", "intl_pg_password_2026"),
        dbname=os.getenv("POSTGRES_DATABASE", "international_analysis"),
    )


def _to_float(val):
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _to_int(val, default=0):
    if val is None or val == "":
        return default
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return default


def load_semiconductor(cur):
    path = DATA_DIR / "semiconductor_market" / "semiconductor_latest.json"
    if not path.exists():
        return 0, 0
    payload = json.loads(path.read_text(encoding="utf-8"))
    collected_utc = payload.get("collected_at_utc", "")
    collected_date = collected_utc[:10] if len(collected_utc) >= 10 else "unknown"

    eq_rows = payload.get("equities_and_indices", [])
    for r in eq_rows:
        cur.execute(
            """
            INSERT INTO semiconductor_equities (
                ticker, observed_date, category, name, role, currency,
                latest_price, day_change_pct, week_change_pct, month_change_pct,
                status_signal, collected_at_utc, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (ticker, observed_date) DO UPDATE SET
                category = EXCLUDED.category,
                name = EXCLUDED.name,
                role = EXCLUDED.role,
                currency = EXCLUDED.currency,
                latest_price = EXCLUDED.latest_price,
                day_change_pct = EXCLUDED.day_change_pct,
                week_change_pct = EXCLUDED.week_change_pct,
                month_change_pct = EXCLUDED.month_change_pct,
                status_signal = EXCLUDED.status_signal,
                collected_at_utc = EXCLUDED.collected_at_utc,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                r.get("ticker"),
                r.get("observed_date") or collected_date,
                r.get("category"),
                r.get("name"),
                r.get("role"),
                r.get("currency"),
                _to_float(r.get("latest_price")),
                _to_float(r.get("day_change_pct")),
                _to_float(r.get("week_change_pct")),
                _to_float(r.get("month_change_pct")),
                r.get("status_signal"),
                collected_utc,
            ),
        )

    mem_rows = payload.get("memory_spot_prices", [])
    for r in mem_rows:
        cur.execute(
            """
            INSERT INTO semiconductor_memory_spot (
                item, collected_date, daily_high_usd, daily_low_usd,
                session_avg_usd, session_change, source, collected_at_utc, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (item, collected_date) DO UPDATE SET
                daily_high_usd = EXCLUDED.daily_high_usd,
                daily_low_usd = EXCLUDED.daily_low_usd,
                session_avg_usd = EXCLUDED.session_avg_usd,
                session_change = EXCLUDED.session_change,
                source = EXCLUDED.source,
                collected_at_utc = EXCLUDED.collected_at_utc,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                r.get("item"),
                collected_date,
                _to_float(r.get("daily_high_usd")),
                _to_float(r.get("daily_low_usd")),
                _to_float(r.get("session_avg_usd")),
                r.get("session_change"),
                r.get("source"),
                collected_utc,
            ),
        )
    return len(eq_rows), len(mem_rows)


def load_bluesky(cur):
    path = DATA_DIR / "bluesky_public" / "bluesky_latest.json"
    if not path.exists():
        return 0
    rows = json.loads(path.read_text(encoding="utf-8"))
    for r in rows:
        uri = r.get("post_uri")
        if not uri:
            continue
        cur.execute(
            """
            INSERT INTO bluesky_signals (
                post_uri, source_id, source_type, signal_class, verification_state,
                query_matched, issue_tags, chokepoint_tag, commodity_tag,
                post_url, author_did, author_handle, author_display_name, language,
                text, external_link, external_title, media_urls, alt_texts,
                has_video, has_media, like_count, repost_count, reply_count,
                published_at, observed_at, content_hash, license_access_note
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            ON CONFLICT (post_uri) DO UPDATE SET
                like_count = EXCLUDED.like_count,
                repost_count = EXCLUDED.repost_count,
                reply_count = EXCLUDED.reply_count,
                issue_tags = EXCLUDED.issue_tags,
                observed_at = EXCLUDED.observed_at
            """,
            (
                uri,
                r.get("source_id"),
                r.get("source_type"),
                r.get("signal_class"),
                r.get("verification_state"),
                r.get("query_matched"),
                Jsonb(r.get("issue_tags") or []),
                r.get("chokepoint_tag"),
                r.get("commodity_tag"),
                r.get("post_url"),
                r.get("author_did"),
                r.get("author_handle"),
                r.get("author_display_name"),
                r.get("language"),
                r.get("text"),
                r.get("external_link"),
                r.get("external_title"),
                Jsonb(r.get("media_urls") or []),
                Jsonb(r.get("alt_texts") or []),
                bool(r.get("has_video")),
                bool(r.get("has_media")),
                _to_int(r.get("like_count")),
                _to_int(r.get("repost_count")),
                _to_int(r.get("reply_count")),
                r.get("published_at"),
                r.get("observed_at"),
                r.get("content_hash"),
                r.get("license_access_note"),
            ),
        )
    return len(rows)


def load_canonical_signals(cur):
    path = DATA_DIR / "automation" / "canonical_signals_latest.json"
    if not path.exists():
        return 0
    payload = json.loads(path.read_text(encoding="utf-8"))
    signals = payload.get("signals", [])
    for s in signals:
        sid = s.get("signal_id") or s.get("cluster_id")
        if not sid:
            continue
        et = s.get("event_tuple") or {}
        cur.execute(
            """
            INSERT INTO canonical_signals (
                signal_id, cluster_id, representative_title, canonical_title, url,
                cluster_size, unique_sources_count, sources, source_types, observed_lanes,
                primary_language, detected_languages, is_cross_lingual, purity_tier,
                relevance_score, who_code, action_code, target_code, threat_severity,
                event_tuple, chokepoints, supply_chain_tags, event_types, hotspot_regions,
                has_visual_media, visual_modalities, media_attachments, visual_alt_texts,
                visual_verification_state, published_at, verification_state,
                alert_level_set, preprocessed_at
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s
            )
            ON CONFLICT (signal_id) DO UPDATE SET
                cluster_size = EXCLUDED.cluster_size,
                unique_sources_count = EXCLUDED.unique_sources_count,
                purity_tier = EXCLUDED.purity_tier,
                relevance_score = EXCLUDED.relevance_score,
                who_code = EXCLUDED.who_code,
                action_code = EXCLUDED.action_code,
                target_code = EXCLUDED.target_code,
                threat_severity = EXCLUDED.threat_severity,
                event_tuple = EXCLUDED.event_tuple,
                preprocessed_at = EXCLUDED.preprocessed_at
            """,
            (
                sid,
                s.get("cluster_id"),
                s.get("representative_title"),
                s.get("canonical_title"),
                s.get("url"),
                _to_int(s.get("cluster_size"), 1),
                _to_int(s.get("unique_sources_count"), 1),
                Jsonb(s.get("sources") or []),
                Jsonb(s.get("source_types") or []),
                Jsonb(s.get("observed_lanes") or []),
                s.get("primary_language"),
                Jsonb(s.get("detected_languages") or []),
                bool(s.get("is_cross_lingual")),
                s.get("purity_tier"),
                _to_float(s.get("relevance_score")),
                et.get("who_code"),
                et.get("action_code"),
                et.get("target_code"),
                et.get("threat_severity"),
                Jsonb(et),
                Jsonb(s.get("chokepoints") or []),
                Jsonb(s.get("supply_chain_tags") or []),
                Jsonb(s.get("event_types") or []),
                Jsonb(s.get("hotspot_regions") or []),
                bool(s.get("has_visual_media")),
                Jsonb(s.get("visual_modalities") or []),
                Jsonb(s.get("media_attachments") or []),
                Jsonb(s.get("visual_alt_texts") or []),
                s.get("visual_verification_state"),
                s.get("published_at"),
                s.get("verification_state"),
                bool(s.get("alert_level_set")),
                s.get("preprocessed_at"),
            ),
        )
    return len(signals)


def load_federal_register(cur):
    path = DATA_DIR / "federal_register" / "federal_register_latest.json"
    if not path.exists():
        return 0
    rows = json.loads(path.read_text(encoding="utf-8"))
    for r in rows:
        doc_no = r.get("document_number")
        if not doc_no:
            continue
        cur.execute(
            """
            INSERT INTO federal_register_docs (
                document_number, source_id, relationship_role, packet, title,
                publication_date, agencies, action, doc_type, executive_order_number,
                abstract, html_url, pdf_url, issue_tags, content_hash,
                observed_at, license_access_note
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s
            )
            ON CONFLICT (document_number) DO UPDATE SET
                title = EXCLUDED.title,
                action = EXCLUDED.action,
                issue_tags = EXCLUDED.issue_tags,
                observed_at = EXCLUDED.observed_at
            """,
            (
                doc_no,
                r.get("source_id"),
                r.get("relationship_role"),
                r.get("packet"),
                r.get("title"),
                r.get("publication_date"),
                Jsonb(r.get("agencies") or []),
                r.get("action"),
                r.get("doc_type"),
                r.get("executive_order_number"),
                r.get("abstract"),
                r.get("html_url"),
                r.get("pdf_url"),
                Jsonb(r.get("issue_tags") or []),
                r.get("content_hash"),
                r.get("observed_at"),
                r.get("license_access_note"),
            ),
        )
    return len(rows)


def load_congress_gov(cur):
    path = DATA_DIR / "congress_gov" / "congress_gov_latest.json"
    if not path.exists():
        return 0
    rows = json.loads(path.read_text(encoding="utf-8"))
    for r in rows:
        doc_id = r.get("document_id")
        if not doc_id:
            continue
        cur.execute(
            """
            INSERT INTO congress_gov_docs (
                document_id, source_id, relationship_role, packet, doc_type,
                congress, chamber, title, publication_date, latest_action,
                summary, source_url, api_url, issue_tags, content_hash,
                observed_at, license_access_note
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s
            )
            ON CONFLICT (document_id) DO UPDATE SET
                latest_action = EXCLUDED.latest_action,
                issue_tags = EXCLUDED.issue_tags,
                observed_at = EXCLUDED.observed_at
            """,
            (
                doc_id,
                r.get("source_id"),
                r.get("relationship_role"),
                r.get("packet"),
                r.get("doc_type"),
                str(r.get("congress")) if r.get("congress") is not None else None,
                r.get("chamber"),
                r.get("title"),
                r.get("publication_date"),
                r.get("latest_action"),
                r.get("summary"),
                r.get("source_url"),
                r.get("api_url"),
                Jsonb(r.get("issue_tags") or []),
                r.get("content_hash"),
                r.get("observed_at"),
                r.get("license_access_note"),
            ),
        )
    return len(rows)


def load_govinfo(cur):
    path = DATA_DIR / "govinfo" / "govinfo_latest.json"
    if not path.exists():
        return 0
    rows = json.loads(path.read_text(encoding="utf-8"))
    for r in rows:
        pkg_id = r.get("package_id")
        if not pkg_id:
            continue
        cur.execute(
            """
            INSERT INTO govinfo_docs (
                package_id, source_id, relationship_role, packet, collection_code,
                doc_type, doc_class, congress, title, publication_date,
                last_modified, summary, source_url, pdf_url, api_url,
                issue_tags, content_hash, observed_at, license_access_note
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            ON CONFLICT (package_id) DO UPDATE SET
                last_modified = EXCLUDED.last_modified,
                issue_tags = EXCLUDED.issue_tags,
                observed_at = EXCLUDED.observed_at
            """,
            (
                pkg_id,
                r.get("source_id"),
                r.get("relationship_role"),
                r.get("packet"),
                r.get("collection_code"),
                r.get("doc_type"),
                r.get("doc_class"),
                str(r.get("congress")) if r.get("congress") is not None else None,
                r.get("title"),
                r.get("publication_date"),
                r.get("last_modified"),
                r.get("summary"),
                r.get("source_url"),
                r.get("pdf_url"),
                r.get("api_url"),
                Jsonb(r.get("issue_tags") or []),
                r.get("content_hash"),
                r.get("observed_at"),
                r.get("license_access_note"),
            ),
        )
    return len(rows)


def load_spatial_signals(cur):
    path = DATA_DIR / "spatial" / "spatial_signals_latest.geojson"
    if not path.exists():
        return 0
    payload = json.loads(path.read_text(encoding="utf-8"))
    features = payload.get("features", [])
    loaded = 0
    for feat in features:
        props = feat.get("properties") or {}
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates") or [None, None]
        lon = _to_float(coords[0]) if len(coords) >= 2 else None
        lat = _to_float(coords[1]) if len(coords) >= 2 else None
        sid = props.get("signal_id")
        place = props.get("place_name") or "unknown"
        if not sid:
            continue
        cur.execute(
            """
            INSERT INTO spatial_signals (
                signal_id, place_name, title, purity_tier, unique_sources,
                geo_method, longitude, latitude, properties, geometry
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (signal_id, place_name) DO UPDATE SET
                title = EXCLUDED.title,
                purity_tier = EXCLUDED.purity_tier,
                unique_sources = EXCLUDED.unique_sources,
                longitude = EXCLUDED.longitude,
                latitude = EXCLUDED.latitude,
                properties = EXCLUDED.properties,
                geometry = EXCLUDED.geometry
            """,
            (
                sid,
                place,
                props.get("title"),
                props.get("purity_tier"),
                _to_int(props.get("unique_sources"), 1),
                props.get("geo_method"),
                lon,
                lat,
                Jsonb(props),
                Jsonb(geom),
            ),
        )
        loaded += 1
    return loaded


def upsert_existing_csv_feeds(cur):
    results = {}

    # 1. rss_signal_gap
    rss_path = DATA_DIR / "signal_gap" / "rss_signal_gap_latest.csv"
    if rss_path.exists():
        cur.execute("SELECT COUNT(*) FROM rss_signal_gap")
        before = cur.fetchone()[0]
        with rss_path.open("r", encoding="utf-8-sig", errors="replace") as f:
            for r in csv.DictReader(f):
                link = (r.get("Link") or "").strip()
                if not link:
                    continue
                cur.execute(
                    """
                    INSERT INTO rss_signal_gap (
                        region, source_type, feed_url, title, summary, link, published_date, scraped_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (link) DO NOTHING
                    """,
                    (
                        (r.get("Region") or "")[:50],
                        (r.get("Source_Type") or "")[:50],
                        r.get("Feed_URL"),
                        (r.get("Title") or "")[:300],
                        r.get("Summary"),
                        link,
                        (r.get("Published_Date") or "")[:50],
                        (r.get("Scraped_At") or "")[:50],
                    ),
                )
        cur.execute("SELECT COUNT(*) FROM rss_signal_gap")
        after = cur.fetchone()[0]
        results["rss_signal_gap"] = (before, after, after - before)

    # 2. telegram_osint
    tg_path = DATA_DIR / "signal_gap" / "telegram_osint_latest.csv"
    if tg_path.exists():
        cur.execute("SELECT COUNT(*) FROM telegram_osint")
        before = cur.fetchone()[0]
        with tg_path.open("r", encoding="utf-8-sig", errors="replace") as f:
            for r in csv.DictReader(f):
                ch = (r.get("Channel_ID") or "").strip()[:100]
                sc = (r.get("Scraped_At") or r.get("Published_At") or "").strip()[:50]
                if not ch or not sc:
                    continue
                cur.execute(
                    """
                    INSERT INTO telegram_osint (region, channel_id, message_content, scraped_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (channel_id, scraped_at) DO NOTHING
                    """,
                    (
                        (r.get("Region") or "")[:50],
                        ch,
                        r.get("Message_Content"),
                        sc,
                    ),
                )
        cur.execute("SELECT COUNT(*) FROM telegram_osint")
        after = cur.fetchone()[0]
        results["telegram_osint"] = (before, after, after - before)

    # 3. us_diplomatic_statements
    dip_path = DATA_DIR / "us_signals" / "us_diplomatic_statements.csv"
    if dip_path.exists():
        cur.execute("SELECT COUNT(*) FROM us_diplomatic_statements")
        before = cur.fetchone()[0]
        with dip_path.open("r", encoding="utf-8-sig", errors="replace") as f:
            for r in csv.DictReader(f):
                link = (r.get("link") or "").strip()
                if not link:
                    continue
                cur.execute(
                    """
                    INSERT INTO us_diplomatic_statements (date, category, title, link, description, source)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (link) DO NOTHING
                    """,
                    (
                        (r.get("date") or "")[:50],
                        (r.get("category") or "")[:100],
                        (r.get("title") or "")[:300],
                        link,
                        r.get("description"),
                        (r.get("source") or "")[:100],
                    ),
                )
        cur.execute("SELECT COUNT(*) FROM us_diplomatic_statements")
        after = cur.fetchone()[0]
        results["us_diplomatic_statements"] = (before, after, after - before)

    # 4. us_presidential_actions
    pres_path = DATA_DIR / "us_signals" / "us_presidential_actions.csv"
    if pres_path.exists():
        cur.execute("SELECT COUNT(*) FROM us_presidential_actions")
        before = cur.fetchone()[0]
        with pres_path.open("r", encoding="utf-8-sig", errors="replace") as f:
            for r in csv.DictReader(f):
                url = (r.get("html_url") or "").strip()
                if not url:
                    continue
                cur.execute(
                    """
                    INSERT INTO us_presidential_actions (
                        date, type, title, executive_order_number, abstract, html_url, pdf_url, source
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (html_url) DO NOTHING
                    """,
                    (
                        (r.get("date") or "")[:50],
                        (r.get("type") or "")[:100],
                        (r.get("title") or "")[:300],
                        (r.get("executive_order_number") or "")[:50],
                        r.get("abstract"),
                        url,
                        r.get("pdf_url"),
                        (r.get("source") or "")[:100],
                    ),
                )
        cur.execute("SELECT COUNT(*) FROM us_presidential_actions")
        after = cur.fetchone()[0]
        results["us_presidential_actions"] = (before, after, after - before)

    return results


def main():
    conn = get_pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(NEW_TABLES_SQL.read_text(encoding="utf-8"))
            print("[OK] Created/verified 8 new PostgreSQL tables.")

            eq_cnt, mem_cnt = load_semiconductor(cur)
            bsky_cnt = load_bluesky(cur)
            can_cnt = load_canonical_signals(cur)
            fr_cnt = load_federal_register(cur)
            cong_cnt = load_congress_gov(cur)
            gov_cnt = load_govinfo(cur)
            sp_cnt = load_spatial_signals(cur)

            inc_results = upsert_existing_csv_feeds(cur)
        conn.commit()

        print("\n=== New PostgreSQL Tables Loaded ===")
        new_tables = [
            "semiconductor_equities",
            "semiconductor_memory_spot",
            "bluesky_signals",
            "canonical_signals",
            "federal_register_docs",
            "congress_gov_docs",
            "govinfo_docs",
            "spatial_signals",
        ]
        with conn.cursor() as cur:
            new_total = 0
            for tbl in new_tables:
                cur.execute(f'SELECT COUNT(*) FROM "{tbl}"')
                cnt = cur.fetchone()[0]
                new_total += cnt
                print(f"  - {tbl}: {cnt:,} rows")
            print(f"  >> New tables subtotal: {new_total:,} rows")

            print("\n=== Existing Tables Incremental Upsert ===")
            inc_added_total = 0
            for tbl, (before, after, added) in inc_results.items():
                inc_added_total += added
                print(f"  - {tbl}: {before:,} -> {after:,} (+{added:,} new)")

            # Overall PostgreSQL base table summary
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            all_tables = [r[0] for r in cur.fetchall()]
            grand_total = 0
            for tbl in all_tables:
                cur.execute(f'SELECT COUNT(*) FROM "{tbl}"')
                grand_total += cur.fetchone()[0]
            print(f"\n=== PostgreSQL Grand Total ===")
            print(f"  Base Tables: {len(all_tables)}, Total Rows: {grand_total:,}")

            # Sample 5W1H JSONB query verification
            cur.execute("""
                SELECT threat_severity, COUNT(*) AS cnt
                FROM canonical_signals
                GROUP BY threat_severity
                ORDER BY cnt DESC
            """)
            print("\n=== Sample Query: canonical_signals by threat_severity ===")
            for sev, cnt in cur.fetchall():
                print(f"  - {sev}: {cnt}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
