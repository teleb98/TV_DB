"""
빈 필드 일괄 보강 (규칙 기반·재현 가능·멱등). 기존 값은 덮지 않음(WHERE ... IS NULL).

두 종류를 구분해 채운다:
  A) 결정적 도출값(신뢰 높음): brand.country, model.smart_os_version(브랜드+연도),
     series.key_features(모델 스펙에서 파생), variant.availability/source_url,
     comparison_map.price_band(tier_match 파생).
  B) 티어/사이즈 기반 대표 추정치(공식 대조 검수 전제): model.audio_channels/audio_output_w,
     variant.weight_kg/power_w/local_dimming_zones/color/stand_type.
     → 무게 0.5kg·전력 10W 단위로 반올림해 '근사치'임을 드러냄.

실행:  ./.venv/bin/python -m scripts.enrich_fill_empties
"""
from __future__ import annotations
import os
import psycopg

import provenance as prov

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")

COUNTRY = {"삼성": "대한민국", "LG": "대한민국", "Sony": "일본", "TCL": "중국",
           "Hisense": "중국", "Huawei": "중국", "Xiaomi": "중국"}
COLOR = {"삼성": "Titan Black", "LG": "Black", "Sony": "Black", "TCL": "Black",
         "Hisense": "Black", "Huawei": "Black", "Xiaomi": "Black"}
SRC = {"삼성": "https://www.samsung.com", "LG": "https://www.lge.co.kr",
       "Sony": "https://www.sony.co.kr", "TCL": "https://www.tcl.com",
       "Hisense": "https://www.hisense.com", "Huawei": "https://consumer.huawei.com",
       "Xiaomi": "https://www.mi.com"}
OLED = ("WOLED", "QD-OLED", "OLED")


def os_version(brand, year):
    if brand == "삼성":
        return {2023: "Tizen 7.0", 2024: "Tizen 8.0", 2025: "Tizen 9.0", 2026: "Tizen 10.0"}.get(year, "Tizen")
    if brand == "LG":
        return f"webOS {str(year)[2:]}" if year else "webOS"
    if brand in ("Sony", "TCL", "Xiaomi"):
        return "Google TV"
    if brand == "Hisense":
        return "VIDAA U"
    if brand == "Huawei":
        return "HarmonyOS 4"
    return None


def audio(brand, tier, res, panel):
    """(채널, 출력W) — 브랜드·티어·해상도 기반 대표값."""
    if res == "8K":
        return "6.2.4", 90
    if tier == "flagship":
        if brand == "삼성":
            return "4.2.2", 70
        if brand == "LG":
            return ("4.2", 60) if panel in OLED else ("2.2", 40)
        if brand == "Sony":
            return "2.2", 70
        return "2.1.2", 60           # TCL/Hisense/Huawei flagship (내장 우퍼)
    if tier == "high":
        return "2.2", 40
    return "2.0", 20                 # mid/entry


def weight(size, panel):
    base = size * 0.35
    if panel in OLED:
        base *= 0.82
    return round(base * 2) / 2       # 0.5kg 단위 (근사)


def power(size, panel):
    f = 3.0 if panel == "Mini-LED" else (2.3 if panel in OLED else 2.6)
    return int(round(size * f / 10) * 10)   # 10W 단위 (근사, 일반사용)


def zones(tier, dimming):
    if dimming == "mini-led":
        return {"flagship": 1344, "high": 512, "mid": 256}.get(tier, 256)
    if dimming == "full-array":
        return {"flagship": 128, "high": 64, "mid": 48}.get(tier, 48)
    return None                      # per-pixel(OLED)·edge-lit·none → 해당없음


def key_features(panel, refresh, nits, hdr, gaming):
    f = []
    if panel:
        f.append(panel)
    if refresh:
        f.append(f"{refresh}Hz")
    if nits and nits >= 2000:
        f.append("고휘도(2000nit+)")
    hdr = hdr or []
    if "Dolby Vision" in hdr:
        f.append("Dolby Vision")
    elif "HDR10+" in hdr:
        f.append("HDR10+")
    if gaming and "VRR" in gaming:
        f.append("VRR/ALLM 게이밍")
    return f[:5]


def avail(year, region):
    if year and year >= 2026:
        return "출시예정"
    if region == "Global":
        return "해외판매"
    return "판매중"


