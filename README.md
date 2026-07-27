# TV Spec DB — 삼성 vs 경쟁사 TV 제품정보 Agent용 DB

스펙 비교 상담봇 + 라인업 안내 Agent를 위한 제품정보 DB 구축 프로젝트.

- **대상**: 삼성 / LG / Sony / TCL / Hisense / Huawei / Xiaomi · KR/US/EU/Global · 2023~2026
- **핵심**: 옵션(Variant) 단위까지 모델링 + 삼성↔경쟁사 비교축
- **모델 추가**: 📄 [**claude.ai 파일 첨부로 DB 추가하기**](docs/ADD_VIA_CLAUDE.md) — 스펙시트·리테일 페이지를 첨부하면 골든 CSV로 변환→한 줄 적재

## 데이터 모델 (4계층)
```
Brand → Series(라인업) → Model(스펙) → Variant(옵션: 인치/지역/색상/스탠드)
        + Comparison_Map(비교축) · Canonical_Dict(정규화 사전) · Price_History
```
- **라인업 안내** → Series 계층 (positioning 필드 RAG)
- **스펙 비교** → Model 계층 (정규화 스펙)
- **옵션/가격** → Variant 계층 (인치별 값 override)

## 구조
```
schema/schema.sql              4계층 DDL (PostgreSQL)
config/targets.py              소스별 수집 타깃 URL (국내/북미)
config/selectors.py            소스별 CSS 셀렉터 (한 곳 관리)
collectors/base.py             수집기 공통 뼈대 (fetch→parse→RawRecord) + 렌더 도메인 분기
collectors/render.py           렌더링 Fetcher(Playwright) — JS/안티봇 사이트 ✅
crawler/frontier.py            크롤 큐 + 원본해시 변경감지(재크롤 스킵) ✅
crawler/change_detector.py     가격인하/신제품/단종 이벤트 발행 ✅
collectors/samsung_official.py 삼성 공식 (정확도 우선)   [셀렉터 미정]
collectors/danawa.py           다나와 (커버리지·가격 우선) [셀렉터 미정]
collectors/spec_pdf.py         스펙시트 PDF→Claude 구조화  [STUB]
normalize/normalizer.py        모델명·마케팅명·단위 정규화 (성패 핵심) ✅검증
db.py                          4계층 upsert (psycopg, ON CONFLICT) ✅
pipeline.py                    수집→정규화→적재 + 골든 로더 ✅
scripts/build_comparison_map.py 삼성↔경쟁사 동급 매핑 생성기 ✅
embed/embedder.py              임베더(model2vec 다국어 + 해시 폴백)
scripts/build_embeddings.py    positioning→pgvector 임베딩 적재
agent/query.py                 상담봇 질의 (compare/lineup/search/recommend/가격/신제품) ✅
agent/assistant.py             tool-use 에이전트(Claude가 질의도구 호출→자연어 답변) ✅
agent/demo.py                  질의 데모 러너
tools/inspect_page.py          실제 페이지→후보 셀렉터 추출 헬퍼
data/golden/golden_models.csv       검증용 골든셋 (46개, 2023~2025 released)
data/golden/golden_models_2026.csv  2026 발표 모델 (잠정, announced/low)
data/golden/golden_models_us.csv    US(미국) variant — 동일 모델·US SKU·USD
```

