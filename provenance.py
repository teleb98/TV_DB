"""
필드 출처(provenance) 단일 소스 — 추정 데이터 표기·근거 주석의 기준.

3분류:
  ESTIMATED    규칙 기반 대표 추정치. 모델별 편차 큼 → 공식 대조 검수 전제.
               (record.estimated_fields 로 행별 표기됨)
  DERIVED      다른 실데이터/공개사실에서 결정적으로 도출(신뢰 높음).
  RULE_DERIVED 기존 enrich_*.py 규칙으로 도출된 스펙(실측+동급근사 혼재, 참고).

이 파일이 근거 텍스트의 원본이며, enrich_fill_empties.py(표기 기록)·export_json.py(범례)·
docs/DATA_PROVENANCE.md 가 이를 사용/반영한다.
"""
from __future__ import annotations

# --- 규칙 기반 대표 추정치 (행별 estimated_fields 로 표기) ---
ESTIMATED: dict[str, dict[str, str]] = {
    "model": {
        "audio_channels": "티어·브랜드 규칙 대표값 (8K=6.2.4 / 플래그십=4.2.2·4.2 / high=2.2 / mid=2.0). 실제 채널구성은 모델별 상이.",
        "audio_output_w": "티어·브랜드 규칙 대표 총출력(W). ±20W 편차 가능.",
    },
    "variant": {
        "weight_kg": "사이즈(inch)×0.35, OLED 0.82배, 0.5kg 반올림 추정. 스탠드 포함여부·패널세대로 편차.",
        "power_w": "사이즈×패널계수(Mini-LED 3.0·OLED 2.3·LCD 2.6), 10W 반올림. 일반사용 근사(피크 소비전력 아님).",
        "local_dimming_zones": "Mini-LED/FALD 티어별 대표값(mini-led flagship 1344·high 512·mid 256 / full-array 128·64·48). 실제 존 수는 모델별 상이. OLED·엣지형은 null(해당없음).",
        "color": "대표 기본 색상 가정(대부분 단일 블랙 계열).",
        "stand_type": "티어 기본값 가정(flagship·high=중앙 스탠드, mid=양측 다리).",
    },
}

# --- 결정적 도출값 (신뢰 높음) ---
DERIVED: dict[str, str] = {
    "brand.country": "브랜드 본사 소재국(공개사실).",
    "model.smart_os_version": "브랜드+연도 매핑 (삼성 Tizen 7.0~10.0 / LG webOS 23~26 / Sony·TCL·Xiaomi Google TV / Hisense VIDAA U / Huawei HarmonyOS 4).",
    "series.key_features": "해당 모델의 실제 스펙(패널·주사율·밝기·HDR·게이밍)에서 파생.",
    "variant.availability": "연도·지역 도출 (≥2026 출시예정 / region=Global 해외판매 / 그외 판매중).",
    "variant.source_url": "브랜드 공식 홈페이지(딥링크 아닌 출처 도메인).",
    "comparison_map.price_band": "tier_match 파생 (flagship 프리미엄 · high 상위 · mid 중급 · entry 보급).",
    "model.size_variants_in": "각 브랜드 공식 제품페이지·뉴스룸·RTINGS(2026-07)에서 확인한 제공 인치 목록(scripts/load_sizes.py, 소스 주석 포함). estimated_fields 에 'size_variants_in' 이 있으면 공식 확인 불가(추정) 모델.",
}

# --- 구성(생성) 값 — 실제 판매값 아님, estimated_fields 로 표기 ---
CONSTRUCTED: dict[str, str] = {
    "variant.sku_full": "인치 세분화(scripts/expand_variants.py)로 생성한 변형의 SKU는 구성값 '{code}-{size}IN-{region}' — 실제 판매 SKU 아님. 골든셋 원본 변형(대표 65인치 등)은 구성값 아님.",
}

# --- 규칙 도출 스펙 (기존 enrich_*.py) — 참고 표기 ---
RULE_DERIVED: dict[str, str] = {
    "model.peak_brightness_nits": "enrich_brightness.py — 리뷰(RTINGS 등) 실측 + 동급 근사치 혼재.",
    "model.gaming_features": "enrich_gaming.py — 브랜드·티어·주사율 규칙.",
    "model.connectivity": "enrich_gaming.py — HDMI2.1 포트수 등 브랜드·티어 규칙.",
}

LEGEND = ("estimated_fields = 규칙 기반 추정치(모델별 편차 큼, 공식 스펙시트 대조 검수 전제). "
          "값 자체는 채워져 있으나 정확도 보증 아님. sourced/derived 는 estimated_fields 에 없음.")


def estimated_for(table: str, row: dict) -> list[str]:
    """해당 행에서 값이 채워진 추정 필드명 목록(값이 null이면 제외)."""
    return [f for f in ESTIMATED.get(table, {}) if row.get(f) is not None]


def legend() -> dict:
    """export 최상위에 실을 근거 범례."""
    return {"legend": LEGEND, "estimated": ESTIMATED, "derived": DERIVED,
            "constructed": CONSTRUCTED, "rule_derived": RULE_DERIVED}