def main():
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()

        # A) brand.country
        for name, c in COUNTRY.items():
            cur.execute("update brand set country=%s where name=%s and country is null", (c, name))

        # model: smart_os_version + audio_channels/output_w
        cur.execute("""select m.model_id, b.name brand, s.generation_year yr, s.tier,
                              m.resolution, s.panel_tech
                       from model m join series s on m.series_id=s.series_id
                       join brand b on s.brand_id=b.brand_id""")
        for mid, brand, yr, tier, res, panel in cur.fetchall():
            ch, w = audio(brand, tier, res, panel)
            conn.cursor().execute("""
                update model set
                  smart_os_version = coalesce(smart_os_version, %s),
                  audio_channels   = coalesce(audio_channels, %s),
                  audio_output_w   = coalesce(audio_output_w, %s)
                where model_id=%s""", (os_version(brand, yr), ch, w, mid))

        # series.key_features (모델 스펙에서 파생)
        cur.execute("""select s.series_id, s.panel_tech, m.refresh_rate_native,
                              m.peak_brightness_nits, m.hdr_formats, m.gaming_features
                       from series s join model m on m.series_id=s.series_id
                       where s.key_features is null""")
        for sid, panel, refresh, nits, hdr, gaming in cur.fetchall():
            kf = key_features(panel, refresh, nits, hdr, gaming)
            conn.cursor().execute("update series set key_features=%s where series_id=%s", (kf, sid))

        # variant: color/stand/weight/power/zones/availability/source_url/audio_output_w
        cur.execute("""select v.variant_id, b.name brand, v.size_inch, v.region,
                              s.tier, s.panel_tech, s.generation_year yr, m.dimming, m.audio_output_w
                       from variant v join model m on v.model_id=m.model_id
                       join series s on m.series_id=s.series_id
                       join brand b on s.brand_id=b.brand_id""")
        for vid, brand, size, region, tier, panel, yr, dimming, m_audio_w in cur.fetchall():
            conn.cursor().execute("""
                update variant set
                  color               = coalesce(color, %s),
                  stand_type          = coalesce(stand_type, %s),
                  weight_kg           = coalesce(weight_kg, %s),
                  power_w             = coalesce(power_w, %s),
                  local_dimming_zones = coalesce(local_dimming_zones, %s),
                  availability        = coalesce(availability, %s),
                  source_url          = coalesce(source_url, %s),
                  audio_output_w      = coalesce(audio_output_w, %s)
                where variant_id=%s""", (
                COLOR.get(brand, "Black"),
                "중앙 스탠드" if tier in ("flagship", "high") else "양측 다리",
                weight(size, panel), power(size, panel), zones(tier, dimming),
                avail(yr, region), SRC.get(brand), m_audio_w, vid))

        # comparison_map.price_band (tier_match 파생)
        cur.execute("""update comparison_map set price_band = case tier_match::text
                         when 'flagship' then '프리미엄' when 'high' then '상위'
                         when 'mid' then '중급' else '보급' end
                       where price_band is null""")

        # estimated_fields 표기 — provenance.ESTIMATED 중 값이 채워진 컬럼만 기록.
        # 이 스크립트가 관리하는 건 model 오디오 필드뿐 → 다른 소유자(load_sizes 의 size_variants_in 등)
        # 플래그는 보존한다.
        model_keys = set(prov.ESTIMATED.get("model", {}))
        cur.execute("select model_id, audio_channels, audio_output_w, estimated_fields from model")
        for mid, ac, aw, existing in cur.fetchall():
            audio_ef = prov.estimated_for("model", {"audio_channels": ac, "audio_output_w": aw})
            keep = [f for f in (existing or []) if f not in model_keys]
            ef = sorted(set(audio_ef) | set(keep))
            conn.cursor().execute("update model set estimated_fields=%s where model_id=%s", (ef, mid))
        variant_keys = set(prov.ESTIMATED.get("variant", {}))
        cur.execute("""select variant_id, weight_kg, power_w, local_dimming_zones,
                              color, stand_type, estimated_fields from variant""")
        for vid, wt, pw, zn, col, st, existing in cur.fetchall():
            base = prov.estimated_for("variant", {"weight_kg": wt, "power_w": pw,
                                                  "local_dimming_zones": zn,
                                                  "color": col, "stand_type": st})
            keep = [f for f in (existing or []) if f not in variant_keys]  # 구성 SKU(sku_full) 등 보존
            ef = sorted(set(base) | set(keep))
            conn.cursor().execute("update variant set estimated_fields=%s where variant_id=%s", (ef, vid))

        conn.commit()
    print("빈 필드 보강 + estimated_fields 표기 완료 (기존 값은 보존).")


if __name__ == "__main__":
    main()
