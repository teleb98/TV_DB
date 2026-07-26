-- =====================================================================
-- TV Spec DB — 4계층 스키마 (PostgreSQL)
-- Brand → Series(라인업) → Model → Variant(옵션)
-- + Comparison_Map(비교축), Canonical_Dict(정규화 사전), Price_History
-- 대상: 삼성 / LG / Sony / TCL / Hisense, 국내→북미, 최근 3년
-- =====================================================================

-- ---------- 열거형 ----------
CREATE TYPE panel_tech    AS ENUM ('OLED','WOLED','QD-OLED','QLED','Neo-QLED','Mini-LED','LED-LCD','Micro-LED');
CREATE TYPE dimming_type  AS ENUM ('none','edge-lit','full-array','mini-led','per-pixel');
CREATE TYPE tier          AS ENUM ('flagship','high','mid','entry');
CREATE TYPE smart_os      AS ENUM ('Tizen','webOS','Google-TV','Android-TV','Roku','VIDAA','Fire-TV','HarmonyOS','other');

-- ---------- 1. Brand ----------
CREATE TABLE brand (
    brand_id     SERIAL PRIMARY KEY,
    name         TEXT UNIQUE NOT NULL,          -- '삼성','LG','Sony','TCL','Hisense'
    country      TEXT,
    default_os   smart_os
);

-- ---------- 2. Series (라인업) ----------  → "라인업 안내봇" 소스
CREATE TABLE series (
    series_id       SERIAL PRIMARY KEY,
    brand_id        INT NOT NULL REFERENCES brand(brand_id),
    series_name     TEXT NOT NULL,              -- 내부 정규화명 'QN90'
    marketing_name  TEXT,                        -- 'Neo QLED 4K'
    generation_year INT,                         -- 세대(출시연도)
    panel_tech      panel_tech,
    tier            tier,
    os              smart_os,
    key_features    TEXT[],                      -- ['Anti-Glare','144Hz','Dolby Atmos']
    positioning     TEXT,                        -- 라인업 포지셔닝 설명(RAG용)
    UNIQUE (brand_id, series_name, generation_year)
);

-- ---------- 3. Model ----------  → "스펙 비교 상담봇" 소스
CREATE TABLE model (
    model_id            SERIAL PRIMARY KEY,
    series_id           INT NOT NULL REFERENCES series(series_id),
    model_code_base     TEXT NOT NULL,           -- 정규화 base 'QN90D'
    resolution          TEXT,                    -- '4K','8K'
    refresh_rate_native INT,                     -- 120,144 (네이티브만)
    hdr_formats         TEXT[],                  -- ['HDR10+','HLG','Dolby Vision']
    processor           TEXT,                    -- 'NQ4 AI Gen2'
    dimming             dimming_type,
    peak_brightness_nits INT,                    -- 대표값(인치별 override는 variant)
    audio_channels      TEXT,                    -- '4.2.2ch'
    audio_output_w      INT,
    smart_os_version    TEXT,
    connectivity        TEXT[],                  -- ['HDMI2.1 x4','eARC','WiFi6E','BT5.3']
    gaming_features     TEXT[],                  -- ['VRR','ALLM','G-Sync','FreeSync']
    size_variants_in    INT[],                   -- 제공 인치 목록(공식 사이트 확인). 예: {55,65,77,83,97}
    tuner               TEXT,                    -- ATSC 1.0/3.0, DVB 등 (DisplaySpecifications)
    vesa_mm             TEXT,                    -- VESA 마운트(예: 400x300)
    estimated_fields    TEXT[],                  -- 규칙기반 추정치인 컬럼명 목록(provenance.py 기준). 예: {audio_channels,audio_output_w}
    UNIQUE (series_id, model_code_base)
);

