"""
series.positioning 채우기 — (brand, series_name)로 매칭해 모든 세대 행에 적용.
실행:  PG_DSN=... .venv/bin/python scripts/load_positioning.py data/golden/series_positioning.csv
"""
from __future__ import annotations
import os
import sys
import csv
import psycopg

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")


def load(path: str):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()
        n = 0
        for r in rows:
            cur.execute("""
                update series s set positioning = %s
                from brand b
                where s.brand_id = b.brand_id
                  and b.name = %s and s.series_name = %s
            """, (r["positioning"], r["brand"], r["series_name"]))
            n += cur.rowcount
        conn.commit()
        print(f"positioning 업데이트 {n}개 series 행")


if __name__ == "__main__":
    load(sys.argv[1] if len(sys.argv) > 1 else "data/golden/series_positioning.csv")
