# 가격 소스 정책 (Pricing Policy)

공식 가격은 **지역별 대표 리테일러**를 표준 출처로 삼는다. `price_history.channel` 로 구분.

| 지역 | 표준 소스(공식가) | channel | 통화 | 로더 |
|---|---|---|---|---|
| **US 🇺🇸** | **Best Buy** (bestbuy.com 최신가) | `bestbuy` | USD | `scripts/load_retail_prices.py` |
| **EU 🇪🇺** | **MediaMarkt** (mediamarkt.de) | `mediamarkt` | EUR | `scripts/load_eu_prices.py` |
| **KR 🇰🇷** | 다나와 / SSG | `danawa`,`ssg` | KRW | `scripts/load_kr_prices.py` |
| **CN 🇨🇳** | 京东/브랜드 공식 | (내수) | CNY | 골든셋 직접 |

## 원칙
1. **US 최신가 = Best Buy**, **EU 최신가 = MediaMarkt** 를 우선 참조. 그 외 채널(amazon·walmart)은 보조.
2. `price_history` 에 채널·시점(`captured_at`)과 함께 스냅샷 적재(멱등) → 추세 추적. 현재가는 `variant.price_street`(최신 캡처)로 동기화.
3. `price_msrp` = 정가/UVP(권장소비자가). `mediamarkt`/`bestbuy` 값 = 실제 판매가.
4. 지역 variant(EU/US/KR) 단위로 통화 자동(`db.py` CASE: US→USD, EU→EUR, CN→CNY, else KRW).
5. 리테일가는 세일 변동이 크므로 `captured_at` 시점 고정 필수. 정기 재수집으로 갱신.

## 조회
- `GET /api/price/best?model=&region=EU` — 지역별 현재 최저가
- `GET /api/price/region?model=` — 동일 모델 지역별 현재가·통화
- `GET /api/price/trend?sku=&region=` — SKU 가격 이력(추세)

## 확인된 예시(2026-08)
- Best Buy(US): LG G5 65″ $2,199.99 · LG C5 65″ $1,099 · TCL QM8K 65″ $1,258
- MediaMarkt(EU): 삼성 S95F 65″ 3,529€ · LG G5 65″ 1,699€(UVP 3,999€)
- 다나와(KR): LG G5 65″ 257.6만 · 삼성 S95F 65″ 396.3만
