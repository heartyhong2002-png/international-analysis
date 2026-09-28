

-- ----------------------------------------------------------------------------
-- NEW VIEW: v_signal_attention_gap
-- 대중 여론(Reddit), 독립 언론(News/Independent), 공식 정부 발표(Gov/Official)의
-- 일별 수집량을 합산하여 관심도(Attention)의 괴리를 정량화합니다.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_signal_attention_gap AS
WITH dates AS (
    SELECT DISTINCT STR_TO_DATE(SUBSTRING(pub_date, 6, 11), '%d %b %Y') as dt
    FROM gov_announcements WHERE pub_date IS NOT NULL
    UNION
    SELECT DISTINCT CAST(date AS DATE) FROM news_data WHERE date IS NOT NULL
    UNION
    SELECT DISTINCT CAST(SUBSTRING(published, 1, 10) AS DATE) FROM reddit_opinion WHERE published IS NOT NULL
    UNION
    SELECT DISTINCT STR_TO_DATE(SUBSTRING(published_date, 6, 11), '%d %b %Y') FROM rss_signal_gap WHERE published_date IS NOT NULL
),
gov_counts AS (
    SELECT STR_TO_DATE(SUBSTRING(pub_date, 6, 11), '%d %b %Y') as dt, COUNT(*) as gov_count
    FROM gov_announcements
    GROUP BY dt
),
news_counts AS (
    SELECT CAST(date AS DATE) as dt, COUNT(*) as news_count
    FROM news_data
    GROUP BY dt
),
reddit_counts AS (
    SELECT CAST(SUBSTRING(published, 1, 10) AS DATE) as dt, COUNT(*) as reddit_count
    FROM reddit_opinion
    GROUP BY dt
),
rss_official AS (
    SELECT STR_TO_DATE(SUBSTRING(published_date, 6, 11), '%d %b %Y') as dt, COUNT(*) as rss_gov_count
    FROM rss_signal_gap WHERE source_type = 'Official'
    GROUP BY dt
),
rss_indep AS (
    SELECT STR_TO_DATE(SUBSTRING(published_date, 6, 11), '%d %b %Y') as dt, COUNT(*) as rss_indep_count
    FROM rss_signal_gap WHERE source_type = 'Independent'
    GROUP BY dt
)
SELECT
    d.dt as analysis_date,
    COALESCE(g.gov_count, 0) + COALESCE(ro.rss_gov_count, 0) as total_official_signals,
    COALESCE(n.news_count, 0) + COALESCE(ri.rss_indep_count, 0) as total_independent_signals,
    COALESCE(r.reddit_count, 0) as public_sentiment_signals,
    ABS((COALESCE(g.gov_count, 0) + COALESCE(ro.rss_gov_count, 0)) - (COALESCE(n.news_count, 0) + COALESCE(ri.rss_indep_count, 0))) as signal_gap_score,
    CASE
        WHEN (COALESCE(n.news_count, 0) + COALESCE(ri.rss_indep_count, 0)) > (COALESCE(g.gov_count, 0) + COALESCE(ro.rss_gov_count, 0)) * 2
             AND (COALESCE(n.news_count, 0) + COALESCE(ri.rss_indep_count, 0)) > 5 THEN 'RED ALERT: High Independent Activity'
        WHEN (COALESCE(r.reddit_count, 0)) > 5 THEN 'WARNING: High Public Attention'
        ELSE 'NORMAL'
    END as gap_status
FROM dates d
LEFT JOIN gov_counts g ON d.dt = g.dt
LEFT JOIN news_counts n ON d.dt = n.dt
LEFT JOIN reddit_counts r ON d.dt = r.dt
LEFT JOIN rss_official ro ON d.dt = ro.dt
LEFT JOIN rss_indep ri ON d.dt = ri.dt
WHERE d.dt IS NOT NULL
ORDER BY d.dt DESC;

