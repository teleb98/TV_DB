"""
온라인 쇼핑몰(리테일러) 실판매가 적재 — 멀티채널 price_history. 멱등.

각 값은 WebSearch(2026-07 확인)로 얻은 실제 리테일러 표기가. region=US(USD).
해당 (모델,사이즈)의 US variant 에 채널별 스냅샷을 append(없으면 구성 variant 생성).
price_msrp(정가)가 있으면 함께 기록.

출처 채널: bestbuy · walmart · amazon · costco (검색 확인). captured_at=조사일.
실행: ./.venv/bin/python -m scripts.load_retail_prices
"""
from __future__ import annotations
import os
import psycopg

import db

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")
CAPTURED = "2026-07-25"

# code: { size: {"msrp": 정가|None, "channels": {채널: 가격USD}} }  — 전부 실제 확인가
RETAIL: dict[str, dict[int, dict]] = {
    "C5":     {65: {"msrp": 2699, "channels": {"bestbuy": 1099, "walmart": 1397}}},
    "G5":     {65: {"msrp": 2999, "channels": {"amazon": 1999}}},
    "XR80II": {65: {"msrp": 3499, "channels": {"walmart": 2398}}},
    "QM8K":   {65: {"msrp": 1499, "channels": {"bestbuy": 1258}}},
    "U8Q":    {75: {"msrp": 1499, "channels": {"bestbuy": 1299}}},
}


def _us_variant(cur, model_id: int, code: str, size: int) -> int:
    cur.execute("select variant_id from variant where model_id=%s and region='US' and size_inch=%s",
                (model_id, size))
    r = cur.fetchone()
    if r:
        return r[0]
    sku = f"{code}-{size}IN-US"
    cur.execute("""insert into variant(model_id, sku_full, size_inch, region, currency, estimated_fields)
                   values (%s,%s,%s,'US','USD', ARRAY['sku_full'])
                   on conflict (sku_full, region) do nothing""", (model_id, sku, size))
    return db.resolve_variant_id(cur, sku, "US")


def main():
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()
        snaps = 0
        for code, sizes in RETAIL.items():
            cur.execute("select model_id from model where model_code_base=%s", (code,))
            row = cur.fetchone()
            if not row:
                print(f"  ⏭ DB에 없음: {code}")
                continue
            mid = row[0]
            for size, info in sizes.items():
                vid = _us_variant(cur, mid, code, size)
                if info.get("msrp"):
                    cur.execute("update variant set price_msrp=coalesce(price_msrp,%s) where variant_id=%s",
                                (info["msrp"], vid))
                for channel, price in info["channels"].items():
                    db.upsert_price_snapshot(cur, vid, channel, price, CAPTURED, "USD")
                    snaps += 1
        conn.commit()
    print(f"리테일러 가격 스냅샷 {snaps}건 적재(price_history, 채널별).")


if __name__ == "__main__":
    main()
