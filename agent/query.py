"""
Agent 검색계층 — 상담봇이 tool-call 로 호출하는 질의 함수.
전부 정형쿼리(스펙/옵션/매핑). 라인업 '설명' 서술은 series.positioning 을
RAG 로 얹는 자리(현재는 정형 반환, positioning 채워지면 확장).

함수:
  compare(samsung_code)   삼성 모델 ↔ 경쟁사 동급 + 스펙 비교표
  lineup(brand, year)     브랜드 라인업 계층(라인업 안내봇)
  search(**filters)       조건 검색(패널/해상도/주사율/티어/예산)
반환은 모두 dict/list[dict] — 상담봇이 그대로 직렬화해 사용.
"""
from __future__ import annotations
import os
import psycopg
from psycopg.rows import dict_row

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")


def _conn():
    return psycopg.connect(DSN, row_factory=dict_row)


# ---------------------------------------------------------------- OS 플랫폼 경험(모델에 연결)
_OS_CACHE: dict[str, dict | None] = {}


def os_experience(os_name) -> dict | None:
    """series.os → os_platform 요약(음성·FAST·클라우드게임·AirPlay·핵심 장점). 캐시."""
    key = str(os_name) if os_name is not None else None
    if key in _OS_CACHE:
        return _OS_CACHE[key]
    exp = None
    if key:
        with _conn() as c:
            cur = c.cursor()
            cur.execute("""
                select os, base_os, voice_assistant, fast_service, casting, airplay,
                       cloud_gaming, smart_home, matter, update_policy, ad_level,
                       strengths, best_for
                from os_platform where os=%s
            """, (key,))
            exp = cur.fetchone()
        if exp and isinstance(exp.get("strengths"), list):
            exp["top_strengths"] = exp["strengths"][:3]
    _OS_CACHE[key] = exp
    return exp


# ---------------------------------------------------------------- 스펙 비교 상담봇
def compare(samsung_code: str) -> dict:
    """삼성 모델코드 → 자기 스펙 + 동급 경쟁사 모델 비교표(confidence 순)."""
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
            select b.name brand, s.marketing_name lineup, m.model_code_base code,
                   s.panel_tech panel, m.resolution, m.refresh_rate_native refresh,
                   m.peak_brightness_nits nits, m.gaming_features gaming,
                   m.connectivity, m.processor, s.tier, s.os
            from model m join series s on m.series_id=s.series_id
                         join brand b on s.brand_id=b.brand_id
            where m.model_code_base = %s and b.name='삼성'
        """, (samsung_code,))
        base = cur.fetchone()
        if not base:
            return {"error": f"삼성 모델 '{samsung_code}' 없음"}
        base["os_experience"] = os_experience(base.get("os"))

        cur.execute("""
            select b.name brand, s.marketing_name lineup, m.model_code_base code,
                   s.panel_tech panel, m.resolution, m.refresh_rate_native refresh,
                   m.peak_brightness_nits nits, m.gaming_features gaming,
                   m.connectivity, m.processor, s.os, cm.confidence
            from comparison_map cm
            join model sm on cm.samsung_model_id=sm.model_id
            join model m  on cm.competitor_model_id=m.model_id
            join series s on m.series_id=s.series_id
            join brand b  on s.brand_id=b.brand_id
            where sm.model_code_base=%s
            order by cm.confidence desc, b.name
        """, (samsung_code,))
        comps = cur.fetchall()
        for cp in comps:
            cp["os_experience"] = os_experience(cp.get("os"))
        return {"samsung": base, "competitors": comps}


# ---------------------------------------------------------------- 라인업 안내
def lineup(brand: str, year: int | None = None) -> list[dict]:
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
            select s.marketing_name lineup, s.tier, s.generation_year yr,
                   s.panel_tech panel, m.model_code_base code, s.positioning
            from series s join brand b on s.brand_id=b.brand_id
            left join model m on m.series_id=s.series_id
            where b.name=%s and (%s::int is null or s.generation_year=%s)
            order by s.generation_year desc,
                     array_position(array['flagship','high','mid','entry']::text[], s.tier::text)
        """, (brand, year, year))
        return cur.fetchall()


# ---------------------------------------------------------------- 신제품(발표) 안내
def whats_new(year: int, brand: str | None = None) -> list[dict]:
    """해당 연도의 발표/출시 라인업."""
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
            select b.name brand, s.marketing_name lineup, m.model_code_base code,
                   s.tier
            from series s join brand b on s.brand_id=b.brand_id
            left join model m on m.series_id=s.series_id
            where s.generation_year=%s and (%s::text is null or b.name=%s)
            order by b.name, array_position(array['flagship','high','mid','entry']::text[], s.tier::text)
        """, (year, brand, brand))
        return cur.fetchall()


# ---------------------------------------------------------------- 라인업 추천(RAG)
_embedder = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        from embed.embedder import get_embedder
        _embedder = get_embedder()
    return _embedder


def recommend_semantic(query_text: str, brand: str | None = None, limit: int = 5) -> list[dict]:
    """자연어 니즈 → 임베딩 코사인 유사도(pgvector)로 라인업 추천 (정식 RAG).
    키워드 매칭과 달리 동의어·의도까지 반영. series_embedding 필요."""
    emb = _get_embedder()
    qv = emb.encode([query_text])[0]
    vec_str = "[" + ",".join(f"{x:.6f}" for x in qv) + "]"
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
            select b.name brand, s.marketing_name lineup, s.tier, s.generation_year yr,
                   s.positioning, round((1 - (se.vec <=> %s::vector))::numeric, 3) score
            from series_embedding se
            join series s on se.series_id=s.series_id
            join brand b on s.brand_id=b.brand_id
            where (%s::text is null or b.name=%s)
            order by se.vec <=> %s::vector
            limit %s
        """, (vec_str, brand, brand, vec_str, limit))
        return cur.fetchall()


