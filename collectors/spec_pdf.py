"""
공식 스펙시트(PDF/카탈로그) → 구조화 파서 — STUB.
정확도 최우선 소스. 비정형 PDF를 Claude로 스키마 필드에 맞춰 추출.
model.py 스키마 필드명과 1:1 정합되도록 출력 스키마 고정.
"""
from __future__ import annotations
import json
import pathlib
from anthropic import Anthropic     # TODO: requirements 에 추가
from pypdf import PdfReader          # TODO: PDF 텍스트 추출
from .base import BaseCollector, RawRecord

MODEL = "claude-opus-4-8"   # 정확도 우선. 대량 배치 시 claude-haiku-4-5 로 비용 절감 검토.

# LLM이 반드시 이 JSON 스키마로만 답하도록 강제 (스키마 필드와 정합)
EXTRACT_SCHEMA = {
    "series": {"marketing_name": "", "panel_marketing": "", "tier": "", "key_features": []},
    "model": {
        "model_code_raw": "", "resolution": "", "refresh_rate_native": 0,
        "hdr_formats": [], "processor": "", "dimming": "",
        "peak_brightness_nits": 0, "audio_channels": "", "connectivity": [],
        "gaming_features": [],
    },
    "variants": [   # 인치별로 값이 다른 항목은 반드시 옵션별로 분리
        {"size_inch": 0, "sku_full": "", "peak_brightness_nits": 0,
         "local_dimming_zones": 0, "weight_kg": 0.0, "power_w": 0}
    ],
}

SYSTEM = (
    "너는 TV 공식 스펙시트에서 사실만 추출하는 파서다. "
    "주어진 JSON 스키마의 키만 채워라. 문서에 없는 값은 null. "
    "마케팅 명칭은 그대로 두되 임의 추정 금지. 인치별로 다른 수치는 variants 배열에 옵션별로 분리하라."
)


class SpecPdfCollector(BaseCollector):
    source_name = "spec_pdf"
    rate_limit_sec = 0.0

    def __init__(self, region: str = "KR"):
        super().__init__(region)
        self.client = Anthropic()   # ANTHROPIC_API_KEY 환경변수 필요

    def fetch(self, target: str) -> str:
        # target = 로컬 PDF 경로. 텍스트 레이어 추출(스캔본이면 OCR 필요 — TODO).
        reader = PdfReader(target)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    def parse(self, raw: str, source_url: str = "") -> list[RawRecord]:
        data = self._extract(raw)
        recs: list[RawRecord] = []
        if data.get("series"):
            recs.append(RawRecord(self.source_name, "series", data["series"], source_url))
        if data.get("model"):
            recs.append(RawRecord(self.source_name, "model", data["model"], source_url))
        for v in data.get("variants", []):
            recs.append(RawRecord(self.source_name, "variant", v, source_url))
        return recs

    def _extract(self, text: str) -> dict:
        msg = self.client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM,
            messages=[{"role": "user", "content":
                f"스키마:\n{json.dumps(EXTRACT_SCHEMA, ensure_ascii=False)}\n\n"
                f"스펙시트 텍스트:\n{text[:12000]}\n\n"
                "위 스키마 형식의 JSON만 출력."}],
        )
        out = msg.content[0].text.strip()
        out = out[out.find("{"): out.rfind("}") + 1]   # 코드펜스 방어
        return json.loads(out)
