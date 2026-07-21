#!/usr/bin/env bash
# =====================================================================
# TV Spec DB — 원클릭 부트스트랩
#   venv 생성 → 의존성 설치 → DB/스키마 → 데이터 적재 → pgvector/임베딩(RAG)
# 사용:
#   bash scripts/setup.sh            # 설치/갱신(멱등)
#   bash scripts/setup.sh --reset    # DB를 지우고 처음부터 재구성
# 환경변수:
#   PG_DSN (기본 postgresql://localhost/tvspec)
# =====================================================================
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"

PG_DSN="${PG_DSN:-postgresql://localhost/tvspec}"
DB_NAME="${PG_DSN##*/}"
PY="${PYTHON:-python3}"
RESET=0
[ "${1:-}" = "--reset" ] && RESET=1
export PG_DSN

echo "==> 프로젝트: $HERE"
echo "==> DB: $DB_NAME  (PG_DSN=$PG_DSN)"

# --- 사전 점검 ---
command -v "$PY"  >/dev/null || { echo "!! python3 없음"; exit 1; }
command -v psql   >/dev/null || { echo "!! PostgreSQL(psql) 없음 — INSTALL.md 참고"; exit 1; }
command -v createdb >/dev/null || { echo "!! createdb 없음"; exit 1; }

echo "==> 1) Python venv + 의존성"
[ -d .venv ] || "$PY" -m venv .venv
./.venv/bin/pip install -q --upgrade pip
./.venv/bin/pip install -q -r requirements.txt

echo "==> 2) DB 준비"
if [ "$RESET" = 1 ]; then
  echo "   --reset: $DB_NAME 삭제 후 재생성"
  dropdb --if-exists "$DB_NAME"
fi
createdb "$DB_NAME" 2>/dev/null && echo "   생성됨" || echo "   이미 존재"

echo "==> 3) 스키마"
if psql "$DB_NAME" -tAc "select 1 from information_schema.tables where table_name='series'" | grep -q 1; then
  echo "   스키마 이미 적용됨(스킵)"
else
  psql "$DB_NAME" -q -f schema/schema.sql && echo "   적용 완료"
fi

echo "==> 4) 데이터 적재(멱등)"
./.venv/bin/python pipeline.py --load-golden data/golden/golden_models.csv
./.venv/bin/python pipeline.py --load-golden data/golden/golden_models_2026.csv
./.venv/bin/python pipeline.py --load-golden data/golden/golden_models_us.csv   # US(USD) variant
./.venv/bin/python scripts/load_positioning.py data/golden/series_positioning.csv
./.venv/bin/python scripts/build_comparison_map.py
./.venv/bin/python scripts/load_prices.py data/golden/prices_kr.csv

echo "==> 5) pgvector + 임베딩(시맨틱 RAG)"
if psql "$DB_NAME" -tAc "select 1 from pg_available_extensions where name='vector'" | grep -q 1; then
  psql "$DB_NAME" -q -c "CREATE EXTENSION IF NOT EXISTS vector;"
  if ./.venv/bin/python scripts/build_embeddings.py; then
    echo "   RAG 활성화 완료"
  else
    echo "   !! 임베딩 실패 — recommend()는 키워드 폴백으로 동작"
  fi
else
  echo "   pgvector 미설치 → RAG 스킵(recommend()는 키워드 폴백)."
  echo "   활성화하려면 INSTALL.md의 'pgvector 설치' 참고."
fi

echo ""
echo "==> 완료 ✅   데모 실행:"
echo "    PG_DSN=$PG_DSN ./.venv/bin/python -m agent.demo"
