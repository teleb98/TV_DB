"""
가격 스냅샷 적재 — CSV(sku_full, region, channel, price, captured_at) →
price_history append + variant.price_street 동기화.
운영에선 danawa 수집기 결과를 이 포맷으로 넘겨 주기적(일/주) 실행 → 가격 이력 축적.

실행:  PG_DSN=... .venv/bin/python scripts/load_prices.py data/golden/prices_kr.csv
"""
from __future__ import annotations
import os
import sys
import csv
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))  # 루트에서 db 임포트
import psycopg
import db

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")


def load(path: str):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    # 시점 오름차순 정렬 → variant.price_street 가 최신가로 수렴
    rows.sort(key=lambda r: r["captured_at"])
    applied = skipped = 0
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()
        for r in rows:
            vid = db.resolve_variant_id(cur, r["sku_full"], r.get("region", "KR"))
            if vid is None:
                skipped += 1
                print(f"  ⏭ variant 없음: {r['sku_full']} ({r.get('region','KR')})")
                continue
            db.upsert_price_snapshot(cur, vid, r["channel"], int(r["price"]),
                                     captured_at=r["captured_at"])
            applied += 1
        conn.commit()
    print(f"가격 스냅샷 {applied}건 적재 / 스킵 {skipped}건")


if __name__ == "__main__":
    load(sys.argv[1] if len(sys.argv) > 1 else "data/golden/prices_kr.csv")
