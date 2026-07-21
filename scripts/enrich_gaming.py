"""
골든셋 gaming_features + connectivity 보강 (규칙 기반, 재현 가능).
게이밍 스펙과 HDMI 2.1 포트 수는 브랜드·티어·주사율에서 신뢰도 높게 도출된다.
특히 HDMI 2.1 개수는 실제 차별점(Sony 2 vs 삼성/LG 4).
없으면 컬럼을 추가하고, 있으면 갱신한다.

실행:  .venv/bin/python scripts/enrich_gaming.py
"""
from __future__ import annotations
import csv
import pathlib

CSV = pathlib.Path(__file__).resolve().parent.parent / "data" / "golden" / "golden_models.csv"

ENTRY = {"DU8000", "QNED80T"}   # HDMI 2.1 없음(엔트리 LCD)


def gaming(brand: str, refresh: int, code: str) -> str:
    rate = f"{refresh}Hz" if refresh else "120Hz"
    if not refresh or refresh < 120:            # 60Hz 패널: VRR 미지원
        return "|".join(["ALLM", rate])
    base = ["VRR", "ALLM", rate]
    base += {
        "삼성": ["FreeSync Premium Pro"],
        "LG": ["G-Sync", "FreeSync", "Dolby Vision Gaming"],
        "Sony": ["Auto HDR Tone Mapping", "Dolby Vision Gaming"],
        "TCL": ["FreeSync Premium Pro", "Game Master"],
        "Hisense": ["FreeSync Premium Pro", "Game Mode Pro"],
    }.get(brand, [])
    return "|".join(base)


def hdmi21(brand: str, code: str) -> int:
    if code in ENTRY:
        return 0
    if brand == "삼성":
        return 4
    if brand == "LG":
        if code.startswith("B") or code.startswith("QNED"):
            return 2
        return 4                                 # G/C 시리즈 4x
    return 2                                      # Sony/TCL/Hisense 2x


def connectivity(brand: str, code: str) -> str:
    n = hdmi21(brand, code)
    parts = [f"HDMI2.1 x{n}"] if n else ["HDMI2.0 x3"]
    parts += ["eARC", "WiFi", "Bluetooth"]
    return "|".join(parts)


def main():
    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    fields = list(rows[0].keys())
    for col in ("gaming_features", "connectivity"):
        if col not in fields:
            fields.append(col)
    for r in rows:
        refresh = int(r["refresh_rate_native"]) if r.get("refresh_rate_native") else 0
        code = r["model_code_base"]
        r["gaming_features"] = gaming(r["brand"], refresh, code)
        r["connectivity"] = connectivity(r["brand"], code)
    with open(CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"gaming_features + connectivity 반영 {len(rows)}행 (컬럼 {len(fields)}개)")


if __name__ == "__main__":
    main()
