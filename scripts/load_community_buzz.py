"""
IT 커뮤니티 관심/화제 모델(community_buzz) 적재 — 정성 여론 신호. 멱등(UNIQUE upsert).

커뮤니티 여론 기반 '관심도'(하드 판매지표가 아님). model_code_base 로 model 과 조인.
값 출처(2026-08 WebSearch): Reddit r/4kTV·r/television, AVSForum/AVForums, RTINGS,
한국 커뮤니티(클리앙·퀘이사존·뽐뿌). interest=very-high/high/medium.

실행: ./.venv/bin/python -m scripts.load_community_buzz
"""
from __future__ import annotations
import os
import psycopg

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")
ASOF = "2026-08-01"

U_REDDIT = "https://www.rtings.com/tv/reviews/best/tvs-on-the-market"
U_AVS = "https://www.avsforum.com/threads/samsung-s95h-qd-oled-tv-review-not-just-a-pretty-frame.3343251/"
U_RTINGS_BUDGET = "https://www.rtings.com/tv/reviews/best/budget"
U_KR = "https://www.clien.net/service/board/park/18957510"

# (model_code, community, region, interest, rank, reason, source_url)
ROWS: list[tuple] = [
    # ── 해외 엔thusiast: 2025 플래그십 OLED 대전 ──
    ("C5",     "reddit",   "Global", "very-high", 1, "가장 많이 추천되는 OLED — '거의 완벽', 가성비 플래그십", U_REDDIT),
    ("G5",     "reddit",   "Global", "very-high", 2, "2025 WOLED 플래그십(Primary RGB Tandem), 밝기 대폭 향상·5/5 리뷰", U_REDDIT),
    ("S95F",   "reddit",   "Global", "very-high", 3, "QD-OLED 최상위·Glare Free·5/5 리뷰, LG G5와 양강 비교글 다수", U_REDDIT),
    ("S90F",   "reddit",   "Global", "high",      5, "스텝다운 QD-OLED가 C5보다 밝다 — 가성비 화제", U_REDDIT),
    ("XR80II", "avsforum", "Global", "high",      4, "Sony Bravia 8 II QD-OLED — 화질처리 호평(4.5/5), 비교 스레드 활발", U_AVS),
    # ── 2026 기대작 ──
    ("S95H",   "avsforum", "Global", "very-high", 1, "2026 AVSForum Top Choice — 최상위 QD-OLED", U_AVS),
    ("G6",     "avsforum", "Global", "high",      2, "2026 WOLED 플래그십 기대작", U_AVS),
    ("C6",     "avsforum", "Global", "high",      3, "2026 C시리즈 — C5 후속 관심", U_AVS),
    # ── 가성비/버짓 킹 ──
    ("QM6K",   "rtings",   "Global", "very-high", 1, "RTINGS 2026 베스트 버짓 — $500 미만 최고 미니LED", U_RTINGS_BUDGET),
    ("U8Q",    "reddit",   "Global", "very-high", 2, "밝기 괴물 가성비 — 버짓 킹 후보로 자주 언급", U_REDDIT),
    ("QM8K",   "reddit",   "Global", "high",      6, "TCL 미니LED 플래그십 — 밝기·존수 가성비", U_REDDIT),
    ("U7Q",    "reddit",   "Global", "high",      7, "중급 미니LED 가성비 추천", U_REDDIT),
    ("U6Q",    "reddit",   "Global", "medium",    8, "엔트리 미니LED 인기 픽", U_RTINGS_BUDGET),
    ("R8C5",   "reddit",   "US",     "high",      9, "Roku Pro Series — 미니LED 가성비·단순 UI로 화제", U_REDDIT),
    # ── 한국 커뮤니티(클리앙·퀘이사존·뽐뿌) ──
    ("C5",     "korea",    "KR",     "very-high", 1, "클리앙/퀘이사존 OLED 대세 추천", U_KR),
    ("QN90F",  "korea",    "KR",     "high",      2, "삼성 Neo QLED 대표 추천 모델", U_KR),
    ("QM8K",   "korea",    "KR",     "high",      3, "쿠팡 TCL 미니LED 가성비로 화제", U_KR),
    ("U8Q",    "korea",    "KR",     "medium",    4, "하이센스 가성비 언급 증가", U_KR),
]

WEIGHT = {"very-high": 3, "high": 2, "medium": 1}


def main():
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()
        miss = 0
        for code, comm, region, interest, rank, reason, url in ROWS:
            cur.execute("select 1 from model where model_code_base=%s", (code,))
            if not cur.fetchone():
                print(f"  ⏭ DB에 없는 모델코드: {code}")
                miss += 1
            cur.execute("""
                insert into community_buzz
                    (model_code, community, region, interest, rank, buzz_reason, source_url, as_of)
                values (%s,%s,%s,%s,%s,%s,%s,%s)
                on conflict (model_code, community) do update set
                    region=excluded.region, interest=excluded.interest, rank=excluded.rank,
                    buzz_reason=excluded.buzz_reason, source_url=excluded.source_url,
                    as_of=excluded.as_of, updated_at=now()
            """, (code, comm, region, interest, rank, reason, url, ASOF))
        conn.commit()
        # 종합 관심 랭킹(커뮤니티 교차 = 가중합)
        cur.execute("""
            select cb.model_code, b.name brand, s.marketing_name lineup,
                   count(*) mentions,
                   sum(case cb.interest when 'very-high' then 3 when 'high' then 2 else 1 end) score,
                   string_agg(distinct cb.community, ',' order by cb.community) communities
            from community_buzz cb
            left join model m on m.model_code_base=cb.model_code
            left join series s on m.series_id=s.series_id
            left join brand b on s.brand_id=b.brand_id
            group by cb.model_code, b.name, s.marketing_name
            order by score desc, mentions desc
            limit 12
        """)
        top = cur.fetchall()
    print(f"community_buzz {len(ROWS)}행 적재 (DB 미매칭 {miss}종).")
    print("── 종합 관심 랭킹(커뮤니티 교차 가중합) ──")
    for code, brand, lineup, ment, score, comms in top:
        print(f"  {score:2}점 x{ment}  {code:8} {brand or '?':6} {lineup or '':22} [{comms}]")


if __name__ == "__main__":
    main()
