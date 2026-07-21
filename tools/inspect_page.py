"""
셀렉터 채우기 보조 도구.
실제 페이지를 받아 '스펙/가격/모델명'일 가능성이 높은 노드의 후보 CSS 셀렉터를 출력.
config/selectors.py 를 손으로 채우기 전에 후보를 좁히는 용도.

사용:
    python tools/inspect_page.py "https://www.samsung.com/sec/tvs/..."
    python tools/inspect_page.py page.html          # 로컬 HTML도 가능
"""
from __future__ import annotations
import sys
import re
import pathlib
import httpx
from selectolax.parser import HTMLParser

# 관심 키워드(스펙/가격 관련 텍스트가 든 노드를 후보로)
KEYWORDS = ["Hz", "㎐", "인치", "4K", "8K", "QLED", "OLED", "HDR",
            "원", "최저가", "모델명", "해상도", "명암", "프로세서"]


def node_selector(node) -> str:
    """노드의 대략적 CSS 셀렉터(tag + class) 생성."""
    tag = node.tag
    cls = node.attributes.get("class") or ""
    cls = ".".join(c for c in cls.split() if c)[:60]
    return f"{tag}.{cls}" if cls else tag


def main(src: str) -> None:
    if src.startswith("http"):
        html = httpx.get(src, timeout=20, headers={"User-Agent": "tv-spec-db/0.1"}).text
    else:
        html = pathlib.Path(src).read_text(encoding="utf-8")

    tree = HTMLParser(html)
    seen: dict[str, list[str]] = {}
    for node in tree.css("*"):
        text = (node.text(deep=False) or "").strip()
        if not text or len(text) > 60:
            continue
        if any(k in text for k in KEYWORDS):
            sel = node_selector(node)
            seen.setdefault(sel, [])
            if len(seen[sel]) < 3 and text not in seen[sel]:
                seen[sel].append(text)

    print(f"# 후보 셀렉터 {len(seen)}개 (텍스트 샘플 포함) — config/selectors.py 채우기 참고\n")
    for sel, samples in sorted(seen.items(), key=lambda x: -len(x[1])):
        print(f"{sel}")
        for s in samples:
            print(f"    ↳ {s}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: python tools/inspect_page.py <url|file.html>")
    main(sys.argv[1])
