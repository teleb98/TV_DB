"""
지역별 모델명 매핑(model_alias) 생성 — 기존 실SKU + EPREL 모델명에서 자동 도출. 멱등.

- 각 (model, region)의 **실제 SKU**(구성SKU 제외: estimated_fields에 sku_full 없는 것)를
  region 모델명(kind=sku_root)으로 등재.
- certification.eprel_model 을 EU 모델명(kind=eprel)으로 등재.

Base_Model_ID 아래 Region_Model_Name 관계를 채운다.
실행: ./.venv/bin/python -m scripts.build_aliases
"""
from __future__ import annotations
import os
import psycopg

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")


def main():
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()
        # 1) 실SKU → 지역 모델명(sku_root). 구성SKU('{code}-{size}IN-...') 제외.
        cur.execute("""
            insert into model_alias(model_id, region, model_name, kind)
            select distinct v.model_id, v.region, v.sku_full, 'sku_root'
            from variant v
            where not ('sku_full' = any(coalesce(v.estimated_fields, '{}')))
              and v.sku_full !~ 'IN-(KR|US|Global)$'
            on conflict (model_id, region, model_name) do nothing
        """)
        sku_n = cur.rowcount
        # 2) EPREL 모델명 → EU 모델명(eprel)
        cur.execute("""
            insert into model_alias(model_id, region, model_name, kind)
            select model_id, 'EU', eprel_model, 'eprel'
            from certification where eprel_model is not null
            on conflict (model_id, region, model_name) do nothing
        """)
        eprel_n = cur.rowcount
        conn.commit()
    print(f"model_alias: 실SKU {sku_n}건 + EPREL {eprel_n}건 등재.")


if __name__ == "__main__":
    main()
