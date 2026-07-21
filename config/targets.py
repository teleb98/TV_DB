"""
수집 타깃 목록 — 소스별 시드 URL/경로.
※ 여기의 URL은 '진입점(카테고리/검색/제품)' 시드. 실제 운영 시 크롤 큐로 확장.
※ 크롤링 전 각 사이트 robots.txt / 이용약관 확인. 가능하면 공식 API·제휴 우선.
"""

TARGETS: dict[str, list[str]] = {
    # 삼성 공식 — 제품 상세페이지 (정확도 최우선). 실제 모델 URL로 확장.
    "samsung_official": [
        "https://www.samsung.com/sec/tvs/all-tvs/",          # 국내 TV 전체 진입점
        # "https://www.samsung.com/sec/tvs/qled-tv/QN90D-...", # TODO: 개별 제품 URL
    ],
    # 다나와 — TV 카테고리(커버리지·가격). 검색어/카테고리 코드로 확장.
    "danawa": [
        "https://prod.danawa.com/list/?cate=102845",          # TV 카테고리 예시 코드
        # 브랜드별 필터 URL 추가 가능
    ],
    # 스펙시트 PDF — 로컬 경로. 공식몰/보도자료에서 내려받아 data/pdf/ 에 저장.
    "spec_pdf": [
        # "data/pdf/samsung_QN90D_2024_spec.pdf",             # TODO
    ],
}

# 지역 확장(2차 북미)
TARGETS_US: dict[str, list[str]] = {
    "samsung_official": ["https://www.samsung.com/us/televisions-home-theater/tvs/"],
    "danawa": [],   # 북미는 Best Buy 등 별도 수집기로 대체
    "spec_pdf": [],
}
