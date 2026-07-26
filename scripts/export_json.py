"""
DB 스냅샷 파일 내보내기 — 검토/공유용.

산출물(data/exports/):
  tvspec_full.json    전체 모델(중첩: 브랜드→라인업→모델→옵션→가격)
  tvspec_sample.json  대표 6종만(스키마 감 잡기용)
  tvspec_models.csv   모델 평면표(엑셀 검토용)

실행:  ./.venv/bin/python -m scripts.export_json
"""
from __future__ import annotations
import csv
import json
import os
import datetime
import decimal
import pathlib

import psycopg
from psycopg.rows import dict_row

import provenance as prov

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")
OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "exports"
OUT.mkdir(parents=True, exist_ok=True)

SAMPLE_CODES = ["QN90F", "QN990F", "G5", "A95L", "U8Q", "QN90"]  # 플래그십 + 2026 잠정


def _default(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    if isinstance(o, decimal.Decimal):
        return float(o)
    return str(o)


def fetch_models(conn):
    cur = conn.cursor()
    cur.execute("""
        select b.name brand, s.marketing_name lineup, s.series_name,
               s.generation_year as "year", s.panel_tech, s.tier, s.os,
               s.positioning, s.key_features,
               m.model_id, m.model_code_base, m.resolution,
               m.refresh_rate_native, m.hdr_formats, m.processor, m.dimming,
               m.peak_brightness_nits, m.audio_channels, m.audio_output_w,
               m.smart_os_version, m.connectivity, m.gaming_features,
               m.size_variants_in, m.estimated_fields
        from model m
        join series s on m.series_id=s.series_id
        join brand b on s.brand_id=b.brand_id
        order by b.name, s.generation_year desc, m.model_code_base
    """)
    return cur.fetchall()


def fetch_variants(conn, model_id):
    cur = conn.cursor()
    cur.execute("""
        select v.variant_id, v.sku_full, v.size_inch, v.region, v.color,
               v.stand_type, v.os_override, v.panel_override, v.refresh_override,
               v.weight_kg, v.power_w,
               v.local_dimming_zones, v.audio_output_w,
               v.price_msrp, v.price_street, v.currency, v.availability, v.source_url,
               v.estimated_fields
        from variant v where v.model_id=%s order by v.region, v.size_inch
    """, (model_id,))
    variants = cur.fetchall()
    for v in variants:
        cur.execute("""
            select ph.channel, ph.price, ph.currency, ph.captured_at::date d
            from price_history ph where ph.variant_id=%s order by ph.captured_at
        """, (v.pop("variant_id"),))
        v["price_history"] = cur.fetchall()
    return variants


def build():
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        rows = fetch_models(conn)
        records = []
        for r in rows:
            mid = r.pop("model_id")
            r["variants"] = fetch_variants(conn, mid)
            r["measurement"] = fetch_measurement(conn, mid)
            r["certification"] = fetch_certification(conn, mid)
            r["region_names"] = fetch_aliases(conn, mid)
            r["features"] = fetch_features(conn, mid)
            records.append(r)
    return records


def fetch_features(conn, model_id):
    cur = conn.cursor()
    cur.execute("""select rank, category, feature, source from model_feature
                   where model_id=%s order by rank""", (model_id,))
    return cur.fetchall()


def fetch_aliases(conn, model_id):
    cur = conn.cursor()
    cur.execute("""select region, model_name, kind from model_alias
                   where model_id=%s order by region, kind""", (model_id,))
    return cur.fetchall()


def fetch_measurement(conn, model_id):
    cur = conn.cursor()
    cur.execute("""select peak_brightness_nits, fullscreen_nits, input_lag_ms,
                          dci_p3_pct, rec2020_pct, contrast, source, measured_date
                   from measurement where model_id=%s""", (model_id,))
    return cur.fetchone()


def fetch_certification(conn, model_id):
    cur = conn.cursor()
    cur.execute("""select energy_class_sdr, energy_class_hdr, power_sdr_w, power_hdr_w,
                          eprel_model, fcc_id, rra_id, source
                   from certification where model_id=%s""", (model_id,))
    return cur.fetchone()


def main():
    records = build()

    full = OUT / "tvspec_full.json"
    full.write_text(json.dumps(
        {"source": "tvspec", "generated_at": datetime.datetime.now().astimezone().isoformat(),
         "model_count": len(records), "provenance": prov.legend(), "records": records},
        ensure_ascii=False, indent=2, default=_default), encoding="utf-8")

    sample = [r for r in records if r["model_code_base"] in SAMPLE_CODES]
    (OUT / "tvspec_sample.json").write_text(json.dumps(
        {"note": "대표 샘플 — 전체는 tvspec_full.json", "provenance": prov.legend(),
         "records": sample},
        ensure_ascii=False, indent=2, default=_default), encoding="utf-8")

    csv_path = OUT / "tvspec_models.csv"
    cols = ["brand", "lineup", "year", "tier", "panel_tech", "model_code_base",
            "resolution", "refresh_rate_native", "peak_brightness_nits", "dimming",
            "processor", "audio_channels", "audio_output_w", "smart_os_version",
            "hdr_formats", "gaming_features", "connectivity", "key_features",
            "size_variants_in", "estimated_fields"]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in records:
            row = dict(r)
            for k in ("hdr_formats", "gaming_features", "connectivity", "key_features",
                      "estimated_fields", "size_variants_in"):
                if isinstance(row.get(k), list):
                    row[k] = ", ".join(str(x) for x in row[k])
            w.writerow(row)

    # variant(인치별) 평면 CSV — 사이즈·가격·물리스펙 한 행씩
    var_path = OUT / "tvspec_variants.csv"
    vcols = ["brand", "model_code_base", "lineup", "year", "panel_tech", "tier",
             "sku_full", "size_inch", "region", "weight_kg", "power_w",
             "local_dimming_zones", "audio_output_w", "price_msrp", "price_street",
             "currency", "availability", "estimated_fields"]
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        cur = conn.cursor()
        cur.execute("""
            select b.name brand, m.model_code_base, s.marketing_name lineup,
                   s.generation_year as "year", s.panel_tech, s.tier,
                   v.sku_full, v.size_inch, v.region, v.weight_kg, v.power_w,
                   v.local_dimming_zones, v.audio_output_w, v.price_msrp, v.price_street,
                   v.currency, v.availability, v.estimated_fields
            from variant v
            join model m on v.model_id=m.model_id
            join series s on m.series_id=s.series_id
            join brand b on s.brand_id=b.brand_id
            order by b.name, m.model_code_base, v.region, v.size_inch
        """)
        vrows = cur.fetchall()
    with var_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=vcols, extrasaction="ignore")
        w.writeheader()
        for r in vrows:
            row = dict(r)
            if isinstance(row.get("estimated_fields"), list):
                row["estimated_fields"] = ", ".join(row["estimated_fields"])
            w.writerow(row)

    print(f"모델 {len(records)}종 / 샘플 {len(sample)}종 / variant {len(vrows)}행 내보냄:")
    for p in (full, OUT / 'tvspec_sample.json', csv_path, var_path):
        print(f"  {p}  ({p.stat().st_size:,} B)")


if __name__ == "__main__":
    main()
