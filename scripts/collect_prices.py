"""
가격 수집 운영 러너 (스케줄러가 매일 호출) — 파이프라인 운영 루프.
흐름: DanawaCollector 수집 → 정규화 → 오늘자 스냅샷 CSV 저장
      → variant 매칭(resolve_variant_id) → price_history upsert → 로깅.
셀렉터(config/selectors.py:DANAWA) 미설정 시 0건 수집으로 안전 종료(하네스는 정상).

실행:  PG_DSN=... .venv/bin/python scripts/collect_prices.py
스케줄: deploy/com.tvspecdb.prices.plist (launchd, 매일 03:00)
"""
from __future__ import annotations
import os
import sys
import csv
import pathlib
from datetime import date, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from collectors.danawa import DanawaCollector
from normalize.normalizer import normalize_record
from config.targets import TARGETS
import db

PRICE_DIR = ROOT / "data" / "prices"
LOG_DIR = ROOT / "data" / "logs"


def _log(msg: str):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
    print(line)
    with open(LOG_DIR / f"prices_{date.today()}.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def collect_and_load(region: str = "KR"):
    today = date.today().isoformat()
    _log(f"[start] danawa 가격 수집 region={region}")

    # 1) 수집 + 정규화 → 가격 있는 variant 레코드만
    recs = DanawaCollector(region=region).collect(TARGETS["danawa"])
    priced = []
    for r in recs:
        n = normalize_record(r.payload)
        if n.get("sku_full") and n.get("price_street"):
            priced.append(n)
    _log(f"[collect] 원본 {len(recs)}건 → 가격보유 {len(priced)}건")

    # 2) 오늘자 스냅샷 CSV 보존(감사/재처리용)
    PRICE_DIR.mkdir(parents=True, exist_ok=True)
    snap = PRICE_DIR / f"{today}.csv"
    with open(snap, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sku_full", "region", "channel", "price", "captured_at"])
        for n in priced:
            w.writerow([n["sku_full"], region, "danawa", n["price_street"], today])

    # 3) DB 적재(variant 매칭 → price_history)
    if not os.environ.get("PG_DSN"):
        _log("[warn] PG_DSN 미설정 — DB 적재 스킵(스냅샷만 저장)")
        return
    applied = skipped = 0
    with db.connect() as conn:
        cur = conn.cursor()
        for n in priced:
            vid = db.resolve_variant_id(cur, n["sku_full"], region)
            if vid is None:
                skipped += 1        # danawa 표기 SKU가 우리 variant와 불일치(정규화 매핑 과제)
                continue
            db.upsert_price_snapshot(cur, vid, "danawa", int(n["price_street"]),
                                     captured_at=today)
            applied += 1
        conn.commit()
    _log(f"[load] 적재 {applied}건 / 미매칭 {skipped}건 → {snap.name}")
    _log("[done]")


if __name__ == "__main__":
    try:
        collect_and_load()
    except Exception as e:            # 스케줄 작업은 실패해도 다음 회차 계속
        _log(f"[error] {type(e).__name__}: {e}")
        raise
