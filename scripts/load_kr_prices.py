"""
국내(KR) 실판매가 적재 — 다나와·SSG 등 국내몰 price_history. 멱등.

각 값은 WebSearch(2026-07 한국어 검색) 확인가. region=KR(KRW).
해당 (모델,사이즈)의 KR variant 에 채널별 스냅샷을 append(없으면 구성 variant 생성).
price_msrp(국내 정가)가 있으면 함께 기록.

채널: danawa · ssg · 11st (검색 확인). captured_at=조사일.
실행: ./.venv/bin/python -m scripts.load_kr_prices
"""
from __future__ import annotations
import os
import psycopg

import db

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")
CAPTURED = "2026-07-25"

# code: { size: {"msrp": 국내정가|None, "channels": {채널: 가격KRW}} } — 전부 실제 확인가
KR_PRICES: dict[str, dict[int, dict]] = {
    "G5":   {65: {"msrp": None,    "channels": {"danawa": 2576000}}},                  # 다나와 최저(스탠드)
    "S95F": {65: {"msrp": 4790000, "channels": {"danawa": 3963200, "ssg": 4296600}}},  # 2개월 최저 / SSG
    "C5":   {65: {"msrp": 4800000, "channels": {}}},                                   # 정가(스트리트 미확인)
}


def _kr_variant(cur, model_id: int, code: str, size: int) -> int:
    cur.execute("select variant_id from variant where model_id=%s and region='KR' and size_inch=%s",
                (model_id, size))
    r = cur.fetchone()
    if r:
        return r[0]
    sku = f"{code}-{size}IN-KR"
    cur.execute("""insert into variant(model_id, sku_full, size_inch, region, currency, estimated_fields)
                   values (%s,%s,%s,'KR','KRW', ARRAY['sku_full'])
                   on conflict (sku_full, region) do nothing""", (model_id, sku, size))
    return db.resolve_variant_id(cur, sku, "KR")


def main():
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()
        snaps = 0
        for code, sizes in KR_PRICES.items():
            cur.execute("select model_id from model where model_code_base=%s", (code,))
            row = cur.fetchone()
            if not row:
                print(f"  ⏭ DB에 없음: {code}")
                continue
            mid = row[0]
            for size, info in sizes.items():
                vid = _kr_variant(cur, mid, code, size)
                if info.get("msrp"):
                    cur.execute("update variant set price_msrp=coalesce(price_msrp,%s) where variant_id=%s",
                                (info["msrp"], vid))
                for channel, price in info["channels"].items():
                    db.upsert_price_snapshot(cur, vid, channel, price, CAPTURED, "KRW")
                    snaps += 1
        conn.commit()
    print(f"국내 가격 스냅샷 {snaps}건 적재(price_history, KRW).")


if __name__ == "__main__":
    main()
