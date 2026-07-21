"""
수집 → 정규화 → 4계층 적재 오케스트레이션 (엔트리포인트).
경로 2가지:
  1) 수집기 실행:  python pipeline.py --source danawa --region KR [--dry-run]
  2) 골든셋 적재:  python pipeline.py --load-golden data/golden/golden_models.csv [--dry-run]

--dry-run 이면 DB 없이 정규화 결과만 출력(검증용). 실제 적재는 db.py(psycopg) 사용.
"""
from __future__ import annotations
import argparse
import csv
from collectors.base import RawRecord
from normalize.normalizer import normalize_record
from config.targets import TARGETS, TARGETS_US


def _load_collectors():
    from collectors.samsung_official import SamsungOfficialCollector
    from collectors.danawa import DanawaCollector
    from collectors.spec_pdf import SpecPdfCollector
    return {
        "samsung_official": SamsungOfficialCollector,
        "danawa": DanawaCollector,
        "spec_pdf": SpecPdfCollector,
    }


def _targets_for(region: str) -> dict[str, list[str]]:
    return TARGETS_US if region == "US" else TARGETS


# ---------------------------------------------------------------- 적재기
class Applier:
    """레코드를 4계층에 적재. 수집 순서(series→model→variant)를 이용해 FK를 이어붙임."""

    def __init__(self, dry_run: bool):
        self.dry_run = dry_run
        self.conn = None
        self.cur = None
        self._brand_id = self._series_id = self._model_id = None
        if not dry_run:
            import db
            self.db = db
            self.conn = db.connect()
            self.cur = self.conn.cursor()

    def apply(self, rec: dict, layer: str):
        if self.dry_run:
            print(f"[{layer}] {rec}")
            return
        d = self.db
        if rec.get("brand"):
            self._brand_id = d.upsert_brand(self.cur, rec)
        if layer in ("series", "row") and self._brand_id:
            self._series_id = d.upsert_series(self.cur, rec, self._brand_id)
        if layer in ("model", "row") and self._series_id:
            self._model_id = d.upsert_model(self.cur, rec, self._series_id)
        if layer in ("variant", "row") and self._model_id and rec.get("sku_full"):
            vid = d.upsert_variant(self.cur, rec, self._model_id)
            d.append_price(self.cur, vid, rec)

    def close(self, commit: bool):
        if self.conn:
            self.conn.commit() if commit else self.conn.rollback()
            self.conn.close()


# ---------------------------------------------------------------- 수집기 경로
def run(source: str, region: str, dry_run: bool):
    Collector = _load_collectors()[source]
    recs: list[RawRecord] = Collector(region=region).collect(_targets_for(region)[source])
    print(f"수집 {len(recs)}건 — 정규화/적재 시작")
    ap = Applier(dry_run)
    try:
        for r in recs:
            ap.apply(normalize_record(r.payload), r.layer)
        ap.close(commit=True)
    except Exception:
        ap.close(commit=False)
        raise


# ---------------------------------------------------------------- 골든셋 경로
def load_golden(path: str, dry_run: bool):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    print(f"골든셋 {len(rows)}행 적재 (dry_run={dry_run})")
    ap = Applier(dry_run)
    try:
        for row in rows:
            # 빈 문자열 → None 정리 후 정규화(모델명 base 코드 채움)
            rec = normalize_record({k: (v or None) for k, v in row.items()})
            ap.apply(rec, "row")   # 'row' = 한 줄에 4계층 필드가 모두 있음
        ap.close(commit=True)
    except Exception:
        ap.close(commit=False)
        raise


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["samsung_official", "danawa", "spec_pdf"])
    ap.add_argument("--load-golden", metavar="CSV")
    ap.add_argument("--region", default="KR")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.load_golden:
        load_golden(args.load_golden, args.dry_run)
    elif args.source:
        run(args.source, args.region, args.dry_run)
    else:
        ap.error("--source 또는 --load-golden 중 하나 필요")
