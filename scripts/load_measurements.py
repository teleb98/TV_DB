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
    "U6Q":    (1000, None, None, None,  None, None,     "2025-06-01", "reviews"),
    "B5":     (688,  None, 9.0,  99.0,  None, "inf",    "2025-05-01", "techradar"),
    "R8C5":   (1818, None, None, 92.0,  None, None,     "2025-11-01", "tomsguide"),  # Roku Pro Series 2025
    "OLED910": (2100, None, None, 99.0,  None, "inf",    "2025-06-01", "flatpanelshd"),
    "OLED810": (1300, None, None, 99.0,  None, "inf",    "2025-09-01", "flatpanelshd"),
    "QN85F":  (1700, None, None, 90.0,  None, None,     "2025-05-01", "choose.tv"),
    "QN990F": (2109, 394,  None, 94.0,  None, None,     "2025-05-01", "reviews"),
    "QM6K":   (700,  None, None, 90.0,  None, "7000:1", "2025-04-01", "reviews"),
    "QN80F":  (1106, 754,  None, 93.0,  None, None,     "2025-05-01", "techradar"),
    "QNED9M": (1400, None, None, 95.0,  None, None,     "2025-05-01", "reviews"),
    "QNED92A": (1450, 770,  None, 97.0,  None, None,     "2025-05-01", "reviews"),
    "Q8F":    (1520, 420,  None, 93.0,  None, None,     "2025-06-01", "reviews"),
    "QN70F":  (733,  None, None, 90.0,  None, None,     "2025-06-01", "rtings"),
    "QN900F": (2109, 394,  None, 94.0,  None, None,     "2025-05-01", "reviews"),
    "S85F":   (1000, None, None, 99.0,  None, "inf",    "2025-06-01", "reviews"),
    "X11K":   (5000, None, None, 97.0,  None, None,     "2025-06-01", "reviews"),
    # 2024
    "G4":     (1500, 235,  None, 97.5,  74.0, "inf",    "2024-04-01", "flatpanelshd"),
    "QN90D":  (2100, 800,  None, 90.0,  None, None,     "2024-05-01", "rtings"),
    "C4":     (1049, 200,  13.0, 96.0,  None, "inf",    "2024-04-01", "flatpanelshd"),
    "A95L":   (1348, None, None, 99.9,  None, "inf",    "2024-01-01", "avforums"),
    "XR80":   (1300, None, None, 100.0, None, "inf",    "2024-05-01", "rtings"),
    # 2023
    "QN90C":  (2000, 680,  None, 90.0,  None, None,     "2023-05-01", "rtings"),
    "S90C":   (1000, 260,  None, 99.0,  None, "inf",    "2023-05-01", "rtings"),
    "X95L":   (1300, 780,  None, 92.0,  None, None,     "2023-06-01", "rtings"),
    "B3":     (655,  None, None, 97.0,  None, "inf",    "2023-05-01", "rtings"),
    "S95D":   (1868, None, None, 99.9,  None, "inf",    "2024-04-01", "avforums"),
    "U8N":    (2629, 695,  None, 97.0,  83.0, None,     "2024-05-01", "avforums"),
    "X90L":   (1600, 800,  None, 94.0,  76.0, None,     "2024-05-01", "reviews"),
    "QM851G": (3583, None, None, 97.4,  None, None,     "2024-05-01", "rtings"),
    "S90D":   (1015, 500,  None, 99.2,  95.0, "inf",    "2024-04-01", "reviews"),
    "XR70":   (1456, 600,  None, 97.0,  None, None,     "2024-05-01", "avforums"),
    "A80L":   (724,  None, None, 99.0,  None, "inf",    "2024-01-01", "reviews"),
    "B4":     (659,  None, None, 97.0,  None, "inf",    "2024-04-01", "reviews"),
    "U7N":    (1130, 658,  None, 96.0,  None, None,     "2024-05-01", "rtings"),
    # 2026
    "G6":     (2481, 471,  None, 99.7,  78.4, "inf",    "2026-03-01", "flatpanelshd"),
    "C6":     (1438, 236,  None, 99.7,  None, "inf",    "2026-03-01", "techradar"),
    "S95H":   (2704, 458,  None, 99.9,  None, "inf",    "2026-04-01", "reviews"),
    "B6":     (835,  None, None, 99.0,  None, "inf",    "2026-05-01", "techradar"),
    "S90H":   (2450, None, None, 99.0,  None, "inf",    "2026-04-01", "reviews"),
    "XR95II": (4250, None, None, 97.0,  90.0, None,     "2026-06-01", "reviews"),  # Bravia 9 II True RGB
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