-- ---------- 4. Variant (옵션) ----------  → 옵션/가격/재고 답변
CREATE TABLE variant (
    variant_id          SERIAL PRIMARY KEY,
    model_id            INT NOT NULL REFERENCES model(model_id),
    sku_full            TEXT NOT NULL,           -- 정식 판매 모델명 'KQ65QNA90DXKR'
    size_inch           INT NOT NULL,
    region              TEXT DEFAULT 'KR',       -- 'KR','US'
    color               TEXT,
    stand_type          TEXT,                    -- 'stand','wall','pedestal'
    os_override         smart_os,                -- 지역별 OS 차이(예: Hisense US=Google-TV, KR=VIDAA). NULL이면 series.os 사용
    -- 인치별로 실제 달라지는 값(override) --
    peak_brightness_nits INT,
    local_dimming_zones  INT,
    weight_kg           NUMERIC(6,2),
    power_w             INT,
    audio_output_w      INT,
    -- 판매정보(스냅샷; 이력은 price_history) --
    price_msrp          INT,
    price_street        INT,
    currency            TEXT DEFAULT 'KRW',
    availability        TEXT,                    -- 'in_stock','eol','preorder'
    source_url          TEXT,
    panel_override      panel_tech,              -- 이 사이즈의 실제 패널(모델 기본과 다를 때, 예: S90 대형 WOLED)
    refresh_override    INT,                     -- 이 사이즈의 실제 주사율(예: 소형 60Hz)
    estimated_fields    TEXT[],                  -- 규칙기반 추정치인 컬럼명 목록. 예: {weight_kg,power_w,local_dimming_zones,color,stand_type}
    updated_at          TIMESTAMPTZ DEFAULT now(),
    UNIQUE (sku_full, region)
);

-- ---------- 5. Comparison_Map (비교축 · 부가가치 자산) ----------
CREATE TABLE comparison_map (
    map_id            SERIAL PRIMARY KEY,
    samsung_model_id  INT NOT NULL REFERENCES model(model_id),
    competitor_model_id INT NOT NULL REFERENCES model(model_id),
    tier_match        tier,
    price_band        TEXT,                      -- '200-300만'
    mapping_basis     TEXT,                      -- 'tier+price+panel'
    confidence        NUMERIC(3,2),              -- 0.00~1.00
    UNIQUE (samsung_model_id, competitor_model_id)
);

-- ---------- 6. Canonical_Dict (정규화 사전) ----------
CREATE TABLE canonical_dict (
    dict_id      SERIAL PRIMARY KEY,
    field        TEXT NOT NULL,                  -- 'panel_tech','refresh_rate','model_code'
    raw_term     TEXT NOT NULL,                  -- 'Neo QLED','120㎐','KQ65QNA90D'
    canonical    TEXT NOT NULL,                  -- 'Mini-LED','120','QN90D'
    UNIQUE (field, raw_term)
);

-- ---------- 7. Price_History (가격 이력) ----------
CREATE TABLE price_history (
    id           BIGSERIAL PRIMARY KEY,
    variant_id   INT NOT NULL REFERENCES variant(variant_id),
    channel      TEXT,                           -- 'danawa','coupang','samsung.com'
    price        INT,
    currency     TEXT DEFAULT 'KRW',
    captured_at  TIMESTAMPTZ DEFAULT now(),
    -- 동일 SKU·채널·시점 중복 방지(재적재 멱등). 일/주 스냅샷은 captured_at 이 달라 공존.
    UNIQUE (variant_id, channel, captured_at)
);

-- ---------- 8. Crawl_Queue (크롤 프론티어) ----------
CREATE TABLE crawl_queue (
    id           BIGSERIAL PRIMARY KEY,
    url          TEXT NOT NULL,
    source       TEXT NOT NULL,                  -- 'danawa','samsung_official',...
    priority     INT DEFAULT 5,                  -- 낮을수록 먼저
    status       TEXT DEFAULT 'pending',         -- pending|done|failed
    content_hash TEXT,                            -- 직전 원본 해시(변경감지)
    last_crawled TIMESTAMPTZ,
    next_due     TIMESTAMPTZ DEFAULT now(),       -- 다음 크롤 예정 시각
    fail_count   INT DEFAULT 0,
    UNIQUE (url, source)
);

