"""
변경 감지 & 이벤트 (Phase 3) — price_history/모델 상태 변화에서 이벤트 발행.
- 가격 인하(price_drop): 직전 대비 임계% 이상 하락
- 신제품(new_model): positioning 있으나 임베딩 없는 series → 임베딩 재생성 대상
- 단종(eol): variant.availability='eol'
이벤트는 crawl_event 에 멱등 적재(중복 무시). 재임베딩/알림 트리거로 사용.
"""
from __future__ import annotations


def detect_price_drops(cur, pct: float = 5.0) -> int:
    """직전 대비 pct% 이상 하락한 SKU → price_drop 이벤트."""
    cur.execute("""
        with ranked as (
          select ph.variant_id, ph.price, ph.currency, ph.captured_at,
                 lag(ph.price) over (partition by ph.variant_id order by ph.captured_at) prev
          from price_history ph)
        select v.sku_full, r.currency, r.prev, r.price,
               round((r.price - r.prev) * 100.0 / r.prev, 0) pct
        from ranked r join variant v on r.variant_id = v.variant_id
        where r.prev is not null and r.price < r.prev * (1 - %s/100.0)
    """, (pct,))
    n = 0
    for sku, cur_code, prev, price, chg in cur.fetchall():
        detail = f"{prev:,}→{price:,} {cur_code} ({int(chg)}%)"
        cur.execute("""insert into crawl_event(type, entity, detail)
                       values ('price_drop', %s, %s) on conflict do nothing""",
                    (sku, detail))
        n += cur.rowcount
    return n


def detect_new_models(cur) -> int:
    """positioning 있으나 임베딩 없는 series → new_model(임베딩 필요) 이벤트."""
    cur.execute("""
        select b.name, s.marketing_name, s.generation_year
        from series s join brand b on s.brand_id = b.brand_id
        left join series_embedding se on se.series_id = s.series_id
        where s.positioning is not null and se.series_id is null
    """)
    n = 0
    for brand, mk, yr in cur.fetchall():
        cur.execute("""insert into crawl_event(type, entity, detail)
                       values ('new_model', %s, %s) on conflict do nothing""",
                    (f"{brand} {mk}", f"{yr} 신규 — 임베딩 필요"))
        n += cur.rowcount
    return n


def detect_eol(cur) -> int:
    """단종 표시 variant → eol 이벤트."""
    cur.execute("select sku_full, region from variant where availability = 'eol'")
    n = 0
    for sku, region in cur.fetchall():
        cur.execute("""insert into crawl_event(type, entity, detail)
                       values ('eol', %s, %s) on conflict do nothing""",
                    (sku, f"{region} 단종"))
        n += cur.rowcount
    return n


def run(cur, price_pct: float = 5.0) -> dict:
    return {
        "price_drop": detect_price_drops(cur, price_pct),
        "new_model": detect_new_models(cur),
        "eol": detect_eol(cur),
    }
