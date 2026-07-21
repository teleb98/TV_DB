"""
Comparison_Map 생성기 — 삼성 ↔ 경쟁사 동급 모델 매핑(부가가치 자산).
규칙: 같은 세대(generation_year) + 같은 tier 안에서 삼성 × 경쟁사 조합을 만들고,
      패널 계열·해상도 일치로 confidence 산정.
멱등: (samsung_model_id, competitor_model_id) UNIQUE + ON CONFLICT.

실행:  PG_DSN=... .venv/bin/python scripts/build_comparison_map.py
"""
from __future__ import annotations
import os
import psycopg

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")

# 패널 계열 그룹 — 같은 계열이면 비교 타당성↑
OLED_FAMILY = {"OLED", "WOLED", "QD-OLED"}
LED_FAMILY = {"QLED", "Neo-QLED", "Mini-LED", "LED-LCD"}


def panel_family(p: str | None) -> str:
    if p in OLED_FAMILY:
        return "OLED"
    if p in LED_FAMILY:
        return "LED"
    return "other"


def confidence(a: dict, b: dict) -> float:
    """0.5(동일 세대·티어) + 패널계열 0.3 + 해상도 0.2."""
    c = 0.5
    if panel_family(a["panel"]) == panel_family(b["panel"]):
        c += 0.3
    if a["resolution"] and a["resolution"] == b["resolution"]:
        c += 0.2
    return round(min(c, 1.0), 2)


def load_models(cur) -> list[dict]:
    cur.execute("""
        select m.model_id, b.name brand, s.tier, s.generation_year yr,
               s.panel_tech panel, m.resolution, m.model_code_base code
        from model m
        join series s on m.series_id = s.series_id
        join brand b on s.brand_id = b.brand_id
    """)
    cols = [d.name for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def build():
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()
        models = load_models(cur)
        sam = [m for m in models if m["brand"] == "삼성"]
        comp = [m for m in models if m["brand"] != "삼성"]

        n = 0
        for s in sam:
            for c in comp:
                if s["tier"] != c["tier"] or s["yr"] != c["yr"]:
                    continue                       # 같은 세대·티어만 매핑
                conf = confidence(s, c)
                if conf < 0.5:
                    continue
                cur.execute("""
                    insert into comparison_map
                      (samsung_model_id, competitor_model_id, tier_match, mapping_basis, confidence)
                    values (%s,%s,%s,%s,%s)
                    on conflict (samsung_model_id, competitor_model_id) do update
                      set confidence = excluded.confidence,
                          mapping_basis = excluded.mapping_basis
                """, (s["model_id"], c["model_id"], s["tier"],
                      "tier+year+panel+resolution", conf))
                n += 1
        conn.commit()
        print(f"매핑 {n}건 적재 (삼성 {len(sam)} × 경쟁사 {len(comp)})")


if __name__ == "__main__":
    build()
