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
collectors/base.py             수집기 공통 뼈대 (fetch→parse→RawRecord)
collectors/samsung_official.py 삼성 공식 (정확도 우선)   [셀렉터 미정]
collectors/danawa.py           다나와 (커버리지·가격 우선) [셀렉터 미정]
collectors/spec_pdf.py         스펙시트 PDF→Claude 구조화  [STUB]
normalize/normalizer.py        모델명·마케팅명·단위 정규화 (성패 핵심) ✅검증
db.py                          4계층 upsert (psycopg, ON CONFLICT) ✅
pipeline.py                    수집→정규화→적재 + 골든 로더 ✅
scripts/build_comparison_map.py 삼성↔경쟁사 동급 매핑 생성기 ✅
agent/query.py                 상담봇 질의 함수 (compare/lineup/search) ✅
agent/demo.py                  질의 데모 러너
tools/inspect_page.py          실제 페이지→후보 셀렉터 추출 헬퍼
data/golden/golden_models.csv  검증용 골든셋 (29개 모델)
```

## 빠른 시작 (검증된 절차)
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
createdb tvspec && psql tvspec -f schema/schema.sql            # 스키마(7 테이블)
export PG_DSN="postgresql://localhost/tvspec"
.venv/bin/python pipeline.py --load-golden data/golden/golden_models.csv  # 골든셋 적재
.venv/bin/python scripts/build_comparison_map.py              # 비교축 생성
.venv/bin/python -m agent.demo                                # 상담봇 질의 데모
```

## 완료 / 남은 일
- [x] 4계층 스키마 · 정규화 엔진(골든셋 29/29 통과) · DB upsert(멱등)
- [x] Comparison_Map 생성기 · Agent 질의계층(compare/lineup/search)
- [ ] **골든셋 스펙값 공식 대조 검수** (현재 대표값 — 정답지 확정 필요)
- [ ] 수집기 셀렉터 확정(`config/selectors.py`) — `tools/inspect_page.py` 활용
- [ ] `series.positioning` 채우고 라인업 안내에 RAG 얹기
- [ ] 가격 수집 스케줄링(주간) → `price_history` 축적

## 준수사항
- 크롤링 전 robots.txt/이용약관 확인, 가능하면 공식 API/제휴 우선
- 리뷰 원문 복제 금지(사실 데이터만), 가격은 `captured_at` 타임스탬프 필수
