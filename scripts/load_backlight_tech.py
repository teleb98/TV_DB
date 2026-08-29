"""
백라이트 세부기술(backlight_tech) 재분류 — Mini-LED 계열을 SQD/QD/RGB 등으로 세분. 멱등.

배경: TCL은 CES 2026에서 **SQD Mini-LED**(Super Quantum Dot + CSOT UltraColor Filter,
100% BT.2020, Color Crosstalk 없음)를 플래그십 전략으로, **RGB Mini-LED**(개별 RGB LED, RM9L)를
별도 라인으로 포지셔닝. 삼성 Micro RGB·하이센스 UR/UX(玲珑)도 RGB Mini-LED 진영.
(참고: ubiresearchnet TCL CES 2026 SQD vs RGB Mini-LED, us.tcl.com/techradar/tomsguide 2026)

분류값: SQD-Mini-LED · QD-Mini-LED · RGB-Mini-LED · Mini-LED · FALD · edge-lit · direct-LED · self-emissive(OLED)

실행: ./.venv/bin/python -m scripts.load_backlight_tech
"""
from __future__ import annotations
import os
import psycopg

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")

# 모델코드 → 명시 분류(마케팅/기술 근거)
EXPLICIT: dict[str, str] = {
    # TCL SQD Mini-LED (2026 플래그십 전략: Super Quantum Dot + UltraColor Filter)
    "X11L": "SQD-Mini-LED", "QM8L": "SQD-Mini-LED", "QM7L": "SQD-Mini-LED",
    "Q9MPro": "SQD-Mini-LED",                                 # TCL 2026 중국 SQD 플래그십(3552존, 5000nit XDR)
    "T7MUltra": "SQD-Mini-LED", "T7MPro": "SQD-Mini-LED",     # TCL 2026 중국 SQD 보급형(2176/1152존)
    # TCL QD Mini-LED (2025 및 이전: QD-Mini LED)
    "X11K": "QD-Mini-LED", "QM9K": "QD-Mini-LED", "QM8K": "QD-Mini-LED",
    "QM7K": "QD-Mini-LED", "QM6K": "QD-Mini-LED", "QM6L": "QD-Mini-LED",
    "Q10K": "QD-Mini-LED", "QM851G": "QD-Mini-LED", "C855": "QD-Mini-LED", "C845": "QD-Mini-LED",
    # RGB Mini-LED (SQD의 대척점 — 개별 R/G/B LED 백라이트)
    "RM9L": "RGB-Mini-LED",                                   # TCL 2026 RGB
    "R95H": "RGB-Mini-LED", "R85H": "RGB-Mini-LED", "MR95F": "RGB-Mini-LED",  # 삼성 Micro RGB
    "UR9": "RGB-Mini-LED", "UR8": "RGB-Mini-LED", "UX26": "RGB-Mini-LED",     # 하이센스 RGB(2026)
}


def classify(code, panel, dimming):
    if code in EXPLICIT:
        return EXPLICIT[code]
    if panel in ("OLED", "WOLED", "QD-OLED"):
        return "self-emissive(OLED)"
    if panel in ("Mini-LED", "Neo-QLED"):
        return "Mini-LED"
    if panel == "QLED":
        return "FALD" if dimming == "full-array" else "edge-lit"
    if panel == "LED-LCD":
        if dimming == "full-array":
            return "FALD"
        return "direct-LED" if dimming == "none" else "edge-lit"
    if panel == "Micro-LED":
        return "self-emissive(MicroLED)"
    return None


def main():
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()
        cur.execute("""select m.model_id, m.model_code_base, s.panel_tech, m.dimming
                       from model m join series s on m.series_id=s.series_id""")
        n = 0
        for mid, code, panel, dimming in cur.fetchall():
            bt = classify(code, panel, str(dimming) if dimming else None)
            conn.cursor().execute("update model set backlight_tech=%s where model_id=%s", (bt, mid))
            n += 1
        conn.commit()
    print(f"backlight_tech {n}종 재분류.")


if __name__ == "__main__":
    main()
