# 데이터 출처(Provenance) 사전

각 필드 값이 **어디서 왔는지**와 **추정치의 근거**를 정의한다.
단일 소스는 [`provenance.py`](../provenance.py) — 이 문서·`enrich_fill_empties.py`·`export_json.py` 가 이를 사용한다.

## 표기 방식
- `model.estimated_fields` / `variant.estimated_fields` (TEXT[]) — 해당 행에서 **규칙 기반 추정치**인 컬럼명 목록.
- export 파일(`tvspec_*.json`) 최상위 `provenance` 블록에 근거 범례가 함께 실린다.
- CSV(`tvspec_models.csv`)에는 `estimated_fields` 컬럼으로 표기.

값이 채워져 있어도 `estimated_fields` 에 있으면 **정확도 보증이 아니며 공식 스펙시트 대조 검수가 필요**하다.

---

## ① ESTIMATED — 규칙 기반 대표 추정치 (모델별 편차 큼)

| 필드 | 근거 |
|---|---|
| `model.audio_channels` | 티어·브랜드 규칙 대표값 (8K=6.2.4 / 플래그십=4.2.2·4.2 / high=2.2 / mid=2.0). 실제 채널구성은 모델별 상이. |
| `model.audio_output_w` | 티어·브랜드 규칙 대표 총출력(W). ±20W 편차 가능. |
| `variant.weight_kg` | 사이즈(inch)×0.35, OLED 0.82배, 0.5kg 반올림 추정. 스탠드 포함여부·패널세대로 편차. |
| `variant.power_w` | 사이즈×패널계수(Mini-LED 3.0·OLED 2.3·LCD 2.6), 10W 반올림. 일반사용 근사(피크 아님). |
| `variant.local_dimming_zones` | Mini-LED/FALD 티어별 대표값(mini-led flagship 1344·high 512·mid 256 / full-array 128·64·48). 실제 존 수는 모델별 상이. **OLED·엣지형은 null(해당없음)** → estimated_fields 에서도 제외. |
| `variant.color` | 대표 기본 색상 가정(대부분 단일 블랙 계열). |
| `variant.stand_type` | 티어 기본값 가정(flagship·high=중앙 스탠드, mid=양측 다리). |

## ② DERIVED — 결정적 도출값 (신뢰 높음, estimated_fields 에 없음)

| 필드 | 근거 |
|---|---|
| `brand.country` | 브랜드 본사 소재국(공개사실). |
| `model.smart_os_version` | 브랜드+연도 매핑(삼성 Tizen 7.0~10.0 / LG webOS 23~26 / Sony·TCL·Xiaomi Google TV / Hisense VIDAA U / Huawei HarmonyOS 4). |
| `series.key_features` | 해당 모델의 실제 스펙(패널·주사율·밝기·HDR·게이밍)에서 파생. |
| `variant.availability` | 연도·지역 도출(≥2026 출시예정 / region=Global 해외판매 / 그외 판매중). |
| `variant.source_url` | 브랜드 공식 홈페이지(딥링크 아닌 출처 도메인). |
| `comparison_map.price_band` | tier_match 파생(flagship 프리미엄·high 상위·mid 중급·entry 보급). |
| `model.size_variants_in` | 각 브랜드 공식 제품페이지·뉴스룸·RTINGS(2026-07)에서 확인한 제공 인치(`scripts/load_sizes.py`, 소스 주석). **`estimated_fields`에 `size_variants_in`이 있으면 공식 확인 불가(추정) 모델** — Huawei 전체·Xiaomi S-OLED/A-Pro·삼성 QN85F·TCL QM6K/QM7K·Hisense U6Q/U7Q·LG B6. 삼성 2026(QN990G/S95G/QN90G)은 실제 코드가 H접미사(S95H 등)와 불일치해 미적재. |

## ③ RULE_DERIVED — 기존 enrich 규칙 스펙 (참고)

| 필드 | 근거 |
|---|---|
| `model.peak_brightness_nits` | `enrich_brightness.py` — 리뷰(RTINGS 등) 실측 + 동급 근사치 혼재. |
| `model.gaming_features` | `enrich_gaming.py` — 브랜드·티어·주사율 규칙. |
| `model.connectivity` | `enrich_gaming.py` — HDMI2.1 포트수 등 브랜드·티어 규칙. |

## ③-b CONSTRUCTED — 구성(생성) 값

| 필드 | 근거 |
|---|---|
| `variant.sku_full` | 인치 세분화(`scripts/expand_variants.py`)로 생성한 변형의 SKU는 구성값 **`{code}-{size}IN-{region}`** — 실제 판매 SKU 아님. `estimated_fields`에 `sku_full` 표기. 골든셋 원본 변형(대표 65인치 등, 실SKU)은 구성값 아님. 인치별 US 가격(QN90F·QM6K·QM7K)은 공식 확인 MSRP(구성 아님). |

## ③-c MEASURED — 실측 성능 (measurement 테이블)

RTINGS·FlatpanelsHD·AVForums 등 전문 리뷰 **실측치**. `measurement` 테이블(모델당 1행), 각 행 `source` 컬럼에 출처 표기. 추정 아님(실측). `model.peak_brightness_nits`(스펙/근사)와 **별개**로 `measurement.peak_brightness_nits`(실측)를 둔다.

| 필드 | 의미 |
|---|---|
| `peak_brightness_nits` | HDR 10% window 실측 피크 |
| `fullscreen_nits` | 전체화면 실측 밝기 |
| `input_lag_ms` | 4K/120Hz 입력랙 |
| `dci_p3_pct` / `rec2020_pct` | 색재현 커버리지 |
| `contrast` | 네이티브 명암비(‘inf’=OLED) |

로더 `scripts/load_measurements.py`(WebSearch 스니펫 확인). ※ DisplaySpecifications(SoC/RAM/tuner/VESA)는 봇차단으로 미수집 — `model.tuner`/`vesa_mm` 컬럼만 준비됨. TechSpecs API는 키 필요로 미연동.

## ④ SOURCED — 큐레이션 스펙 (골든셋 원본)
`panel_tech·resolution·refresh_rate_native·hdr_formats·processor·dimming·sku_full·size_inch·region·price_*` 등은 골든셋 CSV의 큐레이션 대표값(공식 대조 검수 전제).

---

## 정확값으로 교체하는 법
추정 필드에 공식값이 확보되면 해당 `enrich_*.py` 의 딕셔너리를 실측/공식값으로 채우고 재실행 → `estimated_fields` 에서 자동 제외되도록 `provenance.ESTIMATED` 에서 그 필드를 빼면 된다.
