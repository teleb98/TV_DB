"""
크롤 프론티어 (Phase 2) — 대상 큐 관리 + 원본 해시 변경감지.
- seed(): 시드 URL을 crawl_queue 에 등록(멱등)
- due(): 크롤 예정(next_due 도래) 대상 반환, 우선순위순
- record_crawl(): 원본 저장 + 해시 비교 → 변경 여부 반환 + 큐 스케줄 갱신
변경 없으면(해시 동일) 파서가 파싱을 스킵해 비용을 아낀다.
"""
from __future__ import annotations
import hashlib
import pathlib
from datetime import datetime, timezone, timedelta

RAW_DIR = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def seed(cur, url: str, source: str, priority: int = 5):
    """시드 URL 등록(이미 있으면 우선순위만 갱신)."""
    cur.execute("""
        insert into crawl_queue(url, source, priority)
        values (%s,%s,%s)
        on conflict (url, source) do update set priority = excluded.priority
    """, (url, source, priority))


def due(cur, limit: int = 50) -> list[dict]:
    """크롤 예정 대상(next_due<=now), 우선순위·마감 순."""
    cur.execute("""
        select id, url, source, priority, content_hash, fail_count
        from crawl_queue
        where status <> 'failed' and next_due <= now()
        order by priority, next_due
        limit %s
    """, (limit,))
    cols = [d.name for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def record_crawl(cur, url: str, source: str, html: str,
                 interval_hours: int = 24) -> bool:
    """원본 저장 + 해시 비교. 변경됐으면 True.
    큐의 content_hash/last_crawled/next_due 갱신. 원본 파일은 data/raw/ 에 보존."""
    h = _hash(html)
    cur.execute("select content_hash from crawl_queue where url=%s and source=%s", (url, source))
    row = cur.fetchone()
    prev = row[0] if row else None
    changed = (h != prev)

    if changed:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() else "_" for c in url)[-80:]
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = RAW_DIR / f"{source}_{safe}_{stamp}.raw"
        path.write_text(html, encoding="utf-8")
        cur.execute("""insert into crawl_raw(url, source, content_hash, path)
                       values (%s,%s,%s,%s)""", (url, source, h, str(path)))

    nxt = datetime.now(timezone.utc) + timedelta(hours=interval_hours)
    cur.execute("""
        update crawl_queue
        set content_hash=%s, last_crawled=now(), next_due=%s,
            status='done', fail_count=0
        where url=%s and source=%s
    """, (h, nxt, url, source))
    return changed


def mark_failed(cur, url: str, source: str, backoff_hours: int = 6):
    """실패 기록 + 백오프. fail_count 5회 초과 시 status=failed."""
    nxt = datetime.now(timezone.utc) + timedelta(hours=backoff_hours)
    cur.execute("""
        update crawl_queue
        set fail_count = fail_count + 1, next_due = %s,
            status = case when fail_count + 1 >= 5 then 'failed' else status end
        where url=%s and source=%s
    """, (nxt, url, source))
