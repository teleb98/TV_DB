"""
소스별 CSS 셀렉터 — 한 곳에서 관리(사이트 개편 시 여기만 수정).
⚠ 셀렉터는 사이트 실제 HTML을 봐야 확정된다. 아래는 채워야 할 슬롯.
   tools/inspect_page.py 로 후보 셀렉터를 뽑아 채운 뒤, 골든셋으로 검증하라.
   빈 문자열("")이면 해당 필드 스킵(수집기가 방어).
"""

SAMSUNG = {
    "series_name":  "",   # 예: "h1.product-title"
    "model_code":   "",   # 정식 모델명 표기 노드
    "resolution":   "",
    "refresh":      "",
    "panel":        "",   # 'Neo QLED' 등 마케팅 패널명
    "hdr":          "",
    "processor":    "",
    "spec_table":   "",   # 전체 스펙표 컨테이너(<tr> 순회)
    "size_options": "",   # 인치 옵션 버튼/리스트
}

DANAWA = {
    "product_card": "",   # 상품 리스트의 각 카드 컨테이너
    "model_name":   "",   # 카드 내 모델명
    "brand":        "",
    "price":        "",   # 최저가 표기
}
