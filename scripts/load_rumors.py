"""
미출시/루머 제품 사전정보(pre_release_intel) 적재 — 주요국 뉴스·공급망·인증DB 소스. 멱등.

미확정 정보를 확정 model 과 분리 격리한다. 교차검증(독립출처≥2 or 인증DB)으로 confidence 상향,
출시 확정 시 golden CSV 로 승격(status=released, promoted_to=<코드>).
근거·프로토콜: docs/UNRELEASED_SOURCING.md

실행: ./.venv/bin/python -m scripts.load_rumors
"""
from __future__ import annotations
import os
import psycopg

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")

# (brand, tentative_model, category, spec_summary, expected_year, source_org, country,
#  tier, url, report_date, confidence, corroboration, status, note)
INTEL: list[tuple] = [
    ("LG", "Micro RGB evo", "tv",
     "Micro RGB LED 백라이트, 100% BT.2020, 1000+ 로컬디밍존, SDR Adobe RGB/DCI-P3 100%",
     2026, "TechRadar/Engadget", "US", "official-teaser",
     "https://www.techradar.com/televisions/the-age-of-next-gen-rgb-tvs-is-here",
     "2026-01-06", "high", 3, "announced",
     "삼성 Micro RGB(R95H) 대항 라인. 75/86/100인치 공식 예고. 정식 모델코드 미확정."),
    ("Samsung", "QD-OLED Penta Tandem", "panel",
     "5층 탠덤 QD-OLED 패널, 4500nit 목표(캘리 ~2500nit). 55/65/77 적용 예정",
     2026, "FlatpanelsHD", "Global", "supply-chain",
     "https://www.flatpanelshd.com/news.php?id=1770897946",
     "2026-02-01", "med", 2, "announced",
     "삼성디스플레이 차세대 패널 브랜딩. LG Tandem WOLED(4층) 대응."),
    ("LG", "QD-OLED 게이밍 모니터", "monitor",
     "삼성디스플레이 QD-OLED 패널 공급 협의(4K). LG전자 첫 QD-OLED 모니터",
     2026, "디일렉(thelec)/OLED-Info", "KR", "supply-chain",
     "https://www.thelec.net/news/articleView.html?idxno=6464",
     "2026-05-01", "med", 2, "rumored",
     "부품 공급망 확인. 하반기 출시 가능성. 모델명 미정."),
    ("Samsung", "24인치 OLED 모니터 패널", "monitor",
     "삼성디스플레이 24\" OLED 모니터 패널 양산계획 유출. 첫 24인치급 OLED",
     2027, "choose.tv", "US", "leak",
     "https://www.choose.tv/us/news/the-first-24-oled-monitor-will-be-available-in-2027",
     "2026-03-01", "low", 1, "rumored",
     "생산계획 유출 단계. 2027 양산 목표. 단일 출처."),
]


def main():
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()
        n = 0
        for row in INTEL:
            (brand, tm, cat, summ, yr, org, country, tier, url, rdate,
             conf, corrob, status, note) = row
            # 멱등: (brand, tentative_model) 기준 갱신
            cur.execute("delete from pre_release_intel where brand=%s and tentative_model=%s", (brand, tm))
            cur.execute("""
                insert into pre_release_intel(brand, tentative_model, category, spec_summary,
                    expected_year, source_org, source_country, source_tier, source_url,
                    report_date, confidence, corroboration, status, note)
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (brand, tm, cat, summ, yr, org, country, tier, url, rdate, conf, corrob, status, note))
            n += 1
        conn.commit()
    print(f"pre_release_intel {n}건 적재(미출시 사전정보).")


if __name__ == "__main__":
    main()
