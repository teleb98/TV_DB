# 데이터 소스 연결 & 공식 스펙 검수 — 실행 방안

현재 파이프라인(수집기→정규화→4계층 적재→에이전트)은 완성돼 있고, 남은 건
**실데이터 소스 연결**과 **골든셋 정답지 확정(공식 스펙 검수)** 이다.
이 문서는 기존 코드에 그대로 붙일 수 있는 방안을 신뢰도·준법 리스크 순으로 정리한다.

---

## A. 데이터 수집 경로 (신뢰도/안정성 높은 순)

### 1순위 — 공식 API / 제휴 피드  ★가장 안정적
JS 렌더링·안티봇·ToS 문제가 없다. 계약/승인이 필요하지만 운영 관점 최선.

| 소스 | 얻는 것 | 형태 | 비고 |
|---|---|---|---|
| 네이버 쇼핑 검색 API | 상품/최저가/몰 | 공개 REST(JSON) | 신청 즉시 가능, 커버리지 넓음 |
| 다나와 제휴 API | 모델·가격·랭킹 | 제휴 계약 | 커버리지 최다 |
| 삼성/LG 파트너 피드 | 공식 스펙·라인업 | B2B 계약 | 정확도 최상 |

**코드 붙이는 법**: `collectors/naver_shopping.py` 같은 새 수집기 하나 추가.
`fetch()`=API 호출, `parse()`=JSON→`RawRecord`. 나머지(정규화·적재·에이전트)는 무변경.
`config/targets.py`에 검색어/카테고리만 등록.

### 2순위 — 공식 스펙시트 PDF  ★이미 구현됨
`collectors/spec_pdf.py`가 **PDF→Claude 구조화 추출**을 이미 갖췄다. 정확도 최상, JS 무관.
검수 정답지로도 최적(→ C절).

**코드 붙이는 법**: 제조사 다운로드센터/보도자료 PDF를 `data/pdf/`에 저장 →
`config/targets.py`의 `spec_pdf` 경로 채우기 → `pipeline.py --source spec_pdf` 실행. **코드 변경 0.**

### 3순위 — 정적 HTML 크롤링 (셀렉터 확정)
samsung.com 일부·리테일러 정적 페이지 등 정적 렌더 대상.

**코드 붙이는 법**: `tools/inspect_page.py <url>`로 후보 셀렉터 추출 →
`config/selectors.py` 채움 → `tests/test_samsung_fixture.py`처럼 픽스처로 검증.
(픽스처 검증 패턴은 이미 구축돼 있음.)

### 4순위 — JS 렌더링/안티봇 → Playwright 헤드리스
다나와·쿠팡·Best Buy 등 정적 파서로 0건인 사이트. **준법 검토 필수**(→ E절).

**코드 붙이는 법**: B절 참조.

---

## B. Playwright 연동 구체안

정적 `httpx`로 안 잡히는 사이트를 헤드리스 크롬으로 렌더 후 기존 `parse()` 재사용.

```bash
.venv/bin/pip install playwright && .venv/bin/playwright install chromium
```

`collectors/render.py` 신설(개념):
```python
def render_html(url, wait="networkidle", timeout=20000):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(user_agent="tv-spec-db/0.1")
        pg.goto(url, wait_until=wait, timeout=timeout)
        html = pg.content()
        b.close()
        return html
```

`collectors/base.py:fetch_html()`에 도메인 분기 추가:
```python
RENDER_HOSTS = {"prod.danawa.com", "www.bestbuy.com"}  # JS 사이트만
# http면: host in RENDER_HOSTS → render_html(url), 아니면 기존 httpx GET
```
→ **수집기(`danawa.py` 등) 코드는 무변경**. `parse()`는 렌더된 HTML을 그대로 받는다.
셀렉터는 렌더 후 DOM 기준으로 `inspect_page.py`(로컬 저장 HTML)로 확정.

주의: user-agent·요청 지연·세션 재사용으로 예의 갖추되, **캡차 우회 등 과도한 회피는 금지**.

---

## C. 공식 스펙 검수 (골든셋 정답지 확정)

목적: 현재 골든셋의 **대표값**을 공식값으로 대체/확인하고 `data_confidence`를 승격.

| 방안 | 방법 | 신뢰도 |
|---|---|---|
| ① 공식 스펙시트 PDF 대조 | `spec_pdf`로 추출한 값 ↔ 골든셋 diff | 최상 |
| ② 측정 매체 교차검증 | RTINGS 등 밝기·주사율·존수 WebSearch/WebFetch | 상 |
| ③ LLM 보조 검수 | 골든셋 행 + 공식 텍스트를 Claude에 주고 불일치 필드 리포트 | 상(사람 확인 전제) |
| ④ 신뢰도 라벨링 | 검수 완료 행만 `data_confidence='high'`, 미검수는 `med` | 운영 |

**코드 붙이는 법**: `scripts/verify_specs.py` 신설 —
각 모델의 공식 URL/PDF에서 스펙 추출(spec_pdf 재사용) → 골든셋과 필드별 diff →
불일치 리포트 출력 + 일치 시 `series/model` 행 `data_confidence='high'`로 UPDATE.
이미 있는 `status/data_confidence` 스키마가 이 검수 결과를 담는 자리.

---

## D. 권장 로드맵 (위험도 낮은 것부터)

1. **Phase 1 (즉시·저위험)**: `spec_pdf`로 플래그십 공식 스펙시트 10~15개 확보 →
   `verify_specs.py`로 골든셋 검수·정답지 확정. **코드 거의 무변경, ToS/JS 무관.**
2. **Phase 2**: 네이버쇼핑 API(공개) 수집기 추가 → 가격·커버리지 자동화. 다나와 제휴 병행 신청.
3. **Phase 3**: 정적 페이지 셀렉터 확정(`inspect_page`).
4. **Phase 4**: 준법 검토 후 Playwright로 JS 사이트(다나와/쿠팡/Best Buy) 연동.

각 Phase는 독립적으로 가치 산출(다음 Phase 없이도 DB 개선).

---

## E. 법적 · 운영 준수 체크리스트

- 수집 전 각 사이트 **robots.txt / 이용약관** 확인. 가능하면 **공식 API·제휴 우선**.
- 리뷰/설명 **원문 복제 금지** — 사실 데이터(스펙·가격)만 저장.
- **rate limit·요청 지연·캐싱**으로 부하 최소화. 캡차 우회·과도한 안티봇 회피 지양.
- 가격은 **`captured_at` 타임스탬프** 필수(이미 `price_history`에 반영).
- 개인정보(리뷰 작성자 등) 수집 배제.

---

## F. 방안 비교 요약

| 경로 | 난이도 | 신뢰도 | 준법리스크 | 코드 변경 |
|---|---|---|---|---|
| 공식 API/제휴 | 중(계약) | 최상 | 낮음 | 수집기 1개 추가 |
| 스펙시트 PDF | 낮음 | 최상 | 낮음 | **0 (구현됨)** |
| 정적 크롤링 | 중 | 중 | 중 | 셀렉터 채우기 |
| Playwright(JS) | 높음 | 중 | **높음** | render 모듈 + 분기 |
| 공식 스펙 검수 | 중 | 최상 | 낮음 | verify 스크립트 |

**결론**: 코드 변경이 거의 없고 준법 리스크가 낮은 **스펙시트 PDF 검수(Phase 1)** 부터 시작하는 것이 가장 효율적. 가격 자동화는 **공식 API**로, JS 사이트는 최후에 **Playwright + 준법 검토**로.
