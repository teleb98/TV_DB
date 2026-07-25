"""
인치 세분화 → variant 행 생성 (구성 SKU) + 확인된 실제 가격 적재. 멱등.

Phase A: size_variants_in 이 있는 모델(2025–2026)의 각 (기존 region × 사이즈) 조합으로
         variant 를 생성. 실제 판매 SKU 미상이라 **구성 SKU '{code}-{size}IN-{region}'** 사용하고
         estimated_fields 에 'sku_full' 표기(구성값). 물리 스펙은 이후 enrich_fill_empties 가 사이즈별로 채움.
Phase B: 공식 확인된 US 인치별 MSRP(QN90F·QM6K·QM7K)를 해당 (모델,사이즈)의 US variant 에 적재
         (없으면 구성 US variant 생성). price_history + variant.price_msrp/street.

실행: ./.venv/bin/python -m scripts.expand_variants   (이후 enrich_fill_empties 재실행 권장)
"""
from __future__ import annotations
import os
import psycopg

import db

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")

# 공식 확인된 US 인치별 MSRP(USD). 출처: samsung.com/us · us.tcl.com (2025).
REAL_PRICES: dict[str, dict[int, int]] = {
    "QN90F": {50: 1499, 55: 1799, 65: 2499, 75: 2999, 98: 14999, 115: 26999},
    "QM6K":  {50: 750, 55: 800, 65: 1000, 75: 1300, 85: 2000, 98: 3500},
    "QM7K":  {55: 1299, 65: 1499, 75: 1999, 85: 2499, 98: 3999, 115: 19999},
}
PRICE_CHANNEL = "official-msrp"
PRICE_DATE = "2025-04-01"


def _sku(code: str, size: int, region: str) -> str:
    return f"{code}-{size}IN-{region}"


def _insert_variant(cur, model_id: int, code: str, size: int, region: str) -> int:
    cur.execute("""
        insert into variant(model_id, sku_full, size_inch, region, currency, estimated_fields)
        values (%s,%s,%s,%s,%s, ARRAY['sku_full'])
        on conflict (sku_full, region) do nothing
        returning variant_id""",
        (model_id, _sku(code, size, region), size, region,
         "USD" if region == "US" else "KRW"))
    row = cur.fetchone()
    if row:
        return row[0]
    return db.resolve_variant_id(cur, _sku(code, size, region), region)


def main():
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()

        # Phase A ---------------------------------------------------------
        cur.execute("select model_id, model_code_base, size_variants_in "
                    "from model where size_variants_in is not null")
        models = cur.fetchall()
        created = 0
        for mid, code, sizes in models:
            cur.execute("select distinct region from variant where model_id=%s", (mid,))
            regions = [r[0] for r in cur.fetchall()] or ["KR"]
            cur.execute("select region, size_inch from variant where model_id=%s", (mid,))
            have = {(r, s) for r, s in cur.fetchall()}
            ins = conn.cursor()
            for region in regions:
                for size in sizes:
                    if (region, size) in have:
                        continue
                    ins.execute("""
                        insert into variant(model_id, sku_full, size_inch, region, currency, estimated_fields)
                        values (%s,%s,%s,%s,%s, ARRAY['sku_full'])
                        on conflict (sku_full, region) do nothing""",
                        (mid, _sku(code, size, region), size, region,
                         "USD" if region == "US" else "KRW"))
                    created += ins.rowcount

        # Phase B ---------------------------------------------------------
        priced = 0
        for code, prices in REAL_PRICES.items():
            cur.execute("select model_id from model where model_code_base=%s", (code,))
            row = cur.fetchone()
            if not row:
                continue
            mid = row[0]
            for size, usd in prices.items():
                cur.execute("select variant_id from variant where model_id=%s and region='US' and size_inch=%s",
                            (mid, size))
                r = cur.fetchone()
                vid = r[0] if r else _insert_variant(cur, mid, code, size, "US")
                db.upsert_price_snapshot(cur, vid, PRICE_CHANNEL, usd, PRICE_DATE, "USD")
                cur.execute("update variant set price_msrp=%s where variant_id=%s", (usd, vid))
                priced += 1

        conn.commit()
    print(f"인치 variant 생성 {created}행 (구성 SKU) · 실제 US 가격 {priced}건 적재. "
          f"→ enrich_fill_empties 재실행으로 사이즈별 물리스펙 채움.")


if __name__ == "__main__":
    main()
