# CLAUDE.md — 프로젝트 오리엔테이션

Claude Code 가 이 저장소에서 작업할 때 참고하는 안내. (사람은 README.md / INSTALL.md 참고)

## 무엇인가
삼성 vs 경쟁사(LG/Sony/TCL/Hisense) TV 제품정보 상담봇을 위한 **PostgreSQL 4계층 DB + 수집·정규화 파이프라인 + 시맨틱 검색계층**.

## 최초 설치
```bash
bash scripts/setup.sh        # venv~데이터~RAG 자동. --reset 로 초기화
export PG_DSN="postgresql://localhost/tvspec"
./.venv/bin/python -m agent.demo
```
Python 은 항상 프로젝트 `.venv` 사용. 스크립트는 절대경로 또는 프로젝트 루트에서 실행.

## 아키텍처 (데이터 흐름)
```
수집기(collectors/) → 정규화(normalize/) → 적재(db.py, pipeline.py) → PostgreSQL
                                                                         ↑
           비교축(scripts/build_comparison_map) · 임베딩(scripts/build_embeddings) 
                                                                         ↓
                                          상담봇 질의(agent/query.py)
```
- **4계층**: Brand → Series(라인업) → Model(스펙) → Variant(옵션). + Comparison_Map, price_history, series_embedding.
- **정규화 핵심**: `normalize/normalizer.py` 의 `MODEL_RULES` — 브랜드별 SKU→base코드. 새 연도/모델 추가 시 여기 규칙 확인.
- **골든셋**: `data/golden/*.csv` 가 검증 정답지 겸 시드. 값은 **대표값**이라 공식 대조 검수 전제.

## 자주 쓰는 명령
```bash
# 데이터 재적재(멱등)
./.venv/bin/python pipeline.py --load-golden data/golden/golden_models.csv
# 정규화 회귀 확인
./.venv/bin/python -c "import csv;from normalize.normalizer import base_model_code as b;\
[print(r['brand'],r['sku_full'],'->',b(r['sku_full'],r['brand'])) for r in csv.DictReader(open('data/golden/golden_models.csv'))]"
# 상담봇 질의
./.venv/bin/python -m agent.demo
# 수집기 통합테스트(픽스처)
./.venv/bin/python -m tests.test_samsung_fixture
```

## 규칙 / 주의
- **생성기 성격 파일 수정 시 검증 필수**: 스키마·정규화·적재 변경 후 골든셋으로 회귀 확인.
- 데이터 변경(모델/가격/설명) → 해당 로더 재실행. 임베딩 대상(positioning) 바뀌면 `build_embeddings.py` 재실행.
- 실사이트 수집기(samsung_official/danawa)는 **셀렉터 미확정**(config/selectors.py). JS 렌더링 사이트는 정적 파싱 실패 가능 → Playwright 필요.
- 2026 모델은 `status='announced'/data_confidence='low'`(잠정). 공식 확정 시 승격.
- 커밋은 사용자가 요청할 때만.
