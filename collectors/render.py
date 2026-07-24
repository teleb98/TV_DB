"""
렌더링 Fetcher (Phase 1) — JS/안티봇 사이트를 헤드리스 크롬으로 렌더 후 HTML 반환.
정적 httpx로 0건인 사이트(다나와·쿠팡·Best Buy 등)를 위해, 렌더된 DOM을
기존 수집기의 parse() 에 그대로 넘긴다. Playwright 미설치 시 명확히 실패.

의존성:  pip install playwright && playwright install chromium
"""
from __future__ import annotations


def render_html(url: str, ua: str = "tv-spec-db/0.1",
                wait: str = "networkidle", timeout: int = 20000,
                settle_ms: int = 800) -> str:
    """헤드리스 크롬으로 url 을 렌더하고 최종 HTML(문자열) 반환.
    wait: 'load' | 'domcontentloaded' | 'networkidle'. settle_ms: 렌더 후 추가 대기(지연 로딩)."""
    from playwright.sync_api import sync_playwright   # 지연 임포트(미설치 환경 보호)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(user_agent=ua)
            page.goto(url, wait_until=wait, timeout=timeout)
            if settle_ms:
                page.wait_for_timeout(settle_ms)      # 지연 로딩 콘텐츠 대기
            return page.content()
        finally:
            browser.close()
