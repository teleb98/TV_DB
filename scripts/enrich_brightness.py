"""
골든셋 peak_brightness_nits 보강 (일회성 데이터 편집).
HDR 10% 윈도우 피크 밝기(nits) — RTINGS/리뷰 실측 및 근사치.
model_code_base 로 매칭해 golden_models.csv 의 빈 칸을 채운다.
실행:  .venv/bin/python scripts/enrich_brightness.py
"""
from __future__ import annotations
import csv
import pathlib

CSV = pathlib.Path(__file__).resolve().parent.parent / "data" / "golden" / "golden_models.csv"

# model_code_base → HDR 10% 피크 밝기(nits). 검색 확인값 위주 + 동급 근사치.
BRIGHT = {
    # 삼성 2024/2023
    "QN900D": 2200, "QN800D": 1600, "QN90D": 2500, "QN85D": 1400, "S95D": 1900,
    "S90D": 1000, "DU8000": 500, "QN95C": 2000, "S95C": 1350,
    # 삼성 2025
    "QN990F": 2300, "QN90F": 2100, "QN85F": 1500, "S95F": 2132, "S90F": 1300,
    # LG
    "G4": 1500, "C4": 1065, "B4": 650, "QNED90T": 1500, "QNED80T": 500, "G3": 1450, "C3": 800,
    "G5": 2295, "C5": 1180, "B5": 700, "QNED9M": 1500,
    # Sony
    "XR90": 2300, "XR80": 1300, "XR70": 1700, "A95L": 1300, "A80L": 1300, "X90L": 1300,
    "XR80II": 2100, "XR50": 2000,
    # TCL
    "QM851G": 3000, "C855": 2500, "C845": 2000, "QM8K": 3035, "QM7K": 2000, "QM6K": 1300,
    # Hisense
    "U8N": 2600, "U7N": 1500, "U6N": 600, "U8K": 1500, "U8Q": 3200, "U7Q": 2000, "U6Q": 1000,
}


def main():
    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    fields = rows[0].keys()
    filled = miss = 0
    for r in rows:
        v = BRIGHT.get(r["model_code_base"])
        if v is not None:
            r["peak_brightness_nits"] = str(v)
            filled += 1
        else:
            miss += 1
            print("  ⏭ 밝기 미정:", r["brand"], r["model_code_base"])
    with open(CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(fields))
        w.writeheader()
        w.writerows(rows)
    print(f"peak_brightness_nits 채움 {filled}행 / 미정 {miss}행")


if __name__ == "__main__":
    main()
