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
                              panel_tech, tier, os, key_features, positioning)
           VALUES (%(bid)s, %(sn)s, %(mn)s, %(gy)s, %(pt)s, %(tier)s, %(os)s, %(kf)s, %(pos)s)
           ON CONFLICT (brand_id, series_name, generation_year) DO UPDATE SET
             marketing_name = COALESCE(EXCLUDED.marketing_name, series.marketing_name),
             panel_tech     = COALESCE(EXCLUDED.panel_tech, series.panel_tech),
             tier           = COALESCE(EXCLUDED.tier, series.tier),
             positioning    = COALESCE(EXCLUDED.positioning, series.positioning)
           RETURNING series_id""",
        {"bid": brand_id, "sn": rec.get("series_name"), "mn": rec.get("marketing_name"),
         "gy": _int(rec.get("generation_year")), "pt": rec.get("panel_tech"),
         "tier": rec.get("tier"), "os": rec.get("os"),
         "kf": _arr(rec.get("key_features")), "pos": rec.get("positioning")},
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
                               price_msrp, price_street, availability, source_url)
           VALUES (%(mid)s, %(sku)s, %(sz)s, %(rg)s, %(col)s, %(st)s, %(pb)s, %(ld)s,
                   %(wt)s, %(pw)s, %(msrp)s, %(street)s, %(av)s, %(url)s)
           ON CONFLICT (sku_full, region) DO UPDATE SET
             price_msrp   = COALESCE(EXCLUDED.price_msrp, variant.price_msrp),
             price_street = COALESCE(EXCLUDED.price_street, variant.price_street),
             availability = COALESCE(EXCLUDED.availability, variant.availability),
             updated_at   = now()
           RETURNING variant_id""",
        {"mid": model_id, "sku": rec["sku_full"], "sz": _int(rec.get("size_inch")),
         "rg": rec.get("region", "KR"), "col": rec.get("color"), "st": rec.get("stand_type"),
         "pb": _int(rec.get("peak_brightness_nits")), "ld": _int(rec.get("local_dimming_zones")),
         "wt": rec.get("weight_kg"), "pw": _int(rec.get("power_w")),
         "msrp": _int(rec.get("price_msrp")), "street": _int(rec.get("price_street")),
         "av": rec.get("availability"), "url": rec.get("source_url")},
    )
    return cur.fetchone()[0]


# ---------- Price history (append-only) ----------
def append_price(cur, variant_id: int, rec: dict):
    price = _int(rec.get("price_street") or rec.get("price_msrp"))
    if price is None:
        return
    cur.execute(
        """INSERT INTO price_history(variant_id, channel, price, currency)
           VALUES (%s, %s, %s, %s)""",
        (variant_id, rec.get("channel", rec.get("source", "unknown")),
         price, rec.get("currency", "KRW")),
    )
