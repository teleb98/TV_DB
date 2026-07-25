"""
2026 released 스펙 보강 — 삼성/LG 2026 OLED·Neo QLED의 주사율·프로세서·밝기·게이밍·연결 채움. 멱등.

golden_models_2026.csv 는 CES 발표 시점 'announced' seed(주사율/프로세서/게이밍 미기재)라
CES 2026 이후 확정된 실사양을 여기서 채운다(WebSearch 2026-07 확인). gaming/connectivity 는
2026 seed CSV 컬럼에 없어 여기서만 반영(이후 seed 재적재해도 COALESCE로 보존).

실행: ./.venv/bin/python -m scripts.load_2026_specs
"""
from __future__ import annotations
import os
import psycopg

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")

# code: (refresh, processor, nits, gaming|파이프, connectivity|파이프)
SPECS: dict[str, tuple] = {
    "QN990H": (165, "NQ8 AI Gen3", 2500, "VRR|ALLM|240Hz|FreeSync Premium Pro", "HDMI2.1 x5|eARC|WiFi6E|Bluetooth"),
    "QN80H":  (144, "NQ4 AI Gen2", 1100, "VRR|ALLM|144Hz|FreeSync Premium Pro|G-Sync", "HDMI2.1 x4|eARC|WiFi|Bluetooth"),
    "QN70H":  (120, "NQ4 AI Gen2", 750,  "VRR|ALLM|144Hz|FreeSync Premium", "HDMI2.1 x4|eARC|WiFi|Bluetooth"),
    "S95H":   (165, "NQ4 AI Gen3", 2704, "VRR|ALLM|165Hz|FreeSync Premium Pro", "HDMI2.1 x4|eARC|WiFi|Bluetooth"),
    "S99H":   (165, "NQ4 AI Gen3", 2800, "VRR|ALLM|165Hz|FreeSync Premium Pro", "HDMI2.1 x4|eARC|WiFi|Bluetooth"),
    "S90H":   (165, "NQ4 AI Gen3", 2450, "VRR|ALLM|165Hz|FreeSync Premium Pro", "HDMI2.1 x4|eARC|WiFi|Bluetooth"),
    "S85H":   (120, "NQ4 AI Gen2", 800,  "VRR|ALLM|120Hz|FreeSync Premium|G-Sync", "HDMI2.1 x4|eARC|WiFi|Bluetooth"),
    "G6":     (165, "α11 AI Gen2", 2481, "VRR|ALLM|165Hz|G-Sync|FreeSync|Dolby Vision Gaming", "HDMI2.1 x4|eARC|WiFi|Bluetooth"),
    "C6":     (144, "α11 AI Gen2", 1438, "VRR|ALLM|144Hz|G-Sync|FreeSync|Dolby Vision Gaming", "HDMI2.1 x4|eARC|WiFi|Bluetooth"),
    "B6":     (120, "α8 AI Gen3",  835,  "VRR|ALLM|120Hz|G-Sync|FreeSync|Dolby Vision Gaming", "HDMI2.1 x4|eARC|WiFi|Bluetooth"),
}


def main():
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()
        n = 0
        for code, (hz, proc, nits, gaming, conn_s) in SPECS.items():
            cur.execute("""
                update model set
                  refresh_rate_native = %s,
                  processor = %s,
                  peak_brightness_nits = %s,
                  gaming_features = %s,
                  connectivity = %s
                where model_code_base = %s""",
                (hz, proc, nits, gaming.split("|"), conn_s.split("|"), code))
            n += cur.rowcount
        conn.commit()
    print(f"2026 released 스펙 {n}종 보강(주사율·프로세서·밝기·게이밍·연결).")


if __name__ == "__main__":
    main()