def _has_embeddings() -> bool:
    with _conn() as c:
        cur = c.cursor()
        cur.execute("select to_regclass('series_embedding')")
        if cur.fetchone()["to_regclass"] is None:
            return False
        cur.execute("select count(*) n from series_embedding")
        return cur.fetchone()["n"] > 0


def recommend(query_text: str, brand: str | None = None, limit: int = 5) -> list[dict]:
    """라인업 추천. series_embedding 이 있으면 시맨틱(RAG), 없으면 키워드 폴백."""
    if _has_embeddings():
        try:
            return recommend_semantic(query_text, brand, limit)
        except Exception as e:
            print(f"[recommend] 시맨틱 실패({type(e).__name__}) → 키워드 폴백")
    tokens = [t for t in query_text.replace(",", " ").split() if len(t) >= 2]
    if not tokens:
        return []
    # 각 토큰이 positioning 에 있으면 +1 (ILIKE), 점수순 정렬
    score = " + ".join(["(s.positioning ILIKE %s)::int"] * len(tokens))
    params = [f"%{t}%" for t in tokens]
    sql = f"""
        select b.name brand, s.marketing_name lineup, s.tier,
               s.generation_year yr, s.positioning, ({score}) score
        from series s join brand b on s.brand_id=b.brand_id
        where s.positioning is not null
          and (%s::text is null or b.name=%s)
        group by b.name, s.marketing_name, s.tier, s.generation_year, s.positioning
        having ({score}) > 0
        order by score desc, s.generation_year desc
        limit %s
    """
    with _conn() as c:
        cur = c.cursor()
        cur.execute(sql, params + [brand, brand] + params + [limit])
        return cur.fetchall()


# ---------------------------------------------------------------- 가격
def best_price(model_code: str, region: str = "KR") -> list[dict]:
    """모델의 옵션별 현재 최저가(variant.price_street) — 상담봇 '얼마예요?' 응답."""
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
            select v.sku_full, v.size_inch,
                   coalesce(v.price_street, v.price_msrp) price, v.currency, v.updated_at
            from variant v join model m on v.model_id=m.model_id
            where m.model_code_base=%s and v.region=%s
              and coalesce(v.price_street, v.price_msrp) is not null
            order by price
        """, (model_code, region))
        return cur.fetchall()


def price_by_region(model_code: str) -> list[dict]:
    """동일 모델의 지역별 현재가·OS(KR/US…) — '미국이랑 한국 가격 차이?' 응답.
    os 는 지역별 실효 OS(variant.os_override 우선, 없으면 series.os)."""
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
            select v.region, v.sku_full,
                   coalesce(v.price_street, v.price_msrp) price, v.currency,
                   coalesce(v.os_override, s.os) os
            from variant v
            join model m on v.model_id=m.model_id
            join series s on m.series_id=s.series_id
            where m.model_code_base=%s
              and coalesce(v.price_street, v.price_msrp) is not null
            order by v.region
        """, (model_code,))
        return cur.fetchall()


def price_trend(sku_full: str, region: str = "KR") -> list[dict]:
    """특정 SKU 가격 이력(추세) — captured_at 순."""
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
            select ph.captured_at::date d, ph.channel, ph.price, ph.currency
            from price_history ph join variant v on ph.variant_id=v.variant_id
            where v.sku_full=%s and v.region=%s
            order by ph.captured_at
        """, (sku_full, region))
        return cur.fetchall()


# ---------------------------------------------------------------- 조건 검색
def search(panel: str | None = None, resolution: str | None = None,
           min_refresh: int | None = None, tier: str | None = None,
           max_price: int | None = None, region: str = "KR") -> list[dict]:
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
            select b.name brand, s.marketing_name lineup, m.model_code_base code,
                   s.panel_tech panel, m.resolution, m.refresh_rate_native refresh,
                   s.os, v.size_inch, coalesce(v.price_street, v.price_msrp) price, v.currency
            from variant v join model m on v.model_id=m.model_id
            join series s on m.series_id=s.series_id
            join brand b on s.brand_id=b.brand_id
            where v.region=%s
              and (%s::text is null or s.panel_tech::text=%s)
              and (%s::text is null or m.resolution=%s)
              and (%s::int  is null or m.refresh_rate_native >= %s)
              and (%s::text is null or s.tier::text=%s)
              and (%s::int  is null or coalesce(v.price_street, v.price_msrp) <= %s)
            order by b.name, m.model_code_base
        """, (region, panel, panel, resolution, resolution,
              min_refresh, min_refresh, tier, tier, max_price, max_price))
        rows = cur.fetchall()
        for r in rows:
            r["os_experience"] = os_experience(r.get("os"))
        return rows
