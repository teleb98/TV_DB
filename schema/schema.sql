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
CREATE TYPE smart_os      AS ENUM ('Tizen','webOS','Google-TV','Android-TV','Roku','VIDAA','Fire-TV','other');
CREATE TYPE product_status AS ENUM ('announced','released','eol');   -- 수명주기: 발표/출시/단종

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
    status          product_status DEFAULT 'released',  -- 발표/출시/단종
    data_confidence TEXT DEFAULT 'high',         -- high|med|low (잠정 데이터 구분)
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

-- ---------- 인덱스 ----------
CREATE INDEX idx_series_brand   ON series(brand_id);
CREATE INDEX idx_model_series   ON model(series_id);
CREATE INDEX idx_variant_model  ON variant(model_id);
CREATE INDEX idx_variant_sku    ON variant(sku_full);
CREATE INDEX idx_pricehist_var  ON price_history(variant_id, captured_at DESC);