-- ----------------------------------------------------------------------------
-- NEW VIEW: v_signal_tone_gap
-- tone_review_log에 적재된 LLM 판정 결과(우호적/중립적/비판적)를 1, 0, -1 로 치환하고
-- 이슈별 정부 vs 민간(전문가/언론)의 감성(Tone) 온도차를 정량화합니다.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_signal_tone_gap AS
WITH scored_tones AS (
    SELECT
        CAST(SUBSTRING(collected_at, 1, 10) AS DATE) as dt,
        issue_ids,
        source_type,
        CASE llm_label
            WHEN '우호적' THEN 1
            WHEN '중립적' THEN 0
            WHEN '비판적' THEN -1
            ELSE 0
        END as tone_score
    FROM tone_review_log
    WHERE issue_ids IS NOT NULL AND collected_at IS NOT NULL
),
daily_issue_agg AS (
    SELECT
        dt,
        issue_ids,
        AVG(CASE WHEN source_type IN ('official_statement', 'state_media_news') THEN tone_score END) as avg_gov_tone,
        AVG(CASE WHEN source_type IN ('local_media', 'expert_analysis', 'news') THEN tone_score END) as avg_indep_tone,
        COUNT(CASE WHEN source_type IN ('official_statement', 'state_media_news') THEN 1 END) as gov_volume,
        COUNT(CASE WHEN source_type IN ('local_media', 'expert_analysis', 'news') THEN 1 END) as indep_volume
    FROM scored_tones
    GROUP BY dt, issue_ids
)
SELECT
    dt as analysis_date,
    issue_ids,
    ROUND(avg_gov_tone, 2) as avg_gov_tone,
    ROUND(avg_indep_tone, 2) as avg_indep_tone,
    gov_volume,
    indep_volume,
    ABS(COALESCE(avg_gov_tone, 0) - COALESCE(avg_indep_tone, 0)) as signal_tone_gap_score,
    CASE
        WHEN ABS(COALESCE(avg_gov_tone, 0) - COALESCE(avg_indep_tone, 0)) >= 1.5 AND gov_volume > 0 AND indep_volume > 0 THEN 'CRITICAL: Severe Tone Discrepancy'
        WHEN ABS(COALESCE(avg_gov_tone, 0) - COALESCE(avg_indep_tone, 0)) >= 1.0 AND gov_volume > 0 AND indep_volume > 0 THEN 'WARNING: High Tone Discrepancy'
        ELSE 'NORMAL'
    END as tone_gap_status
FROM daily_issue_agg
ORDER BY dt DESC, signal_tone_gap_score DESC;

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


-- ----------------------------------------------------------------------------
-- 조기경보 증거 계층 뷰 1: 대시보드의 현재 경보 목록
-- 점수 자체로 Alert Level을 새로 판단하지 않는다. 경보 판단은 alert_events에
-- 기록된 불변 이벤트를 사용하고, 뷰는 최신 근거와 상태를 읽기 좋게 결합한다.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_dashboard_current_alerts AS
WITH latest_run AS (
    SELECT id, run_key, scoring_version, executed_at, window_start, window_end
    FROM scoring_runs
    WHERE status = 'completed'
    ORDER BY executed_at DESC, id DESC
    LIMIT 1
),
score_rollup AS (
    SELECT
        r.scoring_run_id,
        r.issue_key,
        ROUND(SUM(COALESCE(r.contribution_score, 0)), 2) AS risk_signal_score,
        ROUND(AVG(r.confidence_score), 4) AS confidence_score,
        SUM(r.evidence_count) AS evidence_count,
        COUNT(DISTINCT r.signal_family) AS source_diversity,
        MAX(r.observed_at) AS latest_observed_at,
        SUM(CASE WHEN r.quality_status <> 'usable' THEN 1 ELSE 0 END) AS quality_flag_count
    FROM risk_signal_scores r
    JOIN latest_run lr ON lr.id = r.scoring_run_id
    GROUP BY r.scoring_run_id, r.issue_key
),
latest_gap AS (
    SELECT g.*,
           ROW_NUMBER() OVER (PARTITION BY g.issue_key ORDER BY g.snapshot_at DESC, g.id DESC) AS rn
    FROM signal_gap_snapshots g
    JOIN latest_run lr ON lr.id = g.scoring_run_id
),
latest_alert AS (
    SELECT a.*,
           ROW_NUMBER() OVER (PARTITION BY a.issue_key ORDER BY a.triggered_at DESC, a.id DESC) AS rn
    FROM alert_events a
)
SELECT
    sr.issue_key,
    lr.run_key,
    lr.scoring_version,
    lr.executed_at AS scored_at,
    sr.risk_signal_score,
    sr.confidence_score,
    sr.evidence_count,
    sr.source_diversity,
    sr.latest_observed_at,
    sr.quality_flag_count,
    lg.gap_score,
    lg.evidence_coverage_pct,
    lg.narrative_summary AS signal_gap_summary,
    la.id AS alert_event_id,
    la.alert_level,
    la.lifecycle_status AS alert_status,
    la.triggered_at,
    la.requires_human_review,
    la.decision_rationale
