"""
TV 밝기(peak_brightness_nits) 출처 보충 — model.brightness_source 채움. 멱등.

밝기값의 출처를 모델별로 명시한다:
  - enrich_brightness.BRIGHT 등재(2023~2025 주요 모델) → "RTINGS/전문리뷰 실측+동급 근사"
  - 그 외(골든셋 직접 입력, 대개 2025~2026 신모델) → "골든셋(공식 사이트/뉴스 확인)"
  - 별도 실측(measurement) 존재 시 → "· 실측 출처 {source}" 부기
  ※ 스펙값(model.peak_brightness_nits)과 실측값(measurement.peak_brightness_nits)은 별개.

실행: ./.venv/bin/python -m scripts.load_brightness_source
"""
from __future__ import annotations
import os
import psycopg

from scripts.enrich_brightness import BRIGHT

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")


def main():
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()
        cur.execute("""select m.model_id, m.model_code_base, m.peak_brightness_nits,
                              me.source, me.peak_brightness_nits meas
                       from model m left join measurement me on me.model_id=m.model_id""")
        n = 0
        for mid, code, spec, meas_src, meas in cur.fetchall():
            if spec is None and meas is None:
                src = None
            else:
                base = ("RTINGS/전문리뷰 실측+동급 근사" if code in BRIGHT
                        else "골든셋(공식 사이트/뉴스 확인)")
                if meas_src:
                    base += f" · 실측 출처 {meas_src}({meas}nit)"
                src = base
            conn.cursor().execute("update model set brightness_source=%s where model_id=%s", (src, mid))
            n += 1
        conn.commit()
    print(f"brightness_source {n}종 보충.")


if __name__ == "__main__":
    main()
