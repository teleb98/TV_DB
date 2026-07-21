"""
정규화 엔진 — 이 프로젝트 성패의 핵심.
1) 모델명 파편화 통일   (KQ65QNA90DXKR → base 'QN90D')
2) 마케팅명 → 실제 스펙  (Neo QLED → Mini-LED)
3) 단위/표기 통일        ('120㎐' → 120)
canonical_dict 테이블을 런타임 사전으로 로드해 적용한다.
"""
from __future__ import annotations
import re

# ---- 사전(초기 seed). 실제로는 canonical_dict 테이블에서 로드 ----
PANEL_MAP = {
    "neo qled": "Neo-QLED", "qled": "QLED", "oled evo": "WOLED", "oled": "OLED",
    "qd-oled": "QD-OLED", "mini led": "Mini-LED", "mini-led": "Mini-LED",
    "uled": "Mini-LED", "uhd": "LED-LCD",
}
BRAND_MAP = {
    "samsung": "삼성", "삼성전자": "삼성", "lg전자": "LG", "lg": "LG",
    "sony": "Sony", "소니": "Sony", "tcl": "TCL", "hisense": "Hisense", "하이센스": "Hisense",
}


def norm_brand(raw: str) -> str:
    return BRAND_MAP.get((raw or "").strip().lower(), raw)


def norm_panel(raw: str) -> str:
    return PANEL_MAP.get((raw or "").strip().lower(), raw)


def norm_refresh(raw) -> int | None:
    """'120㎐','120 Hz','네이티브 120' → 120"""
    if raw is None:
        return None
    m = re.search(r"(\d{2,3})", str(raw))
    return int(m.group(1)) if m else None


def norm_inch(raw) -> int | None:
    m = re.search(r"(\d{2,3})", str(raw or ""))
    return int(m.group(1)) if m else None


# ---- 모델명 정규화: 브랜드별 규칙(순서대로 매칭, 먼저 맞는 것 채택) ----
# 각 항목: (정규식, 결과 포맷). 결과는 매치 그룹으로 조립.
#  ⚠ 앞자리 사이즈(예: 65)를 base로 오인하지 않도록 시리즈 접두어를 앵커로 씀.
MODEL_RULES: dict[str, list[tuple[str, str]]] = {
    "삼성": [
        (r"QN[A-Z]?(\d{2,3})([A-Z])", r"QN\1\2"),   # Neo QLED: QNA90D→QN90D, QNA900D→QN900D
        (r"S[A-Z]?(\d{2})([A-Z])",     r"S\1\2"),     # OLED: SD95D→S95D
        (r"(DU)(\d{4})",               r"\1\2"),       # Crystal UHD: DU8000
        (r"(QN)(\d{2,3})",             r"\1\2"),       # 보수적 fallback
    ],
    "LG": [
        (r"OLED\d{2}([A-Z]\d)",  r"\1"),               # OLED65G4→G4, C4, B4
        (r"(QNED)(\d{2}[A-Z])",  r"\1\2"),             # QNED90T
    ],
    "Sony": [
        (r"XR-?\d{2,3}([A-Z]\d{2}[A-Z])", r"\1"),      # 구형 SKU 내 A95L/X90L 형태
        (r"(XR)(\d{2})\b",                r"\1\2"),      # 2024 신명명: K-65XR90→XR90
        (r"([AX]\d{2}[A-Z])\b",           r"\1"),         # A95L, A80L, X90L
    ],
    "TCL": [
        (r"(QM\d{3}[A-Z])", r"\1"),                     # QM851G
        (r"(C\d{3})",       r"\1"),                      # C855, C845 (앞 사이즈와 경계 없음)
    ],
    "Hisense": [
        (r"(U\d[A-Z])", r"\1"),                         # U8N, U7N, U6N, U8K
    ],
}


def base_model_code(sku: str, brand: str) -> str | None:
    """정식 SKU에서 세대·급을 담은 base 코드 추출.
    예) 삼성 KQ65QNA90DXKR→QN90D · LG OLED65G4KNA→G4 · Sony XR-65A95L→A95L
        TCL 65QM851G→QM851G · Hisense 65U8N→U8N"""
    s = (sku or "").upper()
    for pattern, repl in MODEL_RULES.get(brand, []):
        m = re.search(pattern, s)
        if m:
            return re.sub(pattern, repl, m.group(0))
    return None


def normalize_record(rec: dict) -> dict:
    """RawRecord.payload → 스키마 정합 dict. 파이프라인 적재 직전 호출."""
    out = dict(rec)
    if "brand_raw" in out or "brand" in out:
        out["brand"] = norm_brand(out.get("brand") or out.get("brand_raw"))
    if "panel_marketing" in out:
        out["panel_tech"] = norm_panel(out["panel_marketing"])
    if "refresh_rate" in out:
        out["refresh_rate_native"] = norm_refresh(out["refresh_rate"])
    if "size_inch" in out and not isinstance(out["size_inch"], int):
        out["size_inch"] = norm_inch(out["size_inch"])
    # base 모델코드: sku_full(옵션) 또는 model_code_raw(모델 페이지)에서 추출
    code_src = out.get("sku_full") or out.get("model_code_raw")
    if code_src and out.get("brand"):
        out["model_code_base"] = base_model_code(code_src, out["brand"])
    return out