FROM score_rollup sr
JOIN latest_run lr ON lr.id = sr.scoring_run_id
LEFT JOIN latest_gap lg ON lg.issue_key = sr.issue_key AND lg.rn = 1
LEFT JOIN latest_alert la ON la.issue_key = sr.issue_key AND la.rn = 1;


-- ----------------------------------------------------------------------------
-- 조기경보 증거 계층 뷰 2: 경보별 근거 추적
-- 한 행이 하나의 근거이므로, 화면은 이 뷰를 alert_event_id로 필터링해 인용문과
-- 원천 링크를 그대로 보여줄 수 있다.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_alert_evidence_trace AS
SELECT
    a.id AS alert_event_id,
    a.issue_key,
    a.alert_level,
    a.lifecycle_status AS alert_status,
    a.triggered_at,
    a.decision_rationale,
    sr.run_key,
    sr.scoring_version,
    e.id AS evidence_id,
    e.evidence_role,
    e.source_table,
    e.source_record_key,
    e.source_url,
    e.evidence_quote,
    e.relevance_score,
    e.observed_at,
    rs.signal_family,
    rs.metric_name,
    rs.raw_value,
    rs.normalized_score,
    rs.weight,
    rs.contribution_score,
    rs.confidence_score,
    rs.quality_status
FROM alert_events a
JOIN scoring_runs sr ON sr.id = a.scoring_run_id
LEFT JOIN alert_event_evidence e ON e.alert_event_id = a.id
LEFT JOIN risk_signal_scores rs ON rs.id = e.risk_signal_score_id;


-- ----------------------------------------------------------------------------
-- 조기경보 증거 계층 뷰 3: 신호 괴리 시계열
-- 공식/독립/대중/시장 신호와 근거 충분도를 같은 시점의 스냅샷으로 제공한다.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_signal_gap_trend AS
SELECT
    g.issue_key,
    g.snapshot_at,
    g.official_score,
    g.independent_score,
    g.public_score,
    g.market_score,
    g.gap_score,
    g.evidence_coverage_pct,
    g.source_diversity,
    g.methodology_version,
    g.narrative_summary,
    sr.run_key,
    sr.scoring_version
FROM signal_gap_snapshots g
JOIN scoring_runs sr ON sr.id = g.scoring_run_id;


-- ----------------------------------------------------------------------------
-- 조기경보 증거 계층 뷰 4: 검증 결과 요약
-- 톤 분류 정확도와 분리해, 실제 경보의 오탐/미탐/근거 부족을 집계한다.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_alert_validation_summary AS
SELECT
    v.issue_key,
    COALESCE(a.alert_level, 'NO_ALERT') AS alert_level,
    COUNT(*) AS audit_count,
    SUM(CASE WHEN v.verdict = 'confirmed' THEN 1 ELSE 0 END) AS confirmed_count,
    SUM(CASE WHEN v.verdict = 'false_alarm' THEN 1 ELSE 0 END) AS false_alarm_count,
    SUM(CASE WHEN v.verdict = 'missed_signal' THEN 1 ELSE 0 END) AS missed_signal_count,
    SUM(CASE WHEN v.verdict = 'insufficient_evidence' THEN 1 ELSE 0 END) AS insufficient_evidence_count,
    SUM(CASE WHEN v.reviewer IS NOT NULL THEN 1 ELSE 0 END) AS human_reviewed_count,
    ROUND(100.0 * SUM(CASE WHEN v.verdict = 'confirmed' THEN 1 ELSE 0 END)
          / NULLIF(SUM(CASE WHEN v.verdict IN ('confirmed', 'false_alarm') THEN 1 ELSE 0 END), 0), 1)
        AS alert_precision_pct,
    MAX(v.reviewed_at) AS last_reviewed_at
FROM alert_validation_audit v
LEFT JOIN alert_events a ON a.id = v.alert_event_id
GROUP BY v.issue_key, COALESCE(a.alert_level, 'NO_ALERT');
