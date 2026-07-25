"""
읽기 전용 JSON API 서버 — tv-spec-db 를 HTTP 로 제공.

의존성 무추가(stdlib http.server) — 기존 agent.query 함수를 그대로 래핑.
맥미니에서 LaunchAgent(com.tvspecdb.web)로 127.0.0.1:PORT 에 상주하고,
Cloudflare Tunnel(rarebook) 이 tv.rarebook.co.kr → 이 포트로 프록시한다.

실행:  PORT=3004 ./.venv/bin/python -m serve.api
환경:  PG_DSN(기본 postgresql://localhost/tvspec), HOST(기본 127.0.0.1), PORT(기본 3004)

엔드포인트(전부 GET, 읽기 전용):
  GET /                      API 인덱스(엔드포인트 목록)
  GET /health                상태 + 4계층 건수
  GET /api/brands            브랜드별 라인업/모델 건수
  GET /api/lineup?brand=삼성&year=2025
  GET /api/compare?samsung=QN90F
  GET /api/whats_new?year=2026[&brand=]
  GET /api/search?panel=&resolution=&min_refresh=&tier=&max_price=&region=KR
  GET /api/recommend?q=밝은거실용&brand=&limit=5
  GET /api/price/best?model=QN90F&region=KR
  GET /api/price/region?model=QN90F
  GET /api/price/trend?sku=<sku_full>&region=KR
"""
from __future__ import annotations

import json
import os
import datetime
import decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import psycopg
from psycopg.rows import dict_row

from agent import query as Q

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "3004"))
DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")

INDEX = {
    "service": "tv-spec-db read-only API",
    "brands": "삼성 / LG / Sony / TCL / Hisense / Huawei / Xiaomi",
    "endpoints": {
        "GET /health": "상태 + 4계층 건수",
        "GET /api/brands": "브랜드별 라인업/모델 건수",
        "GET /api/lineup?brand=&year=": "브랜드 라인업 계층",
        "GET /api/compare?samsung=QN90F": "삼성 모델 ↔ 경쟁사 동급 비교",
        "GET /api/whats_new?year=2026&brand=": "연도별 발표 라인업",
        "GET /api/search?panel=&resolution=&min_refresh=&tier=&max_price=&region=": "조건 검색",
        "GET /api/recommend?q=&brand=&limit=": "니즈 기반 라인업 추천",
        "GET /api/price/best?model=&region=": "옵션별 현재 최저가",
        "GET /api/price/region?model=": "지역별 현재가·OS",
        "GET /api/price/trend?sku=&region=": "SKU 가격 이력",
    },
    "search_vocab": {
        "panel": ["WOLED", "QD-OLED", "Neo-QLED", "Mini-LED", "LED-LCD"],
        "resolution": ["4K", "8K"],
        "tier": ["flagship", "high", "mid"],
        "region": ["KR", "US", "Global"],
        "note": "search 필터는 정확일치. panel=OLED 처럼 부분값은 0건. Huawei/Xiaomi는 region=Global.",
    },
    "note": "읽기 전용. 수집/적재는 파이프라인(pipeline.py)·가격 스케줄러(com.tvspecdb.prices)가 담당.",
}


def _json_default(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    if isinstance(o, decimal.Decimal):
        return float(o)
    return str(o)


def _conn():
    return psycopg.connect(DSN, row_factory=dict_row)


def _int(v):
    return int(v) if v not in (None, "") else None


# ---- 서버 자체 질의(브랜드/건수) ----
def brands():
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
            select b.name brand,
                   count(distinct s.series_id) lineups,
                   count(distinct m.model_id)  models,
                   count(distinct v.variant_id) variants
            from brand b
            left join series s on s.brand_id=b.brand_id
            left join model m  on m.series_id=s.series_id
            left join variant v on v.model_id=m.model_id
            group by b.name order by models desc
        """)
        return cur.fetchall()


def health():
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
            select
              (select count(*) from brand)   brands,
              (select count(*) from series)  series,
              (select count(*) from model)   models,
              (select count(*) from variant) variants,
              (select count(*) from price_history) price_points
        """)
        counts = cur.fetchone()
    return {"status": "ok", "db": "tvspec", "counts": counts}


# ---- 라우팅 ----
def route(path: str, qs: dict):
    g = lambda k: (qs.get(k, [None])[0] or None)  # noqa: E731

    if path == "/":
        return 200, INDEX
    if path == "/health":
        return 200, health()
    if path == "/api/brands":
        return 200, brands()
    if path == "/api/lineup":
        if not g("brand"):
            return 400, {"error": "brand 파라미터 필요"}
        return 200, Q.lineup(g("brand"), _int(g("year")))
    if path == "/api/compare":
        if not g("samsung"):
            return 400, {"error": "samsung 파라미터 필요 (예: QN90F)"}
        return 200, Q.compare(g("samsung"))
    if path == "/api/whats_new":
        if not _int(g("year")):
            return 400, {"error": "year 파라미터 필요"}
        return 200, Q.whats_new(_int(g("year")), g("brand"))
    if path == "/api/search":
        return 200, Q.search(
            panel=g("panel"), resolution=g("resolution"),
            min_refresh=_int(g("min_refresh")), tier=g("tier"),
            max_price=_int(g("max_price")), region=g("region") or "KR",
        )
    if path == "/api/recommend":
        if not g("q"):
            return 400, {"error": "q 파라미터 필요"}
        return 200, Q.recommend(g("q"), g("brand"), _int(g("limit")) or 5)
    if path == "/api/price/best":
        if not g("model"):
            return 400, {"error": "model 파라미터 필요"}
        return 200, Q.best_price(g("model"), g("region") or "KR")
    if path == "/api/price/region":
        if not g("model"):
            return 400, {"error": "model 파라미터 필요"}
        return 200, Q.price_by_region(g("model"))
    if path == "/api/price/trend":
        if not g("sku"):
            return 400, {"error": "sku 파라미터 필요 (sku_full)"}
        return 200, Q.price_trend(g("sku"), g("region") or "KR")

    return 404, {"error": "not found", "see": "/"}


class Handler(BaseHTTPRequestHandler):
    server_version = "tvspecdb/1.0"

    def _send(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False, default=_json_default,
                          indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "public, max-age=60")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        try:
            code, payload = route(u.path, parse_qs(u.query))
        except Exception as e:  # DB/쿼리 예외 격리 — 한 요청 실패가 서버를 죽이지 않게
            code, payload = 500, {"error": f"{type(e).__name__}: {e}"}
        self._send(code, payload)

    do_HEAD = do_GET

    def log_message(self, fmt, *args):
        # launchd 로그로 최소 기록
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)


def main():
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"[tvspecdb.api] listening on http://{HOST}:{PORT}  DSN={DSN}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
