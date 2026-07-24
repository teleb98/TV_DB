"""
소스별 CSS 셀렉터 — 한 곳에서 관리(사이트 개편 시 여기만 수정).
⚠ 셀렉터는 사이트 실제 HTML을 봐야 확정된다. 아래는 채워야 할 슬롯.
   tools/inspect_page.py 로 후보 셀렉터를 뽑아 채운 뒤, 골든셋으로 검증하라.
   빈 문자열("")이면 해당 필드 스킵(수집기가 방어).
"""

# tests/fixtures/samsung_qn90d.html 구조에 맞춰 확정(픽스처 검증 완료).
# ⚠ 실 samsung.com 은 마크업이 다르므로 tools/inspect_page.py 로 재확인 필요.
SAMSUNG = {
    "series_name":  "h1.pd-title",
    "model_code":   ".model-code",
    "resolution":   "li[data-spec='resolution'] .val",
    "refresh":      "li[data-spec='refresh'] .val",
    "panel":        "li[data-spec='panel'] .val",     # 'Neo QLED' → 사전으로 정규화
    "hdr":          "li[data-spec='hdr'] .val",
    "processor":    "li[data-spec='processor'] .val",
    "spec_table":   "table.spec-table tr",             # <tr><th>라벨</th><td>값</td>
    "size_options": ".size-options button",            # data-sku + '65형'
}

# 렌더된 다나와 DOM에서 발견한 컨테이너 계열(2026 BEM). 상품카드 클래스는 확인됨.
# ⚠ 정확한 TV '카테고리 상품 그리드' URL(cate 코드)로 재확인 필요 — 현재 리스트엔 광고 레일 혼재.
#   model_name/price 는 카드 내부 정제 셀렉터로 후속 확정.
DANAWA = {
    "product_card": "li.prod-list__item",   # 상품 카드(광고 카드 class*=ad 제외 필요)
    "model_name":   "a.prod-list__link",     # 모델명 링크(텍스트에 할인율·가격 혼입 → 정제 필요)
    "brand":        "",
    "price":        ".prod-list__price",     # 가격 영역(숫자만 추출)
}
