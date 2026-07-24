# TV Spec DB — 삼성 vs 경쟁사 TV 제품정보 Agent용 DB

스펙 비교 상담봇 + 라인업 안내 Agent를 위한 제품정보 DB 구축 프로젝트.

- **대상**: 삼성 / LG / Sony / TCL / Hisense · 국내(KR)→북미(US) · 최근 3년
- **핵심**: 옵션(Variant) 단위까지 모델링 + 삼성↔경쟁사 비교축

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

## 완료 / 남은 일
- [x] 4계층 스키마 · 정규화 엔진(골든셋 46/46 통과, 2023~2025) · DB upsert(멱등)
- [x] Comparison_Map 생성기 · Agent 질의계층(compare/lineup/search/recommend)
- [x] `series.positioning` 시드 + 라인업 추천 **pgvector 시맨틱 RAG**(model2vec, 키워드 폴백)
- [x] 수집기 파싱 경로 픽스처 검증(fetch→parse→normalize→DB)
- [x] 가격 스냅샷 파이프라인(`price_history` 축적, 추세/최저가 질의, 재적재 멱등)
- [x] 멀티리전(KR 52·US 20 variant, 2023~2025) — 지역별 SKU·통화·가격이력 + `price_by_region()`
- [x] 지역별 OS 차이 모델링 — `variant.os_override`(예: Hisense US=Google-TV vs KR=VIDAA)
- [x] tool-use 에이전트 — 8개 질의도구를 Claude(claude-opus-4-8)에 노출, 자연어 상담(도구계층 검증 완료; 라이브는 `ANTHROPIC_API_KEY` 필요)
- [x] 수명주기 `status`(announced/released/eol) + `data_confidence` — 2026 잠정 데이터 격리
- [ ] **2026 스펙/SKU 공식 확정 시 released/high 승격** (현재 삼성·LG 6종 announced/low, Sony/TCL/Hisense 보류)
- [ ] **골든셋 스펙값 공식 대조 검수** (현재 대표값 — 정답지 확정 필요)
- [ ] 실사이트 셀렉터 확정 + JS 사이트는 Playwright 연동(위 가이드)
- [x] 가격 수집 스케줄링(launchd 매일) — `collect_prices.py` + `deploy/*.plist`, 예외격리
- [ ] 임베딩 대상 확대(model 스펙·리뷰까지) + Voyage 등 고품질 임베더 교체 검토

## 준수사항
- 크롤링 전 robots.txt/이용약관 확인, 가능하면 공식 API/제휴 우선
- 리뷰 원문 복제 금지(사실 데이터만), 가격은 `captured_at` 타임스탬프 필수
