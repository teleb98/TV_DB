"""
수집기 공통 뼈대.
모든 소스별 수집기는 BaseCollector를 상속한다.
흐름:  fetch(원본 수집) → parse(구조화) → RawRecord 리스트 반환
정규화/적재는 상위 파이프라인(pipeline.py)이 담당 → 수집기는 '수집+파싱'만 책임.
"""
from __future__ import annotations
import abc
import json
import time
import pathlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

RAW_DIR = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"

# JS 렌더링/안티봇으로 정적 GET이 안 되는 호스트 → 헤드리스 렌더 사용(Phase 1).
RENDER_HOSTS = {
    "prod.danawa.com", "www.danawa.com", "search.danawa.com",
    "www.coupang.com", "www.bestbuy.com",
}


def _host(url: str) -> str:
    from urllib.parse import urlparse
    return (urlparse(url).hostname or "").lower()


def fetch_html(target: str, ua: str = "tv-spec-db/0.1", timeout: int = 20,
               force_render: bool = False) -> str:
    """target 이 http(s)면 HTTP GET(또는 RENDER_HOSTS면 헤드리스 렌더), 아니면 로컬 파일.
    force_render=True 면 도메인 무관 렌더. Playwright 미설치면 렌더 경로에서 예외."""
    if target.startswith(("http://", "https://")):
        if force_render or _host(target) in RENDER_HOSTS:
            from .render import render_html
            return render_html(target, ua=ua, timeout=timeout * 1000)
        import httpx
        r = httpx.get(target, timeout=timeout, headers={"User-Agent": ua},
                      follow_redirects=True)   # 카테고리 URL 등 3xx 추종
        r.raise_for_status()
        return r.text
    return pathlib.Path(target).read_text(encoding="utf-8")


@dataclass
class RawRecord:
    """수집기가 뱉는 표준 중간 포맷 (아직 정규화 전)."""
    source: str                       # 'samsung_official','danawa',...
    layer: str                        # 'series' | 'model' | 'variant' | 'price'
    payload: dict                     # 소스 원본 필드 그대로
    source_url: str = ""
    captured_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class BaseCollector(abc.ABC):
    source_name: str = "base"
    # 예의: 크롤링 간 최소 지연(초). robots/약관 준수.
    rate_limit_sec: float = 1.5

    def __init__(self, region: str = "KR"):
        self.region = region

    # --- 하위 클래스가 구현 ---
    @abc.abstractmethod
    def fetch(self, target: str) -> str:
        """target(URL/모델코드/PDF경로) → 원본 문자열(HTML/JSON/텍스트) 반환."""

    @abc.abstractmethod
    def parse(self, raw: str, source_url: str = "") -> list[RawRecord]:
        """원본 → RawRecord 리스트."""

    # --- 공통 유틸 ---
    def collect(self, targets: list[str]) -> list[RawRecord]:
        """타깃별 예외를 격리 — 하나가 실패해도 나머지는 계속(스케줄 작업 견고성)."""
        out: list[RawRecord] = []
        for t in targets:
            try:
                raw = self.fetch(t)
                self._dump_raw(t, raw)             # 원본 보존(재파싱/감사용)
                out.extend(self.parse(raw, source_url=t))
            except Exception as e:
                print(f"[warn] collect skip {t}: {type(e).__name__}: {e}")
            time.sleep(self.rate_limit_sec)
        return out

    def _dump_raw(self, target: str, raw: str) -> None:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() else "_" for c in target)[-80:]
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        (RAW_DIR / f"{self.source_name}_{safe}_{stamp}.raw").write_text(raw, encoding="utf-8")

    @staticmethod
    def save_records(records: list[RawRecord], path: str) -> None:
        pathlib.Path(path).write_text(
            json.dumps([asdict(r) for r in records], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
