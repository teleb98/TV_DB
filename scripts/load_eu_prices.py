"""
유럽(EU) 공식 가격 적재 — MediaMarkt(mediamarkt.de) 기준. 멱등.

가격 정책: US 공식가=Best Buy(load_retail_prices), EU 공식가=**MediaMarkt**, KR=다나와/SSG(load_kr_prices).
값은 WebSearch(mediamarkt.de) 확인가. region=EU(EUR). EU variant 없으면 실제 EU SKU로 생성.
msrp=UVP(권장소비자가), channels.mediamarkt=현재 판매가.

실행: ./.venv/bin/python -m scripts.load_eu_prices
"""
from __future__ import annotations
import os
import psycopg

import db

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")
CAPTURED = "2026-08-08"

# code: { size: {"msrp": UVP|None, "sku": EU_SKU, "channels": {채널: 가격EUR}} }
EU_PRICES: dict[str, dict[int, dict]] = {
    "S95F": {65: {"msrp": None, "sku": "GQ65S95FATXZG", "channels": {"mediamarkt": 3529}}},
    "G5":   {65: {"msrp": 3999, "sku": "OLED65G57LW",   "channels": {"mediamarkt": 1699}}},
}


def _eu_variant(cur, model_id: int, code: str, size: int, sku: str) -> int:
    cur.execute("select variant_id from variant where model_id=%s and region='EU' and size_inch=%s",
                (model_id, size))
    r = cur.fetchone()
    if r:
        return r[0]
    real = sku or f"{code}-{size}IN-EU"
    ef = None if sku else ["sku_full"]      # 실제 EU SKU 면 구성값 아님
    cur.execute("""insert into variant(model_id, sku_full, size_inch, region, currency, estimated_fields)
                   values (%s,%s,%s,'EU','EUR',%s)
                   on conflict (sku_full, region) do nothing""", (model_id, real, size, ef))
    return db.resolve_variant_id(cur, real, "EU")


def main():
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()
        snaps = 0
        for code, sizes in EU_PRICES.items():
            cur.execute("select model_id from model where model_code_base=%s", (code,))
            row = cur.fetchone()
            if not row:
                print(f"  ⏭ DB에 없음: {code}")
                continue
            mid = row[0]
            for size, info in sizes.items():
                vid = _eu_variant(cur, mid, code, size, info.get("sku"))
                if info.get("msrp"):
                    cur.execute("update variant set price_msrp=coalesce(price_msrp,%s) where variant_id=%s",
                                (info["msrp"], vid))
                for channel, price in info["channels"].items():
                    db.upsert_price_snapshot(cur, vid, channel, price, CAPTURED, "EUR")
                    snaps += 1
        conn.commit()
    print(f"EU(MediaMarkt) 가격 스냅샷 {snaps}건 적재(EUR).")


if __name__ == "__main__":
    main()
