"""
인증/에너지(certification) 적재 — EU EPREL 에너지라벨 등. 멱등(model_id upsert).

값은 WebSearch(2026-07)로 확인한 EPREL(EU 에너지효율 등록DB) 데이터.
energy_class=A~G, power=On-mode 소비전력(W, SDR/HDR), eprel_model=EU 정식 SKU(파생명 매핑).
※ EPREL 소비전력은 등록 사이즈 기준(대부분 65", U8Q는 75")이라 사이즈별 차이 있음.
※ FCC ID / RRA(한국 전파인증)는 직접 조회 제약으로 미수집(컬럼만 준비).

실행: ./.venv/bin/python -m scripts.load_certification
"""
from __future__ import annotations
import os
import psycopg

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")

# code: (sdr_class, hdr_class, power_sdr_w, power_hdr_w, eprel_model, note)
CERT: dict[str, tuple] = {
    "S90F":   ("F", "G", 89,   204,  "QE65S90FAT"),    # 65" QD-OLED
    "S95F":   ("F", "G", None, None, "QE65S95FAT"),    # 65"
    "G5":     ("E", "G", 85,   222,  "OLED65G51LW"),   # 65" OLED evo
    "XR80II": ("F", "G", 87,   None, "K-65XR80M2"),    # 65" Bravia 8 II
    "U8Q":    ("D", "G", 85,   None, "75U8QxxUK(EU)"),  # 75" ULED
    "QN90D":  (None, "G", 90,  210,  "QE65QN90DAT"),   # 65" 2024 Neo QLED
}


def main():
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()
        n = 0
        for code, (sdr, hdr, psdr, phdr, eprel) in CERT.items():
            cur.execute("select model_id from model where model_code_base=%s", (code,))
            row = cur.fetchone()
            if not row:
                print(f"  ⏭ DB에 없음: {code}")
                continue
            cur.execute("""
                insert into certification(model_id, energy_class_sdr, energy_class_hdr,
                                          power_sdr_w, power_hdr_w, eprel_model, source)
                values (%s,%s,%s,%s,%s,%s,'eprel')
                on conflict (model_id) do update set
                  energy_class_sdr = excluded.energy_class_sdr,
                  energy_class_hdr = excluded.energy_class_hdr,
                  power_sdr_w = excluded.power_sdr_w,
                  power_hdr_w = excluded.power_hdr_w,
                  eprel_model = excluded.eprel_model,
                  source = 'eprel',
                  updated_at = now()""",
                (row[0], sdr, hdr, psdr, phdr, eprel))
            n += 1
        conn.commit()
    print(f"인증/에너지(certification) {n}종 적재(EPREL).")


if __name__ == "__main__":
    main()