## 빠른 시작 (검증된 절차)
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
createdb tvspec && psql tvspec -f schema/schema.sql            # 스키마(7 테이블)
export PG_DSN="postgresql://localhost/tvspec"
.venv/bin/python pipeline.py --load-golden data/golden/golden_models.csv       # 골든셋(2023~25)
.venv/bin/python pipeline.py --load-golden data/golden/golden_models_2026.csv  # 2026 발표(잠정)
.venv/bin/python scripts/load_positioning.py data/golden/series_positioning.csv  # 라인업 설명
.venv/bin/python scripts/build_comparison_map.py             # 비교축 생성
.venv/bin/python scripts/load_prices.py data/golden/prices_kr.csv  # 가격 스냅샷→price_history
psql tvspec -c "CREATE EXTENSION IF NOT EXISTS vector;"       # pgvector(RAG용)
.venv/bin/python scripts/build_embeddings.py                 # 라인업 임베딩→series_embedding
.venv/bin/python -m agent.demo                               # 질의 함수 데모
.venv/bin/python -m agent.assistant --selftest               # 에이전트 도구계층 검증(LLM 불필요)
ANTHROPIC_API_KEY=... .venv/bin/python -m agent.assistant "QN90F랑 경쟁사 비교해줘"  # 자연어 상담
```

## 수집기 검증 & 실사이트 연결
수집기 파싱 경로는 HTML 픽스처로 end-to-end 검증됨:
```bash
PG_DSN=postgresql://localhost/tvspec .venv/bin/python -m tests.test_samsung_fixture
# fetch(픽스처)→parse→normalize→DB variant upsert, QN90D 55/65/75/85형 적재 확인
```
`collectors/base.py:fetch_html()` 는 http(s)면 GET, 아니면 로컬 파일 → 픽스처/실URL 공용.

**⚠ 실사이트 연결 시 주의 (정적 크롤링 한계)**
- samsung.com·다나와 제품페이지는 상당 부분 **JS 렌더링/안티봇** → `httpx`(정적)로는 스펙표가 안 잡힐 수 있음.
- 대응 우선순위:
  1. **공식 API/제휴 데이터**(다나와 제휴, 삼성 파트너 피드) — 가장 안정적
  2. **공식 스펙시트 PDF**(`spec_pdf` 수집기) — 정확도 최상, JS 무관
  3. **헤드리스 브라우저**(Playwright)로 렌더 후 HTML 추출 → 기존 `parse()` 재사용
- 셀렉터 확정 절차: `tools/inspect_page.py <url>` 로 후보 추출 → `config/selectors.py` 채움 → 픽스처처럼 골든셋으로 검증.

## 가격 수집 스케줄링 (운영)
```bash
.venv/bin/python scripts/collect_prices.py         # 수동 1회(수집→스냅샷→price_history)
# launchd 등록(매일 03:00):
cp deploy/com.tvspecdb.prices.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.tvspecdb.prices.plist
launchctl start com.tvspecdb.prices                # 즉시 1회 실행
```
- 러너는 타깃별 예외 격리 + 3xx 추종 → 한 소스 실패해도 배치 지속. 로그: `data/logs/`.
- ⚠ danawa 셀렉터 미설정/JS 렌더링이면 0건 수집(정상 종료). 셀렉터 확정 시 자동 축적.

## DB 제공 (읽기 전용 JSON API) — 맥미니 배포
DB 를 HTTP 로 제공하는 stdlib(의존성 무추가) 서버. `agent/query.py` 를 래핑.
```bash
# 로컬 실행
PORT=3004 ./.venv/bin/python -m serve.api        # http://127.0.0.1:3004
# 상주(LaunchAgent) 설치
cp deploy/com.tvspecdb.web.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.tvspecdb.web.plist
launchctl kickstart -k gui/501/com.tvspecdb.web  # 재시작
```
- **공개 주소**: `https://tv.rarebook.co.kr` (Cloudflare Tunnel `rarebook` → 127.0.0.1:3004).
- **엔드포인트**(전부 GET, 읽기 전용): `/health` · `/api/brands` · `/api/lineup` · `/api/compare?samsung=` · `/api/whats_new?year=` · `/api/search` · `/api/recommend?q=` · `/api/price/{best,region,trend}`. 목록·검색어휘는 `GET /`.
- **활용(Claude.ai 누적)**: Claude.ai 가 이 API 를 호출해 현재 DB 를 읽고, 신규 모델·가격·리뷰는 골든셋 CSV/로더로 적재 → API 가 즉시 반영. 쓰기는 API 로 노출하지 않음(파이프라인 전용).

