"""
사이즈별 세부 스펙 override 적재 — 같은 시리즈라도 사이즈마다 패널/주사율이 다른 경우. 멱등.

예) 삼성 S90(QD-OLED)의 77/83"는 QD-OLED가 아닌 **WOLED** 패널.
    The Frame/Q8F의 소형(43/50")은 120Hz가 아닌 **60Hz**.

variant.panel_override / refresh_override 에 기록(모델 기본값과 다를 때만).
실행: ./.venv/bin/python -m scripts.load_size_overrides
"""
from __future__ import annotations
import os
import psycopg

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")

# code: {"panel": {panel_val: [sizes]}, "refresh": {hz: [sizes]}}
OVERRIDES: dict[str, dict] = {
    "S90F":  {"panel": {"WOLED": [77, 83]}},              # QD-OLED는 42~65", 대형은 WOLED
    "S90D":  {"panel": {"WOLED": [42, 48, 77, 83]}},      # 2024: QD-OLED 55/65만
    "S99H":  {"panel": {"WOLED": [83]}},                  # 2026: 83"만 WOLED
    "S85F":  {"panel": {"WOLED": [77, 83]}},              # 2025: QD-OLED 55/65, 77/83=WOLED
    "LS03F": {"refresh": {60: [32, 43, 50]}},             # The Frame 소형 60Hz
    "Q8F":   {"refresh": {60: [43, 50]}},                 # 소형 60Hz, 대형 120Hz
    "M5":    {"refresh": {120: [97]}},                    # 97"만 120Hz(나머지 144Hz)
    "S-2026": {"refresh": {144: [85, 98]}},               # Xiaomi S Mini LED 2026: 55~75=60Hz, 85/98=144Hz
}


def main():
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()
        n = 0
        for code, ov in OVERRIDES.items():
            cur.execute("select model_id from model where model_code_base=%s", (code,))
            row = cur.fetchone()
            if not row:
                continue
            mid = row[0]
            for panel, sizes in ov.get("panel", {}).items():
                cur.execute("update variant set panel_override=%s where model_id=%s and size_inch = any(%s)",
                            (panel, mid, sizes))
                n += cur.rowcount
            for hz, sizes in ov.get("refresh", {}).items():
                cur.execute("update variant set refresh_override=%s where model_id=%s and size_inch = any(%s)",
                            (hz, mid, sizes))
                n += cur.rowcount
        conn.commit()
    print(f"사이즈별 override {n}개 variant 반영.")


if __name__ == "__main__":
    main()
