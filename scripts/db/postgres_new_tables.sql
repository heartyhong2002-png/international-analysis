-- PostgreSQL-native tables for newly collected & preprocessed datasets
-- Uses JSONB + GIN indexes for 5W1H tuples, multilingual tags, and GeoJSON properties.

-- 1. Semiconductor Equities & Indices (SOX, NVDA, TSMC, ASML, AMAT, LRCX, KLAC, etc.)
CREATE TABLE IF NOT EXISTS semiconductor_equities (
    ticker VARCHAR(30) NOT NULL,
    observed_date VARCHAR(20) NOT NULL,
    category VARCHAR(100),
    name VARCHAR(200),
    role TEXT,
    currency VARCHAR(10),
    latest_price DOUBLE PRECISION,
    day_change_pct DOUBLE PRECISION,
    week_change_pct DOUBLE PRECISION,
    month_change_pct DOUBLE PRECISION,
    status_signal VARCHAR(100),
    collected_at_utc VARCHAR(50),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticker, observed_date)
);

-- 2. Semiconductor Memory Spot Prices (DRAM / GDDR / NAND)
CREATE TABLE IF NOT EXISTS semiconductor_memory_spot (
    item VARCHAR(200) NOT NULL,
    collected_date VARCHAR(20) NOT NULL,
    daily_high_usd DOUBLE PRECISION,
    daily_low_usd DOUBLE PRECISION,
    session_avg_usd DOUBLE PRECISION,
    session_change VARCHAR(50),
    source VARCHAR(100),
    collected_at_utc VARCHAR(50),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (item, collected_date)
);

