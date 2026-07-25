# Claude.ai 파일 첨부로 모델 추가하기 (기여 가이드)

스펙시트·리테일 페이지·CSV 등을 **claude.ai에 첨부**하면 Claude가 이 DB의 표준 포맷(**골든 CSV**)으로 변환해 주고,
그 결과를 맥미니(`~/tv-spec-db`)에서 한 줄 명령으로 적재하면 공개 API(https://tv.rarebook.co.kr)에 즉시 반영됩니다.

```
[첨부] 스펙시트/리테일캡처/브랜드페이지/CSV/PDF
   │  claude.ai + 아래 "프롬프트 템플릿"
   ▼
[출력] 골든 CSV 행 (표준 스키마·enum 준수)
   │  data/golden/ 에 저장
   ▼
[적재] pipeline.py --load-golden → enrich → export   (멱등)
   ▼
[반영] PostgreSQL + 공개 API 즉시 갱신
```

---

## 1. 첨부할 수 있는 파일
- 브랜드 **스펙시트 PDF** / 제품 상세페이지를 저장한 텍스트·HTML
- **리테일 리스팅**(Amazon/Best Buy/다나와) 캡처·텍스트
- 이미 정리한 **CSV/엑셀**(형식 무관 — Claude가 표준 포맷으로 맞춤)
- RTINGS 등 **리뷰 실측표**(→ measurement), 에너지라벨(→ certification)

---

## 2. 표준 스키마 — 골든 CSV (`data/golden/*.csv`)

헤더(순서 고정):
```
brand,series_name,marketing_name,generation_year,panel_tech,tier,os,model_code_base,resolution,refresh_rate_native,hdr_formats,processor,dimming,peak_brightness_nits,sku_full,size_inch,region,price_msrp,gaming_features,connectivity
```

| 컬럼 | 설명 / 허용값 |
|---|---|
| `brand` | 삼성 / LG / Sony / TCL / Hisense / Huawei / Xiaomi |
| `series_name` | 내부 라인업명(예: `QN90`, `G`, `U8`). (brand+series_name+year 유일) |
| `marketing_name` | 마케팅명(예: `Neo QLED 4K`, `OLED evo G5`) |
| `generation_year` | 출시연도(예: 2025) |
| `panel_tech` | **OLED · WOLED · QD-OLED · Neo-QLED · Mini-LED · QLED · LED-LCD · Micro-LED** 중 하나 |
| `tier` | **flagship · high · mid · entry** 중 하나 |
| `os` | **Tizen · webOS · Google-TV · Android-TV · Roku · VIDAA · Fire-TV · HarmonyOS · other** |
| `model_code_base` | **정규화 base 코드**(예: `QN90F`,`G5`,`A95L`,`U8Q`). 지역 접미사 제외. 라인 내 유일 |
| `resolution` | `4K` / `8K` |
| `refresh_rate_native` | 네이티브 주사율 정수(예: 120,144,165). 모르면 공란 |
| `hdr_formats` | `\|` 구분(예: `Dolby Vision\|HDR10\|HLG`). 삼성은 Dolby Vision 미지원 |
| `processor` | 칩셋명(예: `NQ4 AI Gen3`,`α11 AI Gen2`). 모르면 공란 |
| `dimming` | **none · edge-lit · full-array · mini-led · per-pixel** |
| `peak_brightness_nits` | 스펙/대표 밝기 정수. 모르면 공란 |
| `sku_full` | 대표 SKU(예: `QN65QN90FAFXZA`). 없으면 공란 가능(적재는 되나 variant 생성엔 필요) |
| `size_inch` | 대표 인치 1개(예: 65). **전체 인치 목록은 CSV가 아니라 `scripts/load_sizes.py`로 별도 관리** |
| `region` | `KR` / `US` / `EU` / `Global` |
| `price_msrp` | 정가 정수(옵션) |
| `gaming_features` | `\|` 구분(예: `VRR\|ALLM\|144Hz\|FreeSync Premium Pro`) |
| `connectivity` | `\|` 구분(예: `HDMI2.1 x4\|eARC\|WiFi\|Bluetooth`) |

### 작성 규칙(중요)
1. **모르는 값은 채우지 말고 공란** — 추측 금지(품질 원칙). 대표/추정값을 쓸 땐 그 사실을 사용자에게 알림.
2. `model_code_base`는 **지역 접미사 없는 base**(QN65**QN90F**AFXZA → `QN90F`).
3. enum(패널/티어/OS/디밍/해상도)은 위 허용값만 사용.
4. 삼성 OLED/QLED는 **Dolby Vision 미지원**(HDR10+/HLG). LG·Sony·TCL·Hisense는 Dolby Vision 지원.
5. 배열 필드는 `|`로 구분(쉼표 X — CSV 구분자와 충돌).

---

## 3. claude.ai 프롬프트 템플릿 (파일 첨부 후 복붙)

> 아래를 그대로 붙여넣고 스펙시트/리스팅 파일을 첨부하세요.

```
첨부한 TV 자료를 아래 "골든 CSV" 스키마로 변환해줘. CSV 코드블록만 출력해.

헤더:
brand,series_name,marketing_name,generation_year,panel_tech,tier,os,model_code_base,resolution,refresh_rate_native,hdr_formats,processor,dimming,peak_brightness_nits,sku_full,size_inch,region,price_msrp,gaming_features,connectivity

규칙:
- brand: 삼성/LG/Sony/TCL/Hisense/Huawei/Xiaomi
- panel_tech: OLED/WOLED/QD-OLED/Neo-QLED/Mini-LED/QLED/LED-LCD/Micro-LED 중 하나
- tier: flagship/high/mid/entry
- os: Tizen/webOS/Google-TV/Android-TV/Roku/VIDAA/Fire-TV/HarmonyOS/other
- dimming: none/edge-lit/full-array/mini-led/per-pixel
- resolution: 4K/8K, region: KR/US/EU/Global
- model_code_base 는 지역접미사 없는 base 코드(예: QN65QN90FAFXZA → QN90F)
- hdr_formats/gaming_features/connectivity 는 | 로 구분
- 삼성 OLED/QLED 는 Dolby Vision 미지원(HDR10+/HLG)
- 모르는 값은 절대 추측하지 말고 공란. 대표/추정값을 넣었다면 표 아래에 어떤 값이 추정인지 명시.
- size_inch 는 대표 1개만. 제공 인치 전체 목록은 따로 알려줘(코드: {model_code_base}: [55,65,75,...]).
```

Claude가 (a) CSV 코드블록, (b) 인치 목록, (c) 추정값 표기를 함께 줍니다.

---

## 4. 맥미니에서 적재 (`~/tv-spec-db`)

```bash
cd ~/tv-spec-db
cp ~/Downloads/new_models.csv data/golden/          # Claude가 준 CSV 저장

# (선택) 실제 적재 전 정규화 검증 — DB 미변경
./.venv/bin/python pipeline.py --load-golden data/golden/new_models.csv --dry-run

# 적재(멱등: 같은 model_code_base 는 갱신)
export PG_DSN="postgresql://localhost/tvspec"
./.venv/bin/python pipeline.py --load-golden data/golden/new_models.csv

# 인치 목록 반영 → scripts/load_sizes.py 의 SIZES dict 에 추가 후:
./.venv/bin/python -m scripts.load_sizes

# 파생 데이터 갱신
./.venv/bin/python -m scripts.expand_variants        # 인치별 variant
./.venv/bin/python -m scripts.enrich_fill_empties    # 빈 필드 대표값
./.venv/bin/python -m scripts.build_aliases          # 지역 모델명
./.venv/bin/python scripts/build_comparison_map.py   # 삼성↔경쟁사 비교축
./.venv/bin/python -m scripts.export_json            # data/exports/* 재생성
```
→ 공개 API가 즉시 반영(별도 재시작 불필요). `curl -s https://tv.rarebook.co.kr/health` 로 건수 확인.

---

## 5. 스펙 외 데이터도 첨부로 추가
같은 방식으로 아래 계층도 Claude가 만들어 줄 수 있습니다(각 로더 dict 에 추가):
- **실측 성능**(RTINGS 리뷰 첨부) → `scripts/load_measurements.py` (밝기·입력랙·DCI-P3·명암비)
- **에너지/인증**(EPREL 라벨 첨부) → `scripts/load_certification.py` (등급·소비전력·EU SKU)
- **브랜드 feature 우선순위**(제품페이지 첨부) → `scripts/load_features.py` (rank1=상단=가장 중요)
- **가격**(리테일 캡처) → `scripts/load_retail_prices.py`(US) / `load_kr_prices.py`(국내)

데이터 출처·추정 여부 표기 규칙은 [`DATA_PROVENANCE.md`](DATA_PROVENANCE.md) 참고.

---

## 6. 팁
- 저장소가 public 이므로, claude.ai에 이 파일 URL을 함께 주면 스키마를 더 정확히 따릅니다.
- 여러 모델을 한 번에: CSV에 여러 행을 넣어 한 파일로 적재.
- 잘못 넣었을 때: 같은 `model_code_base`로 올바른 값 재적재(UPSERT) 또는 해당 행 삭제 후 재적재.
```
