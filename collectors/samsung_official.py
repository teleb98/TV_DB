"""
삼성 공식(samsung.com) 제품페이지/스펙 수집기 — STUB.
공식 소스는 '정확도 최우선' 계층. Series/Model 스펙 확보용.
※ TODO 위치에 실제 셀렉터/엔드포인트를 채우면 동작.
"""
from __future__ import annotations
import httpx                      # TODO: requirements 에 추가
from selectolax.parser import HTMLParser   # TODO: 경량 HTML 파서
from .base import BaseCollector, RawRecord
from config.selectors import SAMSUNG as SEL


class SamsungOfficialCollector(BaseCollector):
    source_name = "samsung_official"
    rate_limit_sec = 2.0

    def fetch(self, target: str) -> str:
        # target = 제품 상세페이지 URL
        r = httpx.get(target, timeout=20, headers={"User-Agent": "tv-spec-db/0.1"})
        r.raise_for_status()
        return r.text

    def parse(self, raw: str, source_url: str = "") -> list[RawRecord]:
        tree = HTMLParser(raw)
        records: list[RawRecord] = []

        # --- Model 스펙 추출 (셀렉터는 config/selectors.py:SAMSUNG) ---
        model_payload = {
            "brand": "삼성",
            "marketing_name":  self._text(tree, SEL["series_name"]),
            "model_code_raw":  self._text(tree, SEL["model_code"]),   # → 정규화 대상
            "resolution":      self._text(tree, SEL["resolution"]),
            "refresh_rate":    self._text(tree, SEL["refresh"]),
            "panel_marketing": self._text(tree, SEL["panel"]),        # 'Neo QLED' → 사전 변환
            "hdr":             self._text(tree, SEL["hdr"]),
            "processor":       self._text(tree, SEL["processor"]),
            "spec_table":      self._spec_table(tree),
        }
        records.append(RawRecord(self.source_name, "model", model_payload, source_url))

        # --- Variant(인치/색상 옵션) 추출 ---
        if SEL["size_options"]:
            for opt in tree.css(SEL["size_options"]):
                records.append(RawRecord(self.source_name, "variant", {
                    "sku_full":  opt.attributes.get("data-sku", ""),
                    "size_inch": self._parse_inch(opt.text()),
                    "region":    self.region,
                    "price_msrp": None,   # 공식몰 가격 있으면 채움
                }, source_url))
        return records

    # --- helpers ---
    @staticmethod
    def _text(tree, selector: str) -> str:
        if not selector:            # 미설정 셀렉터는 스킵
            return ""
        node = tree.css_first(selector)
        return node.text(strip=True) if node else ""

    @staticmethod
    def _spec_table(tree) -> dict:
        # TODO: 스펙표 <tr><th>/<td> 순회하여 {항목:값} dict 반환
        return {}

    @staticmethod
    def _parse_inch(text: str) -> int | None:
        import re
        m = re.search(r"(\d{2,3})\s*(?:인치|\")", text)
        return int(m.group(1)) if m else None
