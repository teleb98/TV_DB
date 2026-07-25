"""
실측 성능(measurement) 적재 — RTINGS 등 전문 리뷰 실측치. 멱등(model_id upsert).

값은 WebSearch(2026-07) 스니펫으로 확인한 실측치. peak/fullscreen=HDR 10% window 기준,
input_lag=4K/120Hz 근사, dci_p3=DCI-P3 커버리지(%), contrast=네이티브 명암비('inf'=OLED).
각 행의 source 컬럼에 출처 표기(rtings/flatpanelshd/avforums 등).

주의: model.peak_brightness_nits(스펙/근사)와 별개로 measurement.peak_brightness_nits(실측)를 둔다.
실행: ./.venv/bin/python -m scripts.load_measurements
"""
from __future__ import annotations
import os
import psycopg

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")

# code: (peak_nits, fullscreen_nits, input_lag_ms, dci_p3_pct, contrast, measured_date, source)
MEASURE: dict[str, tuple] = {
    "QN90F":  (2500, 800,  None, 91.0,  None,     "2025-05-01", "rtings"),
    "S95F":   (3789, None, 13.2, 99.0,  "inf",    "2025-04-01", "rtings"),
    "G5":     (2272, None, None, 100.0, "inf",    "2025-04-01", "avforums"),
    "XR80II": (1681, 248,  None, 100.0, "inf",    "2025-08-01", "flatpanelshd"),
    "QM8K":   (2752, None, None, 95.0,  "6470:1", "2025-05-01", "rtings"),
    "U8Q":    (4300, 944,  None, 95.0,  None,     "2025-06-01", "rtings"),
}


def main():
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()
        n = 0
        for code, (peak, full, lag, p3, contrast, mdate, src) in MEASURE.items():
            cur.execute("select model_id from model where model_code_base=%s", (code,))
            row = cur.fetchone()
            if not row:
                print(f"  ⏭ DB에 없음: {code}")
                continue
            cur.execute("""
                insert into measurement(model_id, peak_brightness_nits, fullscreen_nits,
                                        input_lag_ms, dci_p3_pct, contrast, measured_date, source)
                values (%s,%s,%s,%s,%s,%s,%s,%s)
                on conflict (model_id) do update set
                  peak_brightness_nits = excluded.peak_brightness_nits,
                  fullscreen_nits = excluded.fullscreen_nits,
                  input_lag_ms = excluded.input_lag_ms,
                  dci_p3_pct = excluded.dci_p3_pct,
                  contrast = excluded.contrast,
                  measured_date = excluded.measured_date,
                  source = excluded.source,
                  updated_at = now()""",
                (row[0], peak, full, lag, p3, contrast, mdate, src))
            n += 1
        conn.commit()
    print(f"실측(measurement) {n}종 적재.")


if __name__ == "__main__":
    main()
