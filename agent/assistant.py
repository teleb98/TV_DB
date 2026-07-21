"""
TV 제품정보 상담 Agent — DB 질의 함수를 Claude tool-use 로 노출.
Claude(claude-opus-4-8)가 자연어 질문을 받아 알맞은 DB 도구를 호출하고 답변한다.

실행:
    ANTHROPIC_API_KEY=... PG_DSN=postgresql://localhost/tvspec \
        .venv/bin/python -m agent.assistant "QN90F랑 경쟁사 비교해줘"
오프라인 도구 검증(LLM 불필요):
    PG_DSN=... .venv/bin/python -m agent.assistant --selftest
"""
from __future__ import annotations
import os
import sys
import json
from agent import query

MODEL = "claude-opus-4-8"

SYSTEM = """너는 삼성 및 경쟁사(LG/Sony/TCL/Hisense) TV 제품정보 상담 어시스턴트다.
- 답변의 사실(스펙·가격·라인업·비교)은 반드시 제공된 도구를 호출해 DB에서 얻는다. 추측 금지.
- 지역이 명시되면 region(KR/US)을 전달한다. 가격 통화(KRW/USD)를 함께 안내한다.
- 2026 모델은 status=announced(잠정)일 수 있으니 '발표된 잠정 정보'로 안내한다.
- 도구 결과가 비었으면 모른다고 솔직히 답한다. 한국어로 간결히 답한다."""

# ---- 도구 정의: 이름 → (query 함수, 입력 스키마) ----
TOOLS = [
    {"name": "compare", "description": "삼성 모델코드로 동급 경쟁사 비교(스펙+confidence).",
     "input_schema": {"type": "object", "properties": {
         "samsung_code": {"type": "string", "description": "삼성 모델 base코드(예: QN90F, S95D)"}},
         "required": ["samsung_code"]}},
    {"name": "lineup", "description": "브랜드의 라인업 계층(연도 선택). status/포지셔닝 포함.",
     "input_schema": {"type": "object", "properties": {
         "brand": {"type": "string", "description": "삼성/LG/Sony/TCL/Hisense"},
         "year": {"type": "integer"}}, "required": ["brand"]}},
    {"name": "search", "description": "조건 검색(패널/해상도/최소주사율/티어/예산/지역).",
     "input_schema": {"type": "object", "properties": {
         "panel": {"type": "string", "description": "예: WOLED, QD-OLED, Neo-QLED, Mini-LED"},
         "resolution": {"type": "string"}, "min_refresh": {"type": "integer"},
         "tier": {"type": "string", "description": "flagship/high/mid/entry"},
         "max_price": {"type": "integer"}, "region": {"type": "string", "description": "KR 또는 US"}},
         "required": []}},
    {"name": "recommend", "description": "자연어 니즈로 라인업 추천(시맨틱). 예:'밝은 거실 게이밍 가성비'",
     "input_schema": {"type": "object", "properties": {
         "query_text": {"type": "string"}, "brand": {"type": "string"},
         "limit": {"type": "integer"}}, "required": ["query_text"]}},
    {"name": "best_price", "description": "모델의 옵션별 현재 최저가(지역별).",
     "input_schema": {"type": "object", "properties": {
         "model_code": {"type": "string"}, "region": {"type": "string"}},
         "required": ["model_code"]}},
    {"name": "price_trend", "description": "특정 SKU 가격 추세(이력).",
     "input_schema": {"type": "object", "properties": {
         "sku_full": {"type": "string"}, "region": {"type": "string"}},
         "required": ["sku_full"]}},
    {"name": "price_by_region", "description": "동일 모델의 지역별 가격·실효OS 비교(한/미).",
     "input_schema": {"type": "object", "properties": {
         "model_code": {"type": "string"}}, "required": ["model_code"]}},
    {"name": "whats_new", "description": "해당 연도 발표/출시 신제품(announced=잠정).",
     "input_schema": {"type": "object", "properties": {
         "year": {"type": "integer"}, "brand": {"type": "string"}},
         "required": ["year"]}},
]

# 이름 → 실제 query 함수
_FN = {
    "compare": query.compare, "lineup": query.lineup, "search": query.search,
    "recommend": query.recommend, "best_price": query.best_price,
    "price_trend": query.price_trend, "price_by_region": query.price_by_region,
    "whats_new": query.whats_new,
}


def dispatch(name: str, tool_input: dict) -> str:
    """도구 호출 → query 함수 실행 → JSON 문자열(에러도 문자열로)."""
    try:
        result = _FN[name](**tool_input)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False)


def ask(question: str, max_turns: int = 6) -> str:
    """자연어 질문 → Claude tool-use 루프 → 최종 답변 텍스트."""
    import anthropic
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": question}]

    for _ in range(max_turns):
        resp = client.messages.create(
            model=MODEL, max_tokens=4096, system=SYSTEM,
            thinking={"type": "adaptive"}, tools=TOOLS, messages=messages,
        )
        if resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for b in resp.content:
                if b.type == "tool_use":
                    out = dispatch(b.name, b.input)
                    results.append({"type": "tool_result", "tool_use_id": b.id, "content": out})
            messages.append({"role": "user", "content": results})
            continue
        return "".join(b.text for b in resp.content if b.type == "text")
    return "(최대 도구 호출 횟수 초과)"


# ---- LLM 없이 도구 계층만 검증 ----
def selftest():
    print("=== dispatch 오프라인 검증(LLM 불필요) ===")
    cases = [
        ("compare", {"samsung_code": "QN90F"}),
        ("lineup", {"brand": "삼성", "year": 2025}),
        ("search", {"panel": "WOLED", "region": "US", "max_price": 1500}),
        ("recommend", {"query_text": "밝은 거실 게이밍 가성비", "limit": 2}),
        ("best_price", {"model_code": "G5", "region": "US"}),
        ("price_by_region", {"model_code": "QN90F"}),
        ("whats_new", {"year": 2026}),
        ("price_trend", {"sku_full": "65U8QG", "region": "US"}),
    ]
    ok = 0
    for name, args in cases:
        out = dispatch(name, args)
        bad = out.startswith('{"error"')
        rows = out.count("},{") + 1 if out.strip().startswith("[") and out.strip() != "[]" else (0 if out.strip() == "[]" else 1)
        print(f"  [{'X' if bad else 'OK'}] {name}({args}) → {out[:90]}{'…' if len(out) > 90 else ''}")
        ok += not bad
    print(f"--- {ok}/{len(cases)} 도구 정상 (도구 {len(TOOLS)}개 정의)")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "--selftest":
        selftest()
    else:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            sys.exit("ANTHROPIC_API_KEY 필요 (라이브 답변). 도구 검증만: --selftest")
        print(ask(" ".join(args)))
