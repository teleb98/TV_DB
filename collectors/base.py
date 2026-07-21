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


def fetch_html(target: str, ua: str = "tv-spec-db/0.1", timeout: int = 20) -> str:
    """target 이 http(s)면 HTTP GET, 아니면 로컬 파일로 읽음(픽스처 테스트용).
    ⚠ 실사이트가 JS 렌더링/안티봇이면 정적 GET 실패 가능 → 헤드리스(Playwright) 필요."""
    if target.startswith(("http://", "https://")):
        import httpx
        r = httpx.get(target, timeout=timeout, headers={"User-Agent": ua})
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
        out: list[RawRecord] = []
        for t in targets:
            raw = self.fetch(t)
            self._dump_raw(t, raw)                 # 원본 보존(재파싱/감사용)
            out.extend(self.parse(raw, source_url=t))
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
