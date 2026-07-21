# 설치 가이드 — TV Spec DB

삼성 vs 경쟁사 TV 제품정보 Agent용 DB. 이 문서 하나로 설치·실행이 끝납니다.

## 1. 사전 요구사항

| 항목 | 버전 | 비고 |
|---|---|---|
| Python | 3.10+ | `python3 --version` |
| PostgreSQL | 14~18 | 실행 중이어야 함 (`pg_isready`) |
| pgvector | 0.5+ | **선택** — 시맨틱 RAG용. 없으면 recommend()가 키워드 폴백 |
| (macOS) Homebrew | - | PostgreSQL/pgvector 설치에 사용 |

PostgreSQL 이 없다면:
```bash
# macOS
brew install postgresql@16 && brew services start postgresql@16
# Ubuntu/Debian
sudo apt install postgresql && sudo service postgresql start
```

## 2. 원클릭 설치

압축을 풀고 프로젝트 루트에서:
```bash
bash scripts/setup.sh
```
이 스크립트가 자동으로: venv 생성 → 의존성 설치 → DB/스키마 생성 → 데이터 적재
(2023~2026 46+6모델, 라인업 설명, 비교축, 가격) → pgvector 있으면 임베딩까지.

처음부터 재구성(기존 DB 삭제):
```bash
bash scripts/setup.sh --reset
```

DB 접속 정보 변경:
```bash
PG_DSN="postgresql://user@host:5432/tvspec" bash scripts/setup.sh
```

## 3. 실행 확인

```bash
PG_DSN="postgresql://localhost/tvspec" ./.venv/bin/python -m agent.demo
```
상담봇 질의 7종(스펙비교/라인업/조건검색/추천/최저가/가격추세/신제품)이 출력되면 정상.

## 4. pgvector 설치 (시맨틱 RAG, 선택)

recommend()를 키워드→의미 기반으로 승격하려면 pgvector 가 필요합니다.
```bash
brew install pgvector                 # macOS
# 또는 apt: sudo apt install postgresql-16-pgvector
psql tvspec -c "CREATE EXTENSION vector;"
./.venv/bin/python scripts/build_embeddings.py
```

**⚠ pgvector 가 실행 중 PostgreSQL 버전과 안 맞을 때**(예: brew가 pg17/18용만 설치, 서버는 pg16):
소스에서 해당 버전으로 빌드합니다.
```bash
git clone --depth 1 --branch v0.8.5 https://github.com/pgvector/pgvector.git
cd pgvector
make        PG_CONFIG=/opt/homebrew/opt/postgresql@16/bin/pg_config
make install PG_CONFIG=/opt/homebrew/opt/postgresql@16/bin/pg_config
psql tvspec -c "CREATE EXTENSION vector;"
```

## 5. 가격 수집 스케줄링 (선택, macOS)

```bash
cp deploy/com.tvspecdb.prices.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.tvspecdb.prices.plist   # 매일 03:00
launchctl start com.tvspecdb.prices                               # 즉시 1회
```

## 6. 트러블슈팅

| 증상 | 원인/해결 |
|---|---|
| `psql: command not found` | PostgreSQL 미설치 또는 PATH 누락. `brew install postgresql@16` |
| `extension "vector" is not available` | pgvector 미설치/버전불일치 → 4번 소스빌드 |
| `ModuleNotFoundError: model2vec` | `./.venv/bin/pip install -r requirements.txt` 재실행 |
| 임베딩 다운로드 실패(오프라인) | 자동으로 해시 임베더 폴백 — 동작엔 지장 없음(품질만 하향) |
| `role/DB does not exist` | `PG_DSN` 의 계정/DB 확인, `createdb tvspec` |
| 스펙값이 부정확 | 골든셋은 **대표값** — 공식 스펙시트 대조 검수 필요(정답지 확정) |

## 7. 데이터 갱신 / 확장

- **새 모델 추가**: `data/golden/golden_models.csv` 에 행 추가 → `pipeline.py --load-golden ...` 재실행(멱등)
- **가격 갱신**: `data/golden/prices_kr.csv` 또는 실수집 → `scripts/load_prices.py`
- **라인업 설명**: `data/golden/series_positioning.csv` → `scripts/load_positioning.py` → `scripts/build_embeddings.py`
- 자세한 아키텍처/명령은 **README.md** 참고.