-- ---------- 9. Crawl_Raw (원본 스냅샷 이력; 파일은 data/raw/) ----------
CREATE TABLE crawl_raw (
    id           BIGSERIAL PRIMARY KEY,
    url          TEXT NOT NULL,
    source       TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    path         TEXT,                            -- data/raw/ 파일 경로
    fetched_at   TIMESTAMPTZ DEFAULT now()
);

-- ---------- 10. Measurement (RTINGS 등 실측 성능; 모델당 1행) ----------
CREATE TABLE measurement (
    model_id             INT PRIMARY KEY REFERENCES model(model_id) ON DELETE CASCADE,
    peak_brightness_nits INT,            -- 실측 HDR 피크(10% window)
    fullscreen_nits      INT,            -- 실측 전체화면 밝기
    input_lag_ms         NUMERIC(5,1),   -- 4K@120Hz 근사
    dci_p3_pct           NUMERIC(4,1),
    rec2020_pct          NUMERIC(4,1),
    contrast             TEXT,           -- 네이티브 명암비 or 'inf'(OLED)
    source               TEXT DEFAULT 'rtings',  -- rtings/flatpanelshd/avforums 등
    measured_date        DATE,
    updated_at           TIMESTAMPTZ DEFAULT now()
);

-- ---------- 11. Certification (EPREL 에너지·FCC·RRA 인증; 모델당 1행) ----------
CREATE TABLE certification (
    model_id         INT PRIMARY KEY REFERENCES model(model_id) ON DELETE CASCADE,
    energy_class_sdr TEXT,     -- A~G (EU EPREL, SDR)
    energy_class_hdr TEXT,     -- A~G (HDR)
    power_sdr_w      INT,      -- SDR On-mode 소비전력(W)
    power_hdr_w      INT,      -- HDR On-mode 소비전력(W)
    eprel_model      TEXT,     -- EPREL 등록 모델명(EU SKU, 파생명 매핑)
    fcc_id           TEXT,     -- 미 FCC ID
    rra_id           TEXT,     -- 한국 전파인증(RRA) 번호
    source           TEXT DEFAULT 'eprel',
    updated_at       TIMESTAMPTZ DEFAULT now()
);

-- ---------- 12. Model_Alias (지역별 모델명 매핑; Base_Model → Region_Model_Name) ----------
CREATE TABLE model_alias (
    id         BIGSERIAL PRIMARY KEY,
    model_id   INT NOT NULL REFERENCES model(model_id) ON DELETE CASCADE,
    region     TEXT NOT NULL,          -- KR/US/EU/Global
    model_name TEXT NOT NULL,          -- 지역 모델명/SKU 루트
    kind       TEXT DEFAULT 'sku_root',-- sku_root / eprel / marketing
    UNIQUE (model_id, region, model_name)
);
CREATE INDEX idx_alias_model ON model_alias(model_id);
CREATE INDEX idx_alias_name  ON model_alias(model_name);

-- ---------- 13. Model_Feature (브랜드 마케팅 feature; 우선순위 순, rank1=제품페이지 최상단) ----------
CREATE TABLE model_feature (
    id       BIGSERIAL PRIMARY KEY,
    model_id INT NOT NULL REFERENCES model(model_id) ON DELETE CASCADE,
    rank     INT NOT NULL,            -- 1=최상단(가장 중요) … n
    category TEXT,                    -- picture·performance·gaming·sound·ai·design·service·experience
    feature  TEXT NOT NULL,           -- 브랜드 표기 기능명
    source   TEXT DEFAULT 'brand-site',
    UNIQUE (model_id, rank)
);
CREATE INDEX idx_feature_model ON model_feature(model_id, rank);

-- ---------- 인덱스 ----------
CREATE INDEX idx_queue_due  ON crawl_queue(status, next_due);
CREATE INDEX idx_raw_url    ON crawl_raw(url, fetched_at DESC);
CREATE INDEX idx_series_brand   ON series(brand_id);
CREATE INDEX idx_model_series   ON model(series_id);
CREATE INDEX idx_variant_model  ON variant(model_id);
CREATE INDEX idx_variant_sku    ON variant(sku_full);
CREATE INDEX idx_pricehist_var  ON price_history(variant_id, captured_at DESC);
