# 미출시 제품 사양 사전확보 방안 (Pre-Release Sourcing)

미출시 경쟁사 제품의 사양을 **주요국 뉴스·인증DB·공급망 소스**에서 조기 확보하고,
**교차검증 후에만** 신뢰도를 올려 DB에 반영하는 방법론.

## 0. 대원칙
1. **격리**: 미확정 정보는 확정 `model` 테이블에 넣지 않고 **`pre_release_intel`** 테이블에 별도 적재(추측 오염 방지).
2. **다출처 교차검증**: 단일 루머는 `confidence=low`. **독립 출처 2곳 이상** 또는 **인증DB 등재** 시 `med`, **공식 발표/티저** 시 `high`.
3. **승격**: 실제 출시 + 사양 확정 시 `promoted_to`(model_code_base)로 연결하고 golden CSV 한 줄로 이관 → 이때부터 확정 데이터.
4. **출처 명시**: 모든 항목에 `source_org·source_country·source_url·report_date·source_tier` 기록.

## 1. 국가별 소스 맵

### 미국·글로벌 (영어)
| 유형 | 소스 |
|---|---|
| 리뷰/디스플레이 전문 | FlatpanelsHD, RTINGS(preview), HDTVTest, Display Daily, OLED-Info, Notebookcheck |
| IT 뉴스 | The Verge, Engadget, Tom's Guide, TechRadar, 9to5, AVForums(leaks) |
| 공급망/시장조사 | DSCC, Omdia, TrendForce(패널 로드맵·양산계획) |
| 전시회 | **CES(1월)·IFA(9월)** 발표·티저 |

### 중국 (중국어)
| 유형 | 소스 |
|---|---|
| IT 매체 | IT之家(ithome), 中关村在线(zol), 快科技(mydrivers), 泡泡网, 雷科技, Gizmochina(영문) |
| 유출 계정 | 微博 数码闲聊站(@DCS), 数码博主 |
| 유통 예고 | 京东/天猫 사전예약(预售) 페이지 |

### 한국 (한국어)
| 유형 | 소스 |
|---|---|
| 디스플레이/부품 | **디일렉(thelec.net)**, 전자신문(etnews), 디지털데일리(ddaily) — 패널 공급·양산 로드맵 조기 신호 |
| 유통 예고 | **다나와** 신제품 예고, 네이버 뉴스, 세티즌, 루리웹 |

### 인증DB (전세계 공통 · 최고 신뢰 사전 신호) — 출시 전 필수 등록
| DB | 국가 | 조기 노출 정보 |
|---|---|---|
| **EPREL** | EU | 정식 모델명·해상도·대각선·소비전력·에너지등급 (출시 수주 전 등록) |
| **FCC ID** | US | 무선모듈·내부라벨·규격 |
| **RRA(국립전파연구원)** | KR | 전파인증 모델명·기획명 매핑 |
| **Bluetooth SIG / HDMI Forum / Wi-Fi Alliance** | Global | 모델명·규격 사전 등재 |
→ 이미 있는 `certification` 테이블(eprel_model·fcc_id·rra_id)과 연계. **인증DB 등재 = confidence med 자동 상향 근거.**

## 2. source_tier & confidence 프로토콜
| source_tier | 예 | 기본 confidence |
|---|---|---|
| `leak` | 유출계정·미확인 루머 | low |
| `supply-chain` | 디일렉/DSCC 패널 양산계획 | low~med |
| `rumor` | 매체 추정 기사 | low |
| `cert` | EPREL/FCC/RRA 등재 | **med** |
| `tradeshow` | CES/IFA 현장 티저 | med~high |
| `official-teaser` | 브랜드 공식 예고 | **high** |

**상향 규칙**: 독립 출처 `corroboration≥2` → 한 단계 상향. `cert` 등재 확인 → 최소 med. 공식 발표 → high. 출시+리뷰 → 승격(`status=released`).

## 3. 실행 파이프라인
1. **수집**: 국가별 WebSearch 쿼리(아래 템플릿) → 스니펫에서 (브랜드·잠정모델·사양·출처·연도) 추출.
2. **적재**: `scripts/load_rumors.py` 의 딕셔너리에 항목 추가 → `pre_release_intel` upsert(멱등).
3. **조회**: API `GET /api/rumors?brand=&year=&status=` (신뢰도·출처 순).
4. **승격**: 출시 확정 시 golden CSV 로 이관 + `pre_release_intel.status='released', promoted_to=<코드>` 갱신.

### 국가별 검색 쿼리 템플릿
```
US:  "{brand} 2027 TV leak specs Micro RGB OR RGB OLED next-gen"
     "{brand} IFA 2026 preview OR roadmap panel"
CN:  "{brand} 2027 电视 爆料 参数 Mini LED RGB"  (ithome/zol/mydrivers)
KR:  "{brand} 2027 TV 로드맵 패널 양산 디일렉"   / "{brand} 신제품 예고 다나와"
Cert:"{brand} {model} EPREL"  /  "FCC ID {grantee}"  /  "RRA 전파인증 {brand}"
```

## 4. 현재 확보된 실증 사례 (pre_release_intel 시드)
- **LG Micro RGB evo**(75/86/100″) — LG 공식 예고, US/TechRadar·Engadget, `official-teaser`.
- **Samsung QD-OLED Penta Tandem**(5층 패널) — FlatpanelsHD, Global, `supply-chain`.
- **LG QD-OLED 게이밍 모니터**(삼성디스플레이 패널 공급 협의) — 디일렉(thelec)·OLED-Info, KR, `supply-chain`.
- **Samsung Display 24″ OLED 모니터**(2027 양산계획 유출) — choose.tv, US, `leak`.

## 5. 주의
- 미출시 정보는 **변동성이 큼** → `report_date` 로 시점 고정, 출시 시 반드시 재검증.
- 저작권/약관 준수(원문 복제 금지, 요약·출처링크). 스펙시트 원문은 인용만.
