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

DANAWA = {
    "product_card": "",   # 상품 리스트의 각 카드 컨테이너
    "model_name":   "",   # 카드 내 모델명
    "brand":        "",
    "price":        "",   # 최저가 표기
}
