"""
중화권(Xiaomi·Huawei) 공식 CNY 가격 보강 — 홈마켓(중국) 출시가. 멱등(변형별 UPDATE).

값 출처(2026-08 WebSearch): mi.com·중관촌재선·mydrivers 등 공식 발표가.
  Xiaomi S Pro Mini LED 2026(S-Pro26): 65″6499 / 75″7999 (零售价)
  Xiaomi 大师 Master OLED(MasterOLED):  65″9999 / 77″19999
  Huawei Vision 智慧屏5(Vision5):        65″5499 (起售价)
region 이 Global 이어도 실제 MSRP 는 중국 CNY 뿐이므로 currency=CNY 로 명시 기록.

실행: ./.venv/bin/python -m scripts.load_cn_prices
"""
from __future__ import annotations
import os
import psycopg

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")

# (model_code_base, size_inch, cny_msrp, note)
ROWS: list[tuple] = [
    ("S-Pro26",    65,  6499, "小米 S Pro Mini LED 2026 零售价"),
    ("S-Pro26",    75,  7999, "小米 S Pro Mini LED 2026 零售价"),
    ("S-Pro26",    85, 10499, "小米 S Pro Mini LED 2026 零售价"),
    ("S-Pro26",    98, 15999, "小米 S Pro Mini LED 2026 零售价"),
    ("MasterOLED", 65,  9999, "小米电视 大师 OLED"),
    ("MasterOLED", 77, 19999, "小米电视 大师 OLED"),
    ("Vision5",    65,  5499, "华为 Vision 智慧屏5 起售价"),
    # 2026 중국 신제품(년중 런칭)
    ("Q9MPro",     55,  6199, "TCL Q9M Pro SQD-Mini LED 首发"),
    ("Q9MPro",     98, 19999, "TCL Q9M Pro SQD-Mini LED"),
    ("E8NPro",     65,  7099, "海信 E8N Pro Mini LED"),
    ("E8NPro",     75,  8999, "海信 E8N Pro Mini LED"),
    ("E8NPro",     85, 11999, "海信 E8N Pro Mini LED"),
    ("E8NPro",    100, 21999, "海信 E8N Pro Mini LED"),
    ("E8QPro",     75, 13599, "海信 E8Q Pro Mini LED(8320존·Devialet)"),
    ("E8QPro",     85, 17999, "海信 E8Q Pro Mini LED"),
    ("E8QPro",    100, 27999, "海信 E8Q Pro Mini LED"),
    ("T7MUltra",   65,  6799, "TCL T7M Ultra SQD-Mini LED 起售价"),
    ("T7MUltra",   98, 15999, "TCL T7M Ultra SQD-Mini LED"),
    ("T7MPro",     65,  6199, "TCL T7M Pro SQD-Mini LED 起售价"),
    ("RedmiX26",   55,  2499, "Redmi X 2026 Mini LED 起售价"),
    ("RedmiX26",   85,  4799, "Redmi X 2026 Mini LED"),
    ("RedmiX26",   98,  7599, "Redmi X 2026 Mini LED"),
]


def main():
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()
        n = 0
        for code, size, cny, note in ROWS:
            cur.execute("""
                update variant v
                   set price_msrp = %s, currency = 'CNY', source_url = coalesce(source_url, %s)
                  from model m
                 where v.model_id = m.model_id
                   and m.model_code_base = %s and v.size_inch = %s
                   and v.price_msrp is null
            """, (cny, "mi.com/华为官网", code, size))
            if cur.rowcount == 0:
                # 이미 값이 있거나 변형 없음 — 확인용
                cur.execute("""select count(*) from variant v join model m on v.model_id=m.model_id
                               where m.model_code_base=%s and v.size_inch=%s""", (code, size))
                exists = cur.fetchone()[0]
                print(f"  ⏭ {code} {size}\" — 미적용(변형 {exists}개, 기존가 있거나 없음)")
            else:
                n += cur.rowcount
        conn.commit()
        cur.execute("""select b.name, m.model_code_base, v.size_inch, v.price_msrp, v.currency
                       from variant v join model m on v.model_id=m.model_id
                       join series s on m.series_id=s.series_id join brand b on s.brand_id=b.brand_id
                       where v.currency='CNY' order by b.name, m.model_code_base, v.size_inch""")
        cny_rows = cur.fetchall()
    print(f"CNY 가격 {n}개 변형 보강. (전체 CNY 변형 {len(cny_rows)}개)")
    for name, code, size, price, cur_ in cny_rows:
        print(f"  {name:7} {code:11} {size}\"  {price} {cur_}")


if __name__ == "__main__":
    main()
