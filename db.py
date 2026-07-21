"""
4계층 upsert 계층 (psycopg3, PostgreSQL).
FK 순서 해소: brand → series → model → variant → price_history.
모두 ON CONFLICT DO UPDATE (schema.sql 의 UNIQUE 제약과 정합).
연결: 환경변수 PG_DSN (예: 'postgresql://user@localhost/tvspec').
"""
from __future__ import annotations
import os
import psycopg   # psycopg3

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")


def connect():
    return psycopg.connect(DSN, autocommit=False)


def _arr(v):
    """'a|b|c' 또는 list → PostgreSQL 배열 리터럴용 list."""
    if v is None or v == "":
        return None
    return v.split("|") if isinstance(v, str) else list(v)


def _int(v):
    try:
        return int(v) if v not in (None, "") else None
    except (ValueError, TypeError):
        return None


# ---------- Brand ----------
def upsert_brand(cur, rec: dict) -> int:
    cur.execute(
        """INSERT INTO brand(name, country, default_os)
           VALUES (%(name)s, %(country)s, %(default_os)s)
           ON CONFLICT (name) DO UPDATE SET country = COALESCE(EXCLUDED.country, brand.country)
           RETURNING brand_id""",
        {"name": rec["brand"], "country": rec.get("country"),
         "default_os": rec.get("os")},
    )
    return cur.fetchone()[0]


# ---------- Series ----------
def upsert_series(cur, rec: dict, brand_id: int) -> int:
    cur.execute(
        """INSERT INTO series(brand_id, series_name, marketing_name, generation_year,
                              panel_tech, tier, os, key_features, positioning,
                              status, data_confidence)
           VALUES (%(bid)s, %(sn)s, %(mn)s, %(gy)s, %(pt)s, %(tier)s, %(os)s, %(kf)s, %(pos)s,
                   COALESCE(%(st)s::product_status, 'released'), COALESCE(%(dc)s, 'high'))
           ON CONFLICT (brand_id, series_name, generation_year) DO UPDATE SET
             marketing_name = COALESCE(EXCLUDED.marketing_name, series.marketing_name),
             panel_tech     = COALESCE(EXCLUDED.panel_tech, series.panel_tech),
             tier           = COALESCE(EXCLUDED.tier, series.tier),
             positioning    = COALESCE(EXCLUDED.positioning, series.positioning),
             status         = EXCLUDED.status,
             data_confidence = EXCLUDED.data_confidence
           RETURNING series_id""",
        {"bid": brand_id, "sn": rec.get("series_name"), "mn": rec.get("marketing_name"),
         "gy": _int(rec.get("generation_year")), "pt": rec.get("panel_tech"),
         "tier": rec.get("tier"), "os": rec.get("os"),
         "kf": _arr(rec.get("key_features")), "pos": rec.get("positioning"),
         "st": rec.get("status"), "dc": rec.get("data_confidence")},
    )
    return cur.fetchone()[0]


# ---------- Model ----------
def upsert_model(cur, rec: dict, series_id: int) -> int:
    cur.execute(
        """INSERT INTO model(series_id, model_code_base, resolution, refresh_rate_native,
                             hdr_formats, processor, dimming, peak_brightness_nits,
                             audio_channels, smart_os_version, connectivity, gaming_features)
           VALUES (%(sid)s, %(mc)s, %(res)s, %(rr)s, %(hdr)s, %(proc)s, %(dim)s, %(pb)s,
                   %(ac)s, %(osv)s, %(conn)s, %(game)s)
           ON CONFLICT (series_id, model_code_base) DO UPDATE SET
             resolution          = COALESCE(EXCLUDED.resolution, model.resolution),
             refresh_rate_native = COALESCE(EXCLUDED.refresh_rate_native, model.refresh_rate_native),
             hdr_formats         = COALESCE(EXCLUDED.hdr_formats, model.hdr_formats),
             processor           = COALESCE(EXCLUDED.processor, model.processor),
             dimming             = COALESCE(EXCLUDED.dimming, model.dimming),
             peak_brightness_nits = COALESCE(EXCLUDED.peak_brightness_nits, model.peak_brightness_nits)
           RETURNING model_id""",
        {"sid": series_id, "mc": rec.get("model_code_base"), "res": rec.get("resolution"),
         "rr": _int(rec.get("refresh_rate_native")), "hdr": _arr(rec.get("hdr_formats")),
         "proc": rec.get("processor"), "dim": rec.get("dimming"),
         "pb": _int(rec.get("peak_brightness_nits")), "ac": rec.get("audio_channels"),
         "osv": rec.get("smart_os_version"), "conn": _arr(rec.get("connectivity")),
         "game": _arr(rec.get("gaming_features"))},
    )
    return cur.fetchone()[0]


