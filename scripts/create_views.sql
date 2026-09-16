-- ============================================================================
-- create_views.sql — 포트폴리오용 MySQL 고급 분석 뷰(Views) DDL
-- ============================================================================
-- 프로젝트: 국제정세 분석 자동화 시스템 (International Affairs Analysis)
-- 대상 DB: international_analysis (MySQL 8.0+)
-- 주요 기법: CTE (WITH), Window Functions (LAG, AVG OVER), 피벗 조건부 집계,
--           다중 테이블 조인 및 복합 비즈니스 로직 캡슐화
-- ============================================================================

USE `international_analysis`;

-- ----------------------------------------------------------------------------
-- 뷰 1: v_issue_public_vs_gov_daily
-- 설명: 대중 관심도(Wikipedia 일별 페이지뷰)와 정부 공식 외교 발표를 시계열로 매핑.
-- 활용 기법:
--   - Window 함수 `AVG(...) OVER (ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)`: 7일 이동평균
--   - Window 함수 `LAG(...) OVER (...)`: 전일 대비 검색량 증감율(DoD Growth %) 산출
--   - 정부 발표 여부 플래그 및 시차(Lag) 분석 기반 제공
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_issue_public_vs_gov_daily AS
WITH wiki_daily AS (
    SELECT
        issue,
        date,
        SUM(article_count) AS total_pageviews,
        COUNT(DISTINCT keyword) AS keyword_count
    FROM wikipedia_pageviews
    GROUP BY issue, date
),
gov_daily AS (
    SELECT
        m.issue,
        g.collected_date AS date,
        COUNT(DISTINCT g.id) AS gov_announcement_count,
        COUNT(DISTINCT CASE WHEN g.source_type = 'official_statement' THEN g.id END) AS official_stmt_count,
        COUNT(DISTINCT CASE WHEN g.source_type = 'state_media_news' THEN g.id END) AS state_media_count
    FROM issue_gov_match m
    JOIN gov_announcements g ON g.id = m.announcement_id
    GROUP BY m.issue, g.collected_date
)
SELECT
    w.issue,
    w.date,
    w.total_pageviews,
    ROUND(AVG(w.total_pageviews) OVER (
        PARTITION BY w.issue
        ORDER BY w.date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 1) AS pageviews_7d_ma,
    LAG(w.total_pageviews, 1) OVER (
        PARTITION BY w.issue
        ORDER BY w.date
    ) AS prev_day_pageviews,
    ROUND(
        (w.total_pageviews - LAG(w.total_pageviews, 1) OVER (PARTITION BY w.issue ORDER BY w.date))
        / NULLIF(LAG(w.total_pageviews, 1) OVER (PARTITION BY w.issue ORDER BY w.date), 0) * 100,
        1
    ) AS dod_growth_pct,
    COALESCE(g.gov_announcement_count, 0) AS gov_announcement_count,
    COALESCE(g.official_stmt_count, 0) AS official_stmt_count,
    COALESCE(g.state_media_count, 0) AS state_media_count,
    CASE
        WHEN COALESCE(g.gov_announcement_count, 0) > 0 THEN 'GOV_REACTION_PRESENT'
        ELSE 'NO_GOV_REACTION'
    END AS gov_reaction_flag
FROM wiki_daily w
LEFT JOIN gov_daily g
    ON w.issue = g.issue AND w.date = g.date;


-- ----------------------------------------------------------------------------
-- 뷰 2: v_issue_media_framing_summary
-- 설명: 동일 이슈에 대해 매체 유형(뉴스, 현지언론, 전문가분석) 및 매체 정치 성향
--       (Left, Center, Right)별로 어떤 톤(우호적/중립적/비판적)으로 프레이밍하는지 정량화.
-- 활용 기법: 조건부 집계(CASE WHEN 피벗), 톤별 비율(%) 정규화 산출
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_issue_media_framing_summary AS
WITH cleaned_log AS (
    SELECT
        NULLIF(REPLACE(REPLACE(REPLACE(issue_ids, '[', ''), ']', ''), '\'', ''), '') AS issue,
        COALESCE(NULLIF(source_type, ''), 'unspecified') AS source_type,
        COALESCE(NULLIF(outlet_bias, ''), 'unknown') AS outlet_bias,
        llm_label,
        human_label
    FROM tone_review_log
    WHERE issue_ids IS NOT NULL AND issue_ids != '[]'
)
SELECT
    issue,
    source_type,
    outlet_bias,
    COUNT(*) AS total_articles,
    COUNT(CASE WHEN llm_label = '우호적' THEN 1 END) AS positive_count,
    COUNT(CASE WHEN llm_label = '중립적' THEN 1 END) AS neutral_count,
    COUNT(CASE WHEN llm_label = '비판적' THEN 1 END) AS critical_count,
    ROUND(100.0 * COUNT(CASE WHEN llm_label = '우호적' THEN 1 END) / NULLIF(COUNT(CASE WHEN llm_label IN ('우호적', '중립적', '비판적') THEN 1 END), 0), 1) AS positive_pct,
    ROUND(100.0 * COUNT(CASE WHEN llm_label = '중립적' THEN 1 END) / NULLIF(COUNT(CASE WHEN llm_label IN ('우호적', '중립적', '비판적') THEN 1 END), 0), 1) AS neutral_pct,
    ROUND(100.0 * COUNT(CASE WHEN llm_label = '비판적' THEN 1 END) / NULLIF(COUNT(CASE WHEN llm_label IN ('우호적', '중립적', '비판적') THEN 1 END), 0), 1) AS critical_pct
FROM cleaned_log
GROUP BY issue, source_type, outlet_bias;


-- ----------------------------------------------------------------------------
-- 뷰 3: v_human_in_the_loop_audit
-- 설명: ADR-001 3단계 휴먼인더루프(HITL) 검수 성과 및 모델 품질 감사.
-- 활용 기법: 혼동 행렬(Confusion Matrix) 지표, 일치율(정확도) 및 오분류(False Critical) 분석
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_human_in_the_loop_audit AS
SELECT
    COALESCE(NULLIF(language, ''), 'all') AS language,
    COALESCE(NULLIF(source_type, ''), 'all') AS source_type,
    COUNT(*) AS total_samples,
    COUNT(CASE WHEN llm_label IS NOT NULL AND llm_label != '' THEN 1 END) AS llm_classified_count,
    COUNT(CASE WHEN human_label IS NOT NULL AND human_label != '' THEN 1 END) AS human_reviewed_count,
    ROUND(100.0 * COUNT(CASE WHEN human_label IS NOT NULL AND human_label != '' THEN 1 END)
          / NULLIF(COUNT(*), 0), 1) AS review_coverage_pct,
    COUNT(CASE WHEN human_label IS NOT NULL AND human_label != '' AND llm_label = human_label THEN 1 END) AS agreement_count,
    COUNT(CASE WHEN human_label IS NOT NULL AND human_label != '' AND llm_label != human_label THEN 1 END) AS disagreement_count,
    ROUND(100.0 * COUNT(CASE WHEN human_label IS NOT NULL AND human_label != '' AND llm_label = human_label THEN 1 END)
          / NULLIF(COUNT(CASE WHEN human_label IS NOT NULL AND human_label != '' THEN 1 END), 0), 1) AS model_accuracy_pct,
    -- 모델 과잉 비판 판정 (사람은 비판이 아닌데 모델이 비판으로 오판한 건수)
    COUNT(CASE WHEN human_label IS NOT NULL AND human_label != '' AND llm_label = '비판적' AND human_label != '비판적' THEN 1 END) AS llm_over_critical_count,
    -- 모델 비판 누락 (사람은 비판인데 모델이 놓친 건수)
    COUNT(CASE WHEN human_label IS NOT NULL AND human_label != '' AND llm_label != '비판적' AND human_label = '비판적' THEN 1 END) AS llm_under_critical_count
FROM tone_review_log
GROUP BY language, source_type;


-- ----------------------------------------------------------------------------
-- 뷰 4: v_issue_geopolitical_risk_matrix
-- 설명: 이슈별 대중 관심도(intensity), 위키 총 검색량, 정부 발표 반응도를 결합하여
--       외교적 사각지대(관심은 극도로 높으나 정부 대응이 미흡한 이슈)를 도출하는 종합 리스크 매트릭스.
-- 활용 기법: CTE, Window 순위 함수(DENSE_RANK), 조건부 비즈니스 분류 태깅
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_issue_geopolitical_risk_matrix AS
WITH latest_summary AS (
    SELECT
        issue,
        intensity,
        article_count,
        collected_date
    FROM issue_summary
    WHERE collected_date = (SELECT MAX(collected_date) FROM issue_summary)
),
wiki_aggregate AS (
    SELECT
        issue,
        SUM(article_count) AS wiki_total_pageviews,
        ROUND(AVG(article_count), 0) AS wiki_daily_avg_pageviews
    FROM wikipedia_pageviews
    GROUP BY issue
),
gov_aggregate AS (
    SELECT
        m.issue,
        COUNT(DISTINCT g.id) AS total_gov_matches,
        COUNT(DISTINCT CASE WHEN g.source_type = 'official_statement' THEN g.id END) AS official_statement_count,
        COUNT(DISTINCT CASE WHEN g.source_type = 'state_media_news' THEN g.id END) AS state_media_news_count
    FROM issue_gov_match m
    JOIN gov_announcements g ON g.id = m.announcement_id
    GROUP BY m.issue
)
SELECT
    s.issue,
    s.intensity AS public_intensity,
    COALESCE(w.wiki_total_pageviews, 0) AS wiki_total_pageviews,
    COALESCE(w.wiki_daily_avg_pageviews, 0) AS wiki_daily_avg_pageviews,
    COALESCE(g.total_gov_matches, 0) AS total_gov_matches,
    COALESCE(g.official_statement_count, 0) AS official_statement_count,
    COALESCE(g.state_media_news_count, 0) AS state_media_news_count,
    -- 외교적 사각지대 / 반응도 상태 분류
    CASE
        WHEN s.intensity >= 80.0 AND COALESCE(g.total_gov_matches, 0) = 0 THEN 'CRITICAL_GAP (관심 극대 / 정부 발표 전무)'
        WHEN s.intensity >= 70.0 AND COALESCE(g.total_gov_matches, 0) <= 2 THEN 'WARNING_GAP (관심 높음 / 정부 발표 미흡)'
        WHEN COALESCE(g.total_gov_matches, 0) >= 5 THEN 'ACTIVE_DIPLOMACY (정부 외교 대응 활발)'
        ELSE 'MONITORING (일반 모니터링)'
    END AS diplomatic_status,
    -- 종합 리스크 우선순위 순위 (대중 관심도 내림차순, 정부 발표 오름차순)
    DENSE_RANK() OVER (
        ORDER BY s.intensity DESC, COALESCE(g.total_gov_matches, 0) ASC, s.issue ASC
    ) AS attention_gap_rank,
    s.collected_date AS data_as_of
FROM latest_summary s
LEFT JOIN wiki_aggregate w ON s.issue = w.issue
LEFT JOIN gov_aggregate g ON s.issue = g.issue;