-- 3. Bluesky Tech / Security / Regulation Public Signals
CREATE TABLE IF NOT EXISTS bluesky_signals (
    post_uri TEXT PRIMARY KEY,
    source_id VARCHAR(100),
    source_type VARCHAR(50),
    signal_class VARCHAR(50),
    verification_state VARCHAR(50),
    query_matched VARCHAR(200),
    issue_tags JSONB DEFAULT '[]'::jsonb,
    chokepoint_tag VARCHAR(100),
    commodity_tag VARCHAR(100),
    post_url TEXT,
    author_did VARCHAR(150),
    author_handle VARCHAR(150),
    author_display_name VARCHAR(255),
    language VARCHAR(20),
    text TEXT,
    external_link TEXT,
    external_title TEXT,
    media_urls JSONB DEFAULT '[]'::jsonb,
    alt_texts JSONB DEFAULT '[]'::jsonb,
    has_video BOOLEAN DEFAULT FALSE,
    has_media BOOLEAN DEFAULT FALSE,
    like_count INTEGER DEFAULT 0,
    repost_count INTEGER DEFAULT 0,
    reply_count INTEGER DEFAULT 0,
    published_at VARCHAR(60),
    observed_at VARCHAR(60),
    content_hash CHAR(64),
    license_access_note VARCHAR(255),
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_bluesky_published ON bluesky_signals (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_bluesky_issue_tags ON bluesky_signals USING GIN (issue_tags);

-- 4. Canonical Preprocessed Signals (5W1H Event Tuples + ISO-639 Multilingual Clustering)
CREATE TABLE IF NOT EXISTS canonical_signals (
    signal_id VARCHAR(100) PRIMARY KEY,
    cluster_id VARCHAR(50),
    representative_title TEXT,
    canonical_title TEXT,
    url TEXT,
    cluster_size INTEGER DEFAULT 1,
    unique_sources_count INTEGER DEFAULT 1,
    sources JSONB DEFAULT '[]'::jsonb,
    source_types JSONB DEFAULT '[]'::jsonb,
    observed_lanes JSONB DEFAULT '[]'::jsonb,
    primary_language VARCHAR(20),
    detected_languages JSONB DEFAULT '[]'::jsonb,
    is_cross_lingual BOOLEAN DEFAULT FALSE,
    purity_tier VARCHAR(50),
    relevance_score DOUBLE PRECISION,
    -- Promoted 5W1H query fields + full JSONB tuple
    who_code VARCHAR(100),
    action_code VARCHAR(100),
    target_code VARCHAR(100),
    threat_severity VARCHAR(50),
    event_tuple JSONB DEFAULT '{}'::jsonb,
    chokepoints JSONB DEFAULT '[]'::jsonb,
    supply_chain_tags JSONB DEFAULT '[]'::jsonb,
    event_types JSONB DEFAULT '[]'::jsonb,
    hotspot_regions JSONB DEFAULT '[]'::jsonb,
    has_visual_media BOOLEAN DEFAULT FALSE,
    visual_modalities JSONB DEFAULT '[]'::jsonb,
    media_attachments JSONB DEFAULT '[]'::jsonb,
    visual_alt_texts JSONB DEFAULT '[]'::jsonb,
    visual_verification_state VARCHAR(50),
    published_at VARCHAR(60),
    verification_state VARCHAR(50),
    alert_level_set BOOLEAN DEFAULT FALSE,
    preprocessed_at VARCHAR(60),
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_canonical_purity_tier ON canonical_signals (purity_tier);
CREATE INDEX IF NOT EXISTS idx_canonical_threat_severity ON canonical_signals (threat_severity);
CREATE INDEX IF NOT EXISTS idx_canonical_primary_lang ON canonical_signals (primary_language);
CREATE INDEX IF NOT EXISTS idx_canonical_event_tuple ON canonical_signals USING GIN (event_tuple);

-- 5. Federal Register Official Documents
CREATE TABLE IF NOT EXISTS federal_register_docs (
    document_number VARCHAR(100) PRIMARY KEY,
    source_id VARCHAR(100),
    relationship_role VARCHAR(50),
    packet VARCHAR(50),
    title TEXT,
    publication_date VARCHAR(30),
    agencies JSONB DEFAULT '[]'::jsonb,
    action TEXT,
    doc_type VARCHAR(100),
    executive_order_number VARCHAR(50),
    abstract TEXT,
    html_url TEXT,
    pdf_url TEXT,
    issue_tags JSONB DEFAULT '[]'::jsonb,
    content_hash CHAR(64),
    observed_at VARCHAR(60),
    license_access_note VARCHAR(255),
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_fedreg_pub_date ON federal_register_docs (publication_date DESC);

-- 6. US Congress.gov Official Documents
CREATE TABLE IF NOT EXISTS congress_gov_docs (
    document_id VARCHAR(150) PRIMARY KEY,
    source_id VARCHAR(100),
    relationship_role VARCHAR(50),
    packet VARCHAR(50),
    doc_type VARCHAR(100),
    congress VARCHAR(30),
    chamber VARCHAR(50),
    title TEXT,
    publication_date VARCHAR(30),
    latest_action TEXT,
    summary TEXT,
    source_url TEXT,
    api_url TEXT,
    issue_tags JSONB DEFAULT '[]'::jsonb,
    content_hash CHAR(64),
    observed_at VARCHAR(60),
    license_access_note VARCHAR(255),
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_congress_pub_date ON congress_gov_docs (publication_date DESC);

-- 7. US GovInfo Official Documents
CREATE TABLE IF NOT EXISTS govinfo_docs (
    package_id VARCHAR(150) PRIMARY KEY,
    source_id VARCHAR(100),
    relationship_role VARCHAR(50),
    packet VARCHAR(50),
    collection_code VARCHAR(50),
    doc_type VARCHAR(100),
    doc_class VARCHAR(100),
    congress VARCHAR(30),
    title TEXT,
    publication_date VARCHAR(30),
    last_modified VARCHAR(60),
    summary TEXT,
    source_url TEXT,
    pdf_url TEXT,
    api_url TEXT,
    issue_tags JSONB DEFAULT '[]'::jsonb,
    content_hash CHAR(64),
    observed_at VARCHAR(60),
    license_access_note VARCHAR(255),
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_govinfo_pub_date ON govinfo_docs (publication_date DESC);

-- 8. Spatial / Geocoded Geopolitical Signals (from GeoJSON)
CREATE TABLE IF NOT EXISTS spatial_signals (
    signal_id VARCHAR(100) NOT NULL,
    place_name VARCHAR(200) NOT NULL,
    title TEXT,
    purity_tier VARCHAR(50),
    unique_sources INTEGER DEFAULT 1,
    geo_method VARCHAR(50),
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    properties JSONB DEFAULT '{}'::jsonb,
    geometry JSONB DEFAULT '{}'::jsonb,
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (signal_id, place_name)
);
CREATE INDEX IF NOT EXISTS idx_spatial_purity ON spatial_signals (purity_tier);
CREATE INDEX IF NOT EXISTS idx_spatial_coords ON spatial_signals (latitude, longitude);
