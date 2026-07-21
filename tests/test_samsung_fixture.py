"""
수집기 end-to-end 통합테스트 (픽스처 기반, 외부망 불필요).
경로: fetch(로컬 HTML) → parse → normalize → (DB) variant upsert.
DB 파트는 PG_DSN 이 있고 골든셋이 적재돼 QN90D 모델이 존재할 때만 수행.

실행:  PG_DSN=postgresql://localhost/tvspec .venv/bin/python -m tests.test_samsung_fixture
"""
from __future__ import annotations
import os
import pathlib
from collectors.samsung_official import SamsungOfficialCollector
from normalize.normalizer import normalize_record

FIXTURE = str(pathlib.Path(__file__).parent / "fixtures" / "samsung_qn90d.html")


def test_parse_and_normalize():
    recs = SamsungOfficialCollector().collect([FIXTURE])
    models = [r for r in recs if r.layer == "model"]
    variants = [r for r in recs if r.layer == "variant"]

    assert len(models) == 1, f"model 레코드 1개 기대, got {len(models)}"
    m = normalize_record(models[0].payload)
    assert m["brand"] == "삼성"
    assert m["panel_tech"] == "Neo-QLED", m["panel_tech"]        # 'Neo QLED' 정규화
    assert m["refresh_rate_native"] == 144, m["refresh_rate_native"]  # '144㎐' 정규화
    assert m["model_code_base"] == "QN90D", m["model_code_base"]  # SKU→base
    assert len(m["spec_table"]) == 5, m["spec_table"]             # 스펙표 5행 파싱

    assert len(variants) == 4, f"variant 4개(55/65/75/85) 기대, got {len(variants)}"
    sizes = sorted(normalize_record(v.payload)["size_inch"] for v in variants)
    assert sizes == [55, 65, 75, 85], sizes
    print(f"✅ parse/normalize OK — model={m['model_code_base']} sizes={sizes}")
    return variants


def test_db_variant_upsert(variants):
    dsn = os.environ.get("PG_DSN")
    if not dsn:
        print("⏭  PG_DSN 없음 — DB 적재 파트 스킵")
        return
    import db
    with db.connect() as conn:
        cur = conn.cursor()
        mid = db.resolve_model_id(cur, "QN90D")
        if mid is None:
            print("⏭  QN90D 모델 없음(골든셋 미적재) — DB 파트 스킵")
            return
        for v in variants:
            rec = normalize_record(v.payload)
            db.upsert_variant(cur, rec, mid)
        conn.commit()
        cur.execute("select size_inch from variant where model_id=%s order by size_inch", (mid,))
        db_sizes = [r[0] for r in cur.fetchall()]
    assert set([55, 65, 75, 85]).issubset(set(db_sizes)), db_sizes
    print(f"✅ DB upsert OK — QN90D variant sizes in DB={db_sizes}")


if __name__ == "__main__":
    vs = test_parse_and_normalize()
    test_db_variant_upsert(vs)
    print("\n모든 통합테스트 통과")
