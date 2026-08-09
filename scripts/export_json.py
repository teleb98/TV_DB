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
               s.positioning, s.key_features, m.backlight_tech,
               m.model_id, m.model_code_base, m.resolution,
               m.refresh_rate_native, m.hdr_formats, m.processor, m.dimming,
               m.peak_brightness_nits, m.brightness_source, m.audio_channels, m.audio_output_w,
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


_OS_EXP_CACHE: dict = {}


def fetch_os_experience(conn, os_name):
    """series.os → os_platform 요약(모델에 연결). 캐시로 OS당 1회 조회."""
    key = str(os_name) if os_name is not None else None
    if key in _OS_EXP_CACHE:
        return _OS_EXP_CACHE[key]
    exp = None
    if key:
        cur = conn.cursor()
        cur.execute("""select os, base_os, voice_assistant, fast_service, casting, airplay,
                              cloud_gaming, smart_home, matter, update_policy, ad_level,
                              strengths, best_for
                       from os_platform where os=%s""", (key,))
        exp = cur.fetchone()
        if exp and isinstance(exp.get("strengths"), list):
            exp["top_strengths"] = exp["strengths"][:3]
    _OS_EXP_CACHE[key] = exp
    return exp


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
            r["os_experience"] = fetch_os_experience(conn, r.get("os"))
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
    cols = ["brand", "lineup", "year", "tier", "panel_tech", "backlight_tech", "model_code_base",
            "resolution", "refresh_rate_native", "peak_brightness_nits", "brightness_source", "dimming",
            "processor", "audio_channels", "audio_output_w", "smart_os_version",
            "hdr_formats", "gaming_features", "connectivity", "key_features",
            "size_variants_in", "estimated_fields",
            # OS 플랫폼 연결(os_platform 조인) — 모델별 OS 경험
            "os", "os_base", "os_voice", "os_fast", "os_cloud_gaming", "os_airplay",
            "os_ad_level", "os_top_strength"]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in records:
            row = dict(r)
            for k in ("hdr_formats", "gaming_features", "connectivity", "key_features",
                      "estimated_fields", "size_variants_in"):
                if isinstance(row.get(k), list):
                    row[k] = ", ".join(str(x) for x in row[k])
            oe = row.get("os_experience") or {}
            row["os_base"] = oe.get("base_os")
            row["os_voice"] = oe.get("voice_assistant")
            row["os_fast"] = oe.get("fast_service")
            row["os_cloud_gaming"] = oe.get("cloud_gaming")
            row["os_airplay"] = oe.get("airplay")
            row["os_ad_level"] = oe.get("ad_level")
            row["os_top_strength"] = "; ".join(oe.get("top_strengths") or [])
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

    # 미출시 사전정보(뉴스 확인, 기존 DB에 없는 신모델) — 별도 파일로 분리 관리
    pr_json = OUT / "tvspec_pre_release.json"
    pr_csv = OUT / "tvspec_pre_release.csv"
    pcols = ["brand", "tentative_model", "category", "expected_year", "confidence",
             "corroboration", "source_country", "source_tier", "source_org", "status",
             "spec_summary", "source_url", "report_date", "note"]
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        cur = conn.cursor()
        cur.execute(f"""select {', '.join(pcols)} from pre_release_intel
                        order by array_position(array['high','med','low']::text[], confidence),
                                 expected_year, brand""")
        prows = cur.fetchall()
    pr_json.write_text(json.dumps(
        {"note": "미출시/루머 사전정보 — 주요국 뉴스·공급망·인증DB 확인. 기존 사양 DB(model)에 없는 신모델만.",
         "generated_at": datetime.datetime.now().astimezone().isoformat(), "records": prows},
        ensure_ascii=False, indent=2, default=_default), encoding="utf-8")
    with pr_csv.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=pcols, extrasaction="ignore")
        w.writeheader()
        for r in prows:
            w.writerow({k: r.get(k) for k in pcols})

    # 스마트TV OS 시장점유율(업계 리서치) — DB 모델수와 별개인 시장통계
    os_json = OUT / "tvspec_os_share.json"
    os_csv = OUT / "tvspec_os_share.csv"
    ocols = ["region", "metric", "period", "rank", "os", "vendor", "share_pct",
             "estimated", "source_org", "source_url", "note"]
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        cur = conn.cursor()
        cur.execute(f"""select {', '.join(ocols)} from os_market_share
                        order by region, metric, period, rank, share_pct desc""")
        orows = cur.fetchall()
        cur.execute("""select s.os::text os, count(distinct m.model_id) db_models,
                              string_agg(distinct b.name, ', ' order by b.name) brands
                       from model m join series s on m.series_id=s.series_id
                       join brand b on s.brand_id=b.brand_id
                       group by s.os::text order by db_models desc""")
        ocov = cur.fetchall()
    os_json.write_text(json.dumps(
        {"note": "스마트TV OS 시장점유율(Omdia 등 업계 리서치). market_share=시장통계, "
                 "db_coverage=본 DB 보유 모델수(별개). estimated=true는 공개치 없이 밴드중앙/잔여 보정.",
         "generated_at": datetime.datetime.now().astimezone().isoformat(),
         "market_share": orows, "db_coverage": ocov},
        ensure_ascii=False, indent=2, default=_default), encoding="utf-8")
    with os_csv.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=ocols, extrasaction="ignore")
        w.writeheader()
        for r in orows:
            w.writerow({k: r.get(k) for k in ocols})

    # OS 플랫폼 프로파일(장점·약점·사양) — model 스펙과 분리된 OS 자체 특성
    osp_json = OUT / "tvspec_os_profile.json"
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        cur = conn.cursor()
        cur.execute("""
            select p.*,
                   (select count(distinct m.model_id) from series s
                      join model m on m.series_id=s.series_id where s.os::text=p.os) db_models,
                   (select string_agg(distinct b.name, ', ' order by b.name) from series s
                      join brand b on s.brand_id=b.brand_id where s.os::text=p.os) brands
            from os_platform p
            order by db_models desc, p.os
        """)
        oprows = cur.fetchall()
    osp_json.write_text(json.dumps(
        {"note": "스마트TV OS 플랫폼 프로파일 — OS 자체의 장점·약점·사양(음성비서·FAST·클라우드게임·"
                 "AirPlay·스마트홈·업데이트·광고강도). 개별 model 스펙과 분리. db_models=본 DB 보유 모델수.",
         "generated_at": datetime.datetime.now().astimezone().isoformat(), "platforms": oprows},
        ensure_ascii=False, indent=2, default=_default), encoding="utf-8")

    # IT 커뮤니티 관심/화제 모델 — 정성 여론 신호(모델 스펙과 별개)
    buzz_json = OUT / "tvspec_community_buzz.json"
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        cur = conn.cursor()
        cur.execute("""
            select cb.model_code, b.name brand, s.marketing_name lineup,
                   s.generation_year as "year", s.panel_tech, s.tier,
                   count(*) mentions,
                   sum(case cb.interest when 'very-high' then 3 when 'high' then 2 else 1 end) buzz_score,
                   string_agg(distinct cb.community, ',' order by cb.community) communities
            from community_buzz cb
            left join model m on m.model_code_base=cb.model_code
            left join series s on m.series_id=s.series_id
            left join brand b on s.brand_id=b.brand_id
            group by cb.model_code, b.name, s.marketing_name, s.generation_year, s.panel_tech, s.tier
            order by buzz_score desc, mentions desc
        """)
        branking = cur.fetchall()
        cur.execute("""select model_code, community, region, interest, rank, buzz_reason,
                              source_url, as_of from community_buzz
                       order by array_position(array['very-high','high','medium']::text[], interest),
                                model_code""")
        bdetail = cur.fetchall()
    buzz_json.write_text(json.dumps(
        {"note": "IT 커뮤니티 관심/화제 모델 — 여론 기반 정성 신호(하드 판매지표 아님). "
                 "출처: Reddit r/4kTV·AVSForum·RTINGS·한국 커뮤니티. buzz_score=very-high3·high2·medium1 가중합.",
         "generated_at": datetime.datetime.now().astimezone().isoformat(),
         "ranking": branking, "detail": bdetail},
        ensure_ascii=False, indent=2, default=_default), encoding="utf-8")

    print(f"모델 {len(records)}종 / 샘플 {len(sample)}종 / variant {len(vrows)}행 / "
          f"사전정보 {len(prows)}건 / OS점유율 {len(orows)}행 / OS프로파일 {len(oprows)}개 / "
          f"커뮤니티화제 {len(branking)}종 내보냄:")
    for p in (full, OUT / 'tvspec_sample.json', csv_path, var_path, pr_json, pr_csv,
              os_json, os_csv, osp_json, buzz_json):
        print(f"  {p}  ({p.stat().st_size:,} B)")


if __name__ == "__main__":
    main()
