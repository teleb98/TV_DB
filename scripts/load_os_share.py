"""
스마트TV OS 시장점유율(os_market_share) 적재 — 업계 리서치 자료. 멱등(UNIQUE upsert).

제품 model 계층과 분리된 시장 통계. (region, metric, period) 조합이 하나의 "파이".
값 출처(2026-08 WebSearch):
  - Omdia: US 활성기반 2025Q1 (Roku 34 / Tizen 22 / FireTV·CastOS 각 12)
  - Omdia/업계: 글로벌 설치기반 2025 추정 밴드 (Google 35~40 / Tizen 19~23 / webOS ~13 / Roku ~10 / FireTV ~8 / VIDAA ~6)
  - 발표 출하량 점유율 2024Q4 (Google 24 / Tizen 16.9 / webOS 11.8) — 상위 3종만 공개치
estimated=true 는 공개 발표치가 없어 밴드 중앙/잔여로 보정한 추정행.

실행: ./.venv/bin/python -m scripts.load_os_share
"""
from __future__ import annotations
import os
import psycopg

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")

OMDIA = "Omdia"
URL_OMDIA_US = "https://omdia.tech.informa.com/blogs/2025/july/the-smart-tv-os-shakeup-amazon-walmart-and-the-coming-age-of-shoppable-media"
URL_OMDIA_CAST = "https://omdia.tech.informa.com/pr/2025/oct/castos-to-exceed-15-million-shipments-set-to-dominate-north-americas-tv-os-market"

# (os, vendor, region, metric, period, share, rank, source_org, source_url, estimated, note)
ROWS: list[tuple] = [
    # ── 글로벌 설치기반(활성 TV) 2025 추정 — 밴드 중앙값. 합계 100 ──
    ("Google-TV", "Google",         "Global", "installed_base", "2025", 37.0, 1, OMDIA, URL_OMDIA_US, True,  "Android TV+Google TV 합산, 밴드 35~40 중앙"),
    ("Tizen",     "Samsung",        "Global", "installed_base", "2025", 20.0, 2, OMDIA, URL_OMDIA_US, True,  "밴드 19~23 중앙"),
    ("webOS",     "LG",             "Global", "installed_base", "2025", 13.0, 3, OMDIA, URL_OMDIA_US, True,  "밴드 12~14"),
    ("Roku",      "Roku",           "Global", "installed_base", "2025", 10.0, 4, OMDIA, URL_OMDIA_US, True,  "북미 편중"),
    ("Fire-TV",   "Amazon",         "Global", "installed_base", "2025",  8.0, 5, OMDIA, URL_OMDIA_US, True,  ""),
    ("VIDAA",     "Hisense",        "Global", "installed_base", "2025",  6.0, 6, OMDIA, URL_OMDIA_US, True,  "Toshiba(하이센스 소유) 포함, 밸류 세그먼트 최고 성장"),
    ("기타",      "Titan/HarmonyOS 등","Global","installed_base","2025",  6.0, 7, OMDIA, URL_OMDIA_US, True,  "Titan OS·HarmonyOS·자체 OS 등 잔여"),

    # ── 미국 활성기반 2025Q1 (Omdia 발표) — 상위 4종 발표치, 나머지 추정. 합계 100 ──
    ("Roku",      "Roku",           "US", "installed_base", "2025Q1", 34.0, 1, OMDIA, URL_OMDIA_US, False, "Omdia 2025Q1 1위"),
    ("Tizen",     "Samsung",        "US", "installed_base", "2025Q1", 22.0, 2, OMDIA, URL_OMDIA_US, False, "Omdia 2025Q1 2위"),
    ("Fire-TV",   "Amazon",         "US", "installed_base", "2025Q1", 12.0, 3, OMDIA, URL_OMDIA_US, False, "3위 공동"),
    ("CastOS",    "Vizio/Walmart",  "US", "installed_base", "2025Q1", 12.0, 3, OMDIA, URL_OMDIA_CAST, False, "3위 공동, 월마트 인수 후 2029 1위 전망"),
    ("webOS",     "LG",             "US", "installed_base", "2025Q1",  7.0, 5, OMDIA, URL_OMDIA_US, True,  "잔여 추정"),
    ("Google-TV", "Google",         "US", "installed_base", "2025Q1",  7.0, 5, OMDIA, URL_OMDIA_US, True,  "Android TV+Google TV, 잔여 추정"),
    ("기타",      "VIDAA 등",       "US", "installed_base", "2025Q1",  6.0, 7, OMDIA, URL_OMDIA_US, True,  "VIDAA 등 잔여"),

    # ── 글로벌 출하량 점유율 2024Q4 (공개 발표 상위 3종만) ──
    ("Google-TV", "Google",  "Global", "shipments", "2024Q4", 24.0, 1, OMDIA, URL_OMDIA_US, False, "출하량 1위(24%+)"),
    ("Tizen",     "Samsung", "Global", "shipments", "2024Q4", 16.9, 2, OMDIA, URL_OMDIA_US, False, "출하 점유율 16.9%"),
    ("webOS",     "LG",      "Global", "shipments", "2024Q4", 11.8, 3, OMDIA, URL_OMDIA_US, False, "출하 점유율 11.8%"),
]


def main():
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()
        for r in ROWS:
            cur.execute("""
                insert into os_market_share
                    (os, vendor, region, metric, period, share_pct, rank,
                     source_org, source_url, estimated, note)
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                on conflict (os, region, metric, period) do update set
                    vendor=excluded.vendor, share_pct=excluded.share_pct, rank=excluded.rank,
                    source_org=excluded.source_org, source_url=excluded.source_url,
                    estimated=excluded.estimated, note=excluded.note, updated_at=now()
            """, r)
        conn.commit()
        # 파이 합계 검증
        cur.execute("""select region, metric, period, round(sum(share_pct),1)
                       from os_market_share group by region, metric, period
                       order by region, period""")
        sums = cur.fetchall()
    print(f"os_market_share {len(ROWS)}행 적재.")
    for reg, met, per, tot in sums:
        flag = "" if (met == "shipments" or abs(float(tot) - 100.0) < 0.05) else "  ⚠ 합계≠100"
        print(f"  {reg:7} {met:14} {per:7} 합계 {tot}%{flag}")


if __name__ == "__main__":
    main()
