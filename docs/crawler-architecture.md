# DB 웹크롤러 — 단계별 구축 계획

기존 파이프라인(`collectors/base.py` fetch→parse→RawRecord → normalize → 4계층 upsert)
위에 **Fetcher 3-티어 + 원본해시 변경감지 + LLM 폴백 파서**를 얹는다.
하부(정규화·적재·스케줄러·예외격리)는 이미 구축돼 있어 각 단계는 독립적으로 가치 산출.

```
[Scheduler] → [Frontier/Queue] → [Fetcher(API/정적/렌더)] → [Raw Store+해시]
   → [Parser(셀렉터→LLM폴백)] → [Normalizer] → [Loader upsert] → [Change Detector]
```

각 단계: 목표 · 산출물 · 핵심코드 · 연결점 · 검증기준 · 난이도.

---

## Phase 0 — 준비 (0.5일)
- **목표**: 크롤러 의존성·디렉토리 확보
- **산출물**: `requirements`에 `playwright` 추가, `data/raw/`(존재), `crawler/` 패키지
- **작업**: `pip install playwright && playwright install chromium`
- **검증**: `playwright --version`, chromium 실행 확인
- **난이도**: 낮음 (브라우저 ~150MB 다운로드)

## Phase 1 — 렌더링 Fetcher (Playwright)  ★즉효  ✅완료
> 구현됨: `collectors/render.py` + `base.fetch_html` RENDER_HOSTS 분기.
> 검증: 다나와 정적 268KB → 렌더 448KB(+67%, 가격 '원' 206건). 셀렉터 확정은 후속.

- **목표**: JS/안티봇 사이트(다나와·쿠팡·Best Buy)를 헤드리스로 렌더 후 기존 `parse()` 재사용
- **산출물**: `collectors/render.py`(`render_html(url)`), `base.fetch_html` 도메인 분기
- **핵심코드**:
  ```python
  # collectors/render.py
  def render_html(url, wait="networkidle", timeout=20000):
      from playwright.sync_api import sync_playwright
      with sync_playwright() as p:
          b = p.chromium.launch(headless=True)
          pg = b.new_page(user_agent="tv-spec-db/0.1")
          pg.goto(url, wait_until=wait, timeout=timeout)
          html = pg.content(); b.close(); return html
  # base.py: RENDER_HOSTS = {"prod.danawa.com","www.bestbuy.com"}
  #   http면 host in RENDER_HOSTS → render_html, 아니면 기존 httpx
  ```
- **연결점**: `danawa.py` 등 수집기 **무변경** — parse가 렌더된 DOM을 받음
- **검증**: 렌더 HTML을 `inspect_page.py`로 셀렉터 추출 → 픽스처 테스트(`test_samsung_fixture` 패턴)로 파싱 0→N건
- **난이도**: 중

## Phase 2 — Frontier/Queue + Raw Store 해시 (1~2일)
- **목표**: 크롤 대상 관리 + 원본 보존 + 변경 없으면 파싱 스킵(비용 절감)
- **산출물**: `crawl_queue`·`crawl_raw` 테이블(schema), `crawler/frontier.py`
- **스키마**:
  ```sql
  CREATE TABLE crawl_queue(
    id BIGSERIAL PK, url TEXT, source TEXT, priority INT DEFAULT 5,
    status TEXT DEFAULT 'pending', content_hash TEXT,
    last_crawled TIMESTAMPTZ, next_due TIMESTAMPTZ, fail_count INT DEFAULT 0,
    UNIQUE(url, source));
  CREATE TABLE crawl_raw(
    id BIGSERIAL PK, url TEXT, source TEXT, content_hash TEXT,
    fetched_at TIMESTAMPTZ DEFAULT now());  -- 원본은 data/raw/ 파일, 해시만 DB
  ```
- **로직**: 시드에서 큐 채움 → dedup(url,source) → 우선순위·`next_due`로 스케줄 → 실패 백오프
- **연결점**: `base.collect()`가 큐에서 타깃을 받도록 확장, `_dump_raw`가 해시 기록
- **검증**: 같은 URL 2회 크롤 → 해시 동일 시 "파싱 스킵" 로그, 큐 status 전이 확인
- **난이도**: 중

