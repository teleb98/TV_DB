"""
라인업 positioning 임베딩 생성 → pgvector 적재.
series_embedding(series_id, vec vector(dim)) 테이블을 임베더 차원에 맞춰 생성/적재.
텍스트 = marketing_name + positioning (라인업 의미 표현).

실행:  PG_DSN=... .venv/bin/python scripts/build_embeddings.py
"""
from __future__ import annotations
import os
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import psycopg
from embed.embedder import get_embedder

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")


def build():
    emb = get_embedder()
    print(f"[embed] embedder={emb.name} dim={emb.dim}")
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")   # 자체 완결
        # 차원에 맞춰 테이블 (재실행 시 차원 바뀌면 재생성)
        cur.execute("DROP TABLE IF EXISTS series_embedding")
        cur.execute(f"""
            CREATE TABLE series_embedding (
                series_id INT PRIMARY KEY REFERENCES series(series_id) ON DELETE CASCADE,
                vec       vector({emb.dim}) NOT NULL,
                model     TEXT,
                built_at  TIMESTAMPTZ DEFAULT now()
            )
        """)

        cur.execute("""
            select series_id, coalesce(marketing_name,'')||' '||coalesce(positioning,'')
            from series where positioning is not null
        """)
        rows = cur.fetchall()
        ids = [r[0] for r in rows]
        texts = [r[1] for r in rows]
        vecs = emb.encode(texts)

        for sid, v in zip(ids, vecs):
            vec_str = "[" + ",".join(f"{x:.6f}" for x in v) + "]"
            cur.execute(
                "insert into series_embedding(series_id, vec, model) values (%s, %s::vector, %s)",
                (sid, vec_str, emb.name))

        # 코사인 검색용 HNSW 인덱스(소량이라 성능보단 관례적 구성)
        cur.execute("CREATE INDEX ON series_embedding USING hnsw (vec vector_cosine_ops)")
        conn.commit()
        print(f"[embed] {len(ids)}개 series 임베딩 적재 완료")


if __name__ == "__main__":
    build()
