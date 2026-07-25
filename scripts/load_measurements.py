"""
실측 성능(measurement) 적재 — RTINGS 등 전문 리뷰 실측치. 멱등(model_id upsert).

값은 WebSearch(2026-07) 스니펫으로 확인한 실측치. peak/fullscreen=HDR 10% window 기준,
input_lag=4K/120Hz 근사(일부 4K60/1080p120 표기), dci_p3/rec2020=색재현 커버리지(%),
contrast=네이티브 명암비('inf'=OLED). 각 행 source 에 출처 표기(rtings/flatpanelshd/avforums 등).

주의: model.peak_brightness_nits(스펙/근사)와 별개로 measurement.peak_brightness_nits(실측)를 둔다.
실행: ./.venv/bin/python -m scripts.load_measurements
"""
from __future__ import annotations
import os
import psycopg

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")

# code: (peak, fullscreen, input_lag_ms, dci_p3, rec2020, contrast, measured_date, source)
MEASURE: dict[str, tuple] = {
    # 2025 플래그십/상위
    "QN90F":  (2500, 800,  None, 91.0,  None, None,     "2025-05-01", "rtings"),
    "S95F":   (3789, None, 13.2, 99.0,  None, "inf",    "2025-04-01", "rtings"),
    "S90F":   (1300, 250,  None, 99.0,  None, "inf",    "2025-05-01", "avforums"),
    "G5":     (2272, None, None, 100.0, 74.0, "inf",    "2025-04-01", "avforums"),
    "C5":     (1075, 199,  10.8, 97.0,  None, "inf",    "2025-04-01", "flatpanelshd"),
    "XR80II": (1681, 248,  None, 100.0, None, "inf",    "2025-08-01", "flatpanelshd"),
    "XR50":   (769,  None, None, 96.0,  None, None,     "2025-06-01", "hometheaterhifi"),
    "QM8K":   (2752, None, None, 95.0,  None, "6470:1", "2025-05-01", "rtings"),
    "QM7K":   (1731, None, None, 98.0,  None, "8392:1", "2025-05-01", "rtings"),
    "QM9K":   (5413, None, None, 97.0,  77.3, None,     "2025-10-01", "tomsguide"),
    "U8Q":    (4300, 944,  None, 95.0,  None, None,     "2025-06-01", "rtings"),
    "U7Q":    (3000, None, None, 93.0,  None, None,     "2025-06-01", "reviews"),
    # 2024
    "G4":     (1500, 235,  None, 97.5,  74.0, "inf",    "2024-04-01", "flatpanelshd"),
    "QN90D":  (2100, 800,  None, 90.0,  None, None,     "2024-05-01", "rtings"),
}


def main():
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()
        n = 0
        for code, (peak, full, lag, p3, rec, contrast, mdate, src) in MEASURE.items():
            cur.execute("select model_id from model where model_code_base=%s", (code,))
            row = cur.fetchone()
            if not row:
                print(f"  ⏭ DB에 없음: {code}")
                continue
            cur.execute("""
                insert into measurement(model_id, peak_brightness_nits, fullscreen_nits,
                                        input_lag_ms, dci_p3_pct, rec2020_pct, contrast,
                                        measured_date, source)
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                on conflict (model_id) do update set
                  peak_brightness_nits = excluded.peak_brightness_nits,
                  fullscreen_nits = excluded.fullscreen_nits,
                  input_lag_ms = excluded.input_lag_ms,
                  dci_p3_pct = excluded.dci_p3_pct,
                  rec2020_pct = excluded.rec2020_pct,
                  contrast = excluded.contrast,
                  measured_date = excluded.measured_date,
                  source = excluded.source,
                  updated_at = now()""",
                (row[0], peak, full, lag, p3, rec, contrast, mdate, src))
            n += 1
        conn.commit()
    print(f"실측(measurement) {n}종 적재.")


if __name__ == "__main__":
    main()