## Phase 3 — 변경 감지 & 이벤트 (1일)
- **목표**: 해시 diff로 가격변동·신제품·EOL 이벤트 발행 → 재임베딩/알림 트리거
- **산출물**: `crawler/change_detector.py`, `crawl_event` 테이블
- **로직**:
  - variant 가격 변동 → `price_history`는 이미 축적 → 임계 초과 변동 시 이벤트
  - 신 `model_code_base` 등장 → `whats_new` 대상, positioning 필요 → 임베딩 재생성 트리거
  - 재고 'eol' → series/variant `status` 갱신
- **연결점**: `build_embeddings.py`를 신규 series에만 증분 실행
- **검증**: 시드 가격 변경본 재적재 → 이벤트 1건 생성 확인
- **난이도**: 중

## Phase 4 — API 어댑터 (2~3일, 제휴 의존)
- **목표**: 공식/제휴 API로 가격·커버리지 대폭 확대(가장 안정적 소스)
- **산출물**: `collectors/naver_shopping.py`(공개 API), (제휴 시)`danawa_api.py`
- **핵심**: `fetch()`=REST 호출, `parse()`=JSON→`RawRecord`. 나머지 파이프라인 무변경
- **연결점**: `pipeline._load_collectors`에 등록, `config/targets`에 검색어
- **검증**: 검색어 1개로 variant/price 레코드 수집 → DB 적재 확인
- **난이도**: 중 (API 키/제휴)

## Phase 5 — LLM 폴백 파서 & 셀렉터 자가복구 (2~3일)
- **목표**: 셀렉터 실패/사이트 개편에 자가 대응, 비정형 스펙 추출
- **산출물**: `parser/llm_extract.py`(Claude 구조화), `tools/suggest_selectors.py`
- **핵심**:
  - 셀렉터 파싱 결과가 비면 → 페이지 텍스트를 Claude에 주고 스키마 필드 추출(`spec_pdf` 패턴 재사용)
  - 개편 감지 시 `inspect_page` + Claude로 후보 셀렉터 제안 → `config/selectors.py` 갱신 리뷰
- **연결점**: `spec_pdf.py`의 EXTRACT_SCHEMA/SYSTEM 재활용
- **검증**: 셀렉터 고의 파손 → LLM 폴백이 핵심 필드 복구
- **난이도**: 중~높음

## Phase 6 — 관측성 · 스케줄 통합 · 운영 (1~2일)
- **목표**: 소스별 수집량·성공률·신선도 모니터링, 실패 급증 알림
- **산출물**: `crawler/metrics.py`, launchd plist 확장(가격 외 크롤 주기), 대시보드(선택)
- **연결점**: 기존 `collect_prices.py`+plist 패턴을 크롤 파이프라인 전반으로 확장
- **검증**: 크롤 1회전 후 소스별 건수/성공률 로그, 실패율 임계 시 메일/Slack
- **난이도**: 중

---

## 단계 요약

| Phase | 산출물 | 의존성 | 난이도 | 즉효성 |
|---|---|---|---|---|
| 0 준비 | playwright 설치 | - | 낮음 | - |
| 1 렌더 Fetcher | render.py + 분기 | P0 | 중 | ★★★ |
| 2 큐+원본해시 | crawl_queue/raw | - | 중 | ★★ |
| 3 변경감지 | change_detector | P2 | 중 | ★★ |
| 4 API 어댑터 | naver_shopping | API키/제휴 | 중 | ★★★ |
| 5 LLM 파서 | llm_extract | P1 | 중~높 | ★★ |
| 6 운영 | metrics/스케줄 | P1~4 | 중 | ★ |

**권장 순서**: P0→P1(다나와 실크롤 즉효) → P2(효율화) → P4(API 커버리지) → P3(변경감지) → P5(자가복구) → P6(운영).
각 Phase는 앞 단계 없이도 부분 가치 산출(P1만으로도 JS 사이트 수집 가능).
