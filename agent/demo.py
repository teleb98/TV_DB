"""
Agent 검색계층 데모 — query.py 함수를 실제 호출해 출력.
실행:  PG_DSN=... .venv/bin/python -m agent.demo
"""
from __future__ import annotations
import json
from agent import query


def _p(title, obj):
    print(f"\n### {title}")
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    _p("compare('QN90D') — 스펙 비교 상담봇", query.compare("QN90D"))
    _p("lineup('삼성', 2024) — 라인업 안내", query.lineup("삼성", 2024))
    _p("search(panel='WOLED', min_refresh=120) — 조건검색: OLED 120Hz+",
       query.search(panel="WOLED", min_refresh=120))
    _p("recommend('밝은 거실 스포츠 게이밍 가성비') — 라인업 추천(RAG 자리)",
       query.recommend("밝은 거실 스포츠 게이밍 가성비"))