# ---------- Variant ----------
def upsert_variant(cur, rec: dict, model_id: int) -> int:
    cur.execute(
        """INSERT INTO variant(model_id, sku_full, size_inch, region, color, stand_type,
                               peak_brightness_nits, local_dimming_zones, weight_kg, power_w,
                               price_msrp, price_street, currency, os_override, availability, source_url)
           VALUES (%(mid)s, %(sku)s, %(sz)s, %(rg)s, %(col)s, %(st)s, %(pb)s, %(ld)s,
                   %(wt)s, %(pw)s, %(msrp)s, %(street)s,
                   COALESCE(%(cur)s, CASE WHEN %(rg)s='US' THEN 'USD' ELSE 'KRW' END),
                   %(osov)s, %(av)s, %(url)s)
           ON CONFLICT (sku_full, region) DO UPDATE SET
             price_msrp   = COALESCE(EXCLUDED.price_msrp, variant.price_msrp),
             price_street = COALESCE(EXCLUDED.price_street, variant.price_street),
             os_override  = COALESCE(EXCLUDED.os_override, variant.os_override),
             availability = COALESCE(EXCLUDED.availability, variant.availability),
             updated_at   = now()
           RETURNING variant_id""",
        {"mid": model_id, "sku": rec["sku_full"], "sz": _int(rec.get("size_inch")),
         "rg": rec.get("region", "KR"), "col": rec.get("color"), "st": rec.get("stand_type"),
         "pb": _int(rec.get("peak_brightness_nits")), "ld": _int(rec.get("local_dimming_zones")),
         "wt": rec.get("weight_kg"), "pw": _int(rec.get("power_w")),
         "msrp": _int(rec.get("price_msrp")), "street": _int(rec.get("price_street")),
         "cur": rec.get("currency"), "osov": rec.get("os_override") or None,
         "av": rec.get("availability"), "url": rec.get("source_url")},
    )
    return cur.fetchone()[0]


# ---------- 조회 헬퍼 ----------
def resolve_model_id(cur, model_code_base: str) -> int | None:
    """model_code_base 로 model_id 조회(수집기 variant 적재 시 부모 모델 연결용)."""
    cur.execute("select model_id from model where model_code_base = %s limit 1",
                (model_code_base,))
    row = cur.fetchone()
    return row[0] if row else None


def resolve_variant_id(cur, sku_full: str, region: str = "KR") -> int | None:
    """정식 SKU + 지역으로 variant_id 조회(가격 스냅샷 연결용)."""
    cur.execute("select variant_id from variant where sku_full = %s and region = %s",
                (sku_full, region))
    row = cur.fetchone()
    return row[0] if row else None


def upsert_price_snapshot(cur, variant_id: int, channel: str, price: int,
                          captured_at: str | None = None, currency: str = "KRW"):
    """price_history 에 스냅샷 append + variant.price_street 를 최신가로 동기화.
    captured_at(ISO 날짜) 지정 시 이력의 시점을 명시(트렌드 축적용)."""
    if captured_at:
        cur.execute("""insert into price_history(variant_id, channel, price, currency, captured_at)
                       values (%s,%s,%s,%s,%s)
                       on conflict (variant_id, channel, captured_at) do update
                         set price = excluded.price""",
                    (variant_id, channel, price, currency, captured_at))
    else:
        cur.execute("""insert into price_history(variant_id, channel, price, currency)
                       values (%s,%s,%s,%s)""", (variant_id, channel, price, currency))
    # variant 의 현재가는 '가장 최근 캡처' 기준으로 갱신
    cur.execute("""
        update variant v set price_street = ph.price, updated_at = now()
        from (select price from price_history where variant_id=%s
              order by captured_at desc limit 1) ph
        where v.variant_id=%s
    """, (variant_id, variant_id))