## 완료 / 남은 일
- [x] 4계층 스키마 · 정규화 엔진(골든셋 46/46 통과, 2023~2025) · DB upsert(멱등)
- [x] Comparison_Map 생성기 · Agent 질의계층(compare/lineup/search/recommend)
- [x] `series.positioning` 시드 + 라인업 추천 **pgvector 시맨틱 RAG**(model2vec, 키워드 폴백)
- [x] 수집기 파싱 경로 픽스처 검증(fetch→parse→normalize→DB)
- [x] 가격 스냅샷 파이프라인(`price_history` 축적, 추세/최저가 질의, 재적재 멱등)
- [x] 멀티리전(KR 52·US 20 variant, 2023~2025) — 지역별 SKU·통화·가격이력 + `price_by_region()`
- [x] 지역별 OS 차이 모델링 — `variant.os_override`(예: Hisense US=Google-TV vs KR=VIDAA)
- [x] tool-use 에이전트 — 8개 질의도구를 Claude(claude-opus-4-8)에 노출, 자연어 상담(도구계층 검증 완료; 라이브는 `ANTHROPIC_API_KEY` 필요)
- [x] 7개 브랜드 커버 — 삼성·LG·Sony·TCL·Hisense + **Huawei·Xiaomi(2025, region=Global)**
- [x] `series.status`/`data_confidence` 컬럼 제거(2026-07-25) — 수명주기 라벨 미사용으로 정리
- [x] 빈 필드 보강(`scripts/enrich_fill_empties.py`, 멱등) — 국가·OS버전·key_features·availability·source_url·price_band(결정적 도출) + 오디오·무게·소비전력·디밍존(티어/사이즈 대표 추정치, **근사값·공식 대조 검수 전제**). `local_dimming_zones`는 Mini-LED/full-array만 채우고 OLED/엣지형은 NULL(해당없음).
- [x] **추정 데이터 표기** — `model`/`variant`에 `estimated_fields TEXT[]` 컬럼으로 행별 추정 필드 표기. 근거 단일 소스 [`provenance.py`](provenance.py) + 사전 [`docs/DATA_PROVENANCE.md`](docs/DATA_PROVENANCE.md). export 파일 최상위 `provenance` 범례에 근거 동봉.
- [x] **인치 세분화(2025–2026)** — `model.size_variants_in INT[]`에 각 브랜드 공식 사이트 확인 제공 인치(`scripts/load_sizes.py`, 소스 주석). 33종 적재 **확인 27·추정 6**. 공식 확인 불가(Hisense U6Q·Huawei 3종·Xiaomi S-OLED/A-Pro)만 `estimated_fields`에 `size_variants_in` 표기.
- [x] **삼성 2026 모델코드 정정(2026-07-25)** — QN990G→**QN990H**(85·98), S95G→**S95H**, QN90G→**QN80H**(QN90 라인 2026 단종 → 4K Neo QLED 최상위 QN80H). 골든셋·SKU·사이즈·비교맵 정합.
- [x] **2026 삼성 라인업 보강** — S99H(프리미엄 QD-OLED)·S90H·S85H(WOLED)·QN70H(Neo QLED 4K) 추가 → 2026 삼성 7종, 전체 **62종**.
- [x] **2026 중가·엔트리 확장** — 삼성 Crystal UHD **U8000H**(entry)·**The Frame LS03H**(mid) / TCL **QM7L**(3000nit)·**QM6L** / Hisense **U7SG**(2026 U7) / LG **QNED85B**.
- [x] **보완가이드(xlsx) 대조 반영(2026-07-27)** — 우선순위(Micro RGB·플래그십) 누락 11종 추가: 삼성 **QN900F**(8K)·**S85F**(OLED)·**MR95F**(Micro RGB 115″), TCL **X11K/X11L**(RGB 6500nit), Hisense **UR9/UR8**(2026 RGB), LG **QNED82A/70A**, Sony **XR80**(Bravia 8 2024)·**S30**(Bravia 3 2024). §4 모델명 별칭(U8QG·XR80M2·S5F 등) `model_alias`에 등재. → 전체 **115종**.
- [x] **amazon.com 대조 누락 점검(2026-07-26)** — 삼성 **The Frame Pro LS03HW**(2026)·LG **QNED84B/QNED73B**(2026 Mini-LED)·LG **QNED92A**(2025 FALD 플래그십) 추가. Sony Bravia 3 II 코드 **S30II→XR30M2**(Amazon SKU K-xxXR30M2 확인) 정정. → 전체 **105종**.
- [x] **공식 사이트 재확인 반영(2026-07-26)** — 불명확했던 2026 모델을 각 브랜드 도메인(samsung.com·lg.com·hisense-usa.com)에서 재검증: 삼성 **Mini LED M70H·M80H**(2026 신 Mini-LED 라인, 실재 확인)·Hisense **U6SF**(2026 U6 엔트리)·LG **QNED80B** 추가, LG **QNED85B** 사이즈·SKU(65QNED85UQA) 정정. (삼성 Q7H/Q8H·LG 2026 UHD는 공식 미확인 → 미등록) → 전체 **100종**.
- [x] **2026 released 스펙 완성(2026-07-26)**(`scripts/load_2026_specs.py`) — 발표시점 seed(announced)로 비어있던 삼성/LG 2026 OLED·Neo QLED 10종의 주사율·프로세서·밝기·게이밍·연결을 CES2026 이후 확정 실사양으로 채움(QN990H NQ8 Gen3·8K120/4K240·5×HDMI2.1, S99H 165Hz·48/83″WOLED, G6/C6 α11, B6 α8 Gen3 835nit). **2026 17종 스펙 100% 완비.**
- [x] **인치별 variant 확장 + 가격**(`scripts/expand_variants.py`) — size_variants_in 기준 인치별 variant 생성(82→**267행**). 실제 판매 SKU 미상이라 **구성 SKU `{code}-{size}IN-{region}`**(estimated_fields에 `sku_full` 표기), 물리스펙은 사이즈별 보강. 공식 확인된 **US 인치별 MSRP**(QN90F·QM6K·QM7K, 18건) price_history 적재.
- [x] **브랜드 마케팅 feature(우선순위+카테고리)**(`model_feature` 테이블, `scripts/load_features.py`) — 스펙 외 브랜드가 앞세우는 기능을 **제품페이지 노출 순서(rank1=최상단)**로, **category(picture/performance/gaming/sound/ai/design/service/experience)** 별로 적재. 특히 **service**(Gaming Hub·TV Plus·SmartThings·LG Channels·Bravia Core·Google TV·음성비서)와 **experience**(Ambient·Art·Multi View·Always Ready·Bravia Cam·SolarCell 리모컨·FlexConnect)를 브랜드별로 반영. **전 105모델 1164 feature**(experience 365·service 336) — 6종은 공식 페이지 순서(CURATED), 나머지는 브랜드 생태계+패널 아키타입 기반 생성(source=brand-generic). API `GET /api/features?model=`(rank순·category 포함).
- [x] **지역별 모델명 매핑**(`model_alias` 테이블, `scripts/build_aliases.py`) — Base_Model→Region_Model_Name. 실SKU(KR/US) + EPREL(EU) 자동 등재(105건). API `GET /api/aliases?model=`. 지역별 접미사 차이 통합의 기반.
- [x] **사이즈별 세부 스펙 override**(`variant.panel_override`·`refresh_override`) — 같은 시리즈라도 사이즈마다 패널/주사율이 다른 경우(예: 삼성 S90 77/83″=WOLED, The Frame/Q8F 소형=60Hz)를 사이즈 단위로 기록. `scripts/load_size_overrides.py`.
- [x] **OS 필터**(API `GET /api/by_os?os=`) — Tizen/webOS/Google-TV/VIDAA/Fire-TV/HarmonyOS + 버전(smart_os_version)으로 필터·비교.
- [x] **인증/에너지(EPREL)**(`certification` 테이블, `scripts/load_certification.py`) — EU 에너지효율 등록DB 기반 에너지등급(SDR/HDR)·소비전력(W)·**EU 정식 모델명(파생 SKU 매핑)**. 6종(S90F·S95F·G5·XR80II·U8Q·QN90D). API `GET /api/certification?model=`. ※FCC·RRA(한국)는 직접조회 제약으로 컬럼만 준비.
- [x] **엔트리 모델 스펙 정밀 보강** — Q6F·Q7F·U8000F·UA77·QNED80A·QD6QF·S5·BRAVIA 2 II의 로컬디밍(Q7F edge-lit)·HDR 포맷(HDR10 보강)·HDMI 포트수(4포트 정정)·VRR 유무(BRAVIA 2 II VRR 제거)·프로세서를 공식/RTINGS 사양으로 정정.
- [x] **온라인몰 실판매가**(`scripts/load_retail_prices.py`) — WebSearch(2026-07) 확인가로 멀티채널 price_history 적재: **bestbuy·walmart·amazon**(+official-msrp). LG C5/G5·Sony 8 II·TCL QM8K·Hisense U8 등.
- [x] **국내가(KR)**(`scripts/load_kr_prices.py`) — 한국어 검색으로 **다나와·SSG** 국내 실판매가 적재(KRW): LG G5 65″ 257만·삼성 S95F 65″ 396만 등. 채널: danawa·ssg.
- [x] **실측 성능(RTINGS 등)**(`measurement` 테이블, `scripts/load_measurements.py`) — HDR 실측 피크·입력랙·DCI-P3·rec2020·명암비. **37종**(2024~2026 플래그십~엔트리, 브랜드별 삼성12·LG9·Sony6·Hisense5·TCL5), 출처(source) 표기. API `GET /api/measurements?model=`(밝기순 랭킹). ※Huawei·Xiaomi는 전문 실측 리뷰 부재로 미수집. DisplaySpecifications 봇차단·TechSpecs API 키필요로 미연동(tuner/vesa_mm 컬럼만 준비).
- [x] **누락 모델 추가(2025)** — TCL QM9K·삼성 QN800F(8K)·Sony BRAVIA 2 II·삼성 Q7F/Q8F(QLED)·삼성 The Frame LS03F·삼성 QN80F·Hisense UX(RGB 6000nit)·LG QNED85A/QNED90A → 전체 **72종**. Hisense U8Q 오디오 4.1.2ch 실측.
- [x] **2024 라인업 인치 세분화** — QN90D·S95D·G4·C4·A95L·X90L·QM851G·U8N 등 2024 주요 모델에 size_variants_in 추가(공식/RTINGS). 연도 커버리지: 2026·2025 전량, 2024 17/20.
- [x] **추가 플래그십/누락 모델(2024~2026)** — LG M5(무선 OLED)·삼성 QN95F(EU)·The Frame Pro·Hisense U9N·TCL QM8L·U6N + **삼성 QN70F**·**Sony BRAVIA 9 II/7 II(True RGB Mini-LED, 4250nit)**·**LG QNED92(2026)**·**삼성 Micro RGB R95H/R85H(2026 신기술)** → 전체 **90종**(신규 차세대 RGB-LED 계열 포함).
- [x] **엔트리·미드 UHD 확장** — 삼성 Q6F(QLED)·Crystal UHD U8000F · LG UA77(UHD)·QNED80A · Hisense QD6QF(Fire TV) · TCL S5(4K LED)·Sony BRAVIA 3 II 추가 → 전체 **79종**, entry 다수 포함.
- [x] **Huawei/Xiaomi 실모델 정비** — VisionSE→실제 Vision Smart Screen 5 SE(Mini-LED 240Hz, 55/65/75 확인), VisionX→V5 Pro, S-OLED→S Pro OLED 로 명칭·패널 정정. variant **450행**.
- [ ] **골든셋 스펙값 공식 대조 검수** (현재 대표값 — 정답지 확정 필요)
- [ ] 실사이트 셀렉터 확정 + JS 사이트는 Playwright 연동(위 가이드)
- [x] 가격 수집 스케줄링(launchd 매일) — `collect_prices.py` + `deploy/*.plist`, 예외격리
- [ ] 임베딩 대상 확대(model 스펙·리뷰까지) + Voyage 등 고품질 임베더 교체 검토

## 준수사항
- 크롤링 전 robots.txt/이용약관 확인, 가능하면 공식 API/제휴 우선
- 리뷰 원문 복제 금지(사실 데이터만), 가격은 `captured_at` 타임스탬프 필수
