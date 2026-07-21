"""
다나와 수집기 — STUB.
'커버리지 최우선' 계층: 모델 리스트 + Variant(SKU) + 가격.
경쟁사(LG/Sony/TCL/Hisense) 옵션·가격도 여기서 폭넓게 확보.
⚠ 크롤링 전 robots.txt / 이용약관 확인. 가능하면 제휴 API 우선.
"""
from __future__ import annotations
from selectolax.parser import HTMLParser
from .base import BaseCollector, RawRecord, fetch_html
from config.selectors import DANAWA as SEL


class DanawaCollector(BaseCollector):
    source_name = "danawa"
    rate_limit_sec = 2.5     # 예의상 넉넉히

    def fetch(self, target: str) -> str:
        return fetch_html(target, ua="tv-spec-db/0.1")

    def parse(self, raw: str, source_url: str = "") -> list[RawRecord]:
        tree = HTMLParser(raw)
        records: list[RawRecord] = []
        # 검색결과/카테고리 페이지의 상품 카드 순회 (셀렉터: config/selectors.py:DANAWA)
        if not SEL["product_card"]:
            return records          # 셀렉터 미설정 시 빈 결과(안전)
        for card in tree.css(SEL["product_card"]):
            records.append(RawRecord(self.source_name, "variant", {
                "sku_full":    self._text(card, SEL["model_name"]),   # 다나와 표기 모델명 → 정규화 대상
                "brand_raw":   self._text(card, SEL["brand"]),
                "size_inch":   None,   # 상품명에서 정규식 추출(normalize 단계)
                "price_street": self._price(card, SEL["price"]),
                "region":      self.region,
                "availability": "in_stock",
            }, source_url))
        return records

    @staticmethod
    def _text(node, selector: str) -> str:
        if not selector:
            return ""
        n = node.css_first(selector)
        return n.text(strip=True) if n else ""

    @staticmethod
    def _price(node, selector: str):
        import re
        t = DanawaCollector._text(node, selector)
        digits = re.sub(r"[^\d]", "", t)
        return int(digits) if digits else None
