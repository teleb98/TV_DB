"""
2025–2026 라인업 모델별 제공 사이즈(인치) 적재 — 각 브랜드 공식/신뢰 소스에서 확인(2026-07).
model.size_variants_in(INT[]) 을 채운다.

confirmed=False(공식 사이즈 확인 불가·모델코드 대응 불명확)는 model.estimated_fields 에
'size_variants_in' 을 추가해 표기한다. confirmed=True 면 제거한다. 오디오 추정 플래그는 보존.

각 항목 주석 = 근거 소스. 실행: ./.venv/bin/python -m scripts.load_sizes
"""
from __future__ import annotations
import os
import psycopg

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")
SIZE_FLAG = "size_variants_in"

# code: (sizes, confirmed, source)
SIZES: dict[str, tuple[list[int], bool, str]] = {
    # --- 삼성 2025 (samsung.com 제품페이지) ---
    "QN90F":  ([43, 50, 55, 65, 75, 85, 98, 115], True,  "samsung.com US 개별 제품페이지(50/55/65/75/98/115) + 43/85"),
    "QN990F": ([65, 75, 85, 98],                  True,  "samsung.com US Neo QLED 8K 제품페이지"),
    "S95F":   ([55, 65, 77, 83],                  True,  "samsung.com US OLED(83 rollout)"),
    "S90F":   ([42, 48, 55, 65, 77, 83],          True,  "samsung.com US / newsroom(42~83)"),
    "QN85F":  ([55, 65, 75, 85],                  True,  "samsung.com/RTINGS QN85F 55·65·75·85(98 없음 확인)"),
    # --- LG 2025 (lg.com / 뉴스룸) ---
    "G5":     ([55, 65, 77, 83, 97],              True,  "lg.com / lgnewsroom 2025 OLED evo"),
    "C5":     ([42, 48, 55, 65, 77, 83],          True,  "lg.com C5 제품페이지"),
    "B5":     ([48, 55, 65, 77, 83],              True,  "lg.com / 리뷰 B5"),
    "QNED9M": ([65, 75, 86],                      True,  "lgnewsroom 2025 QNED evo(True Wireless)"),
    # --- Sony 2025 ---
    "XR80II": ([55, 65],                          True,  "BRAVIA 8 II — Sony/RTINGS(55·65만 출시)"),
    "XR50":   ([55, 65, 75, 85, 98],              True,  "BRAVIA 5 — Best Buy/Sony(55~98)"),
    # --- TCL 2025 ---
    "QM8K":   ([65, 75, 85, 98],                  True,  "RTINGS QM8K(65/75/85/98)"),
    "QM7K":   ([55, 65, 75, 85, 98, 115],         True,  "RTINGS QM7K 55·65·75·85·98·115"),
    "QM6K":   ([50, 55, 65, 75, 85, 98],          True,  "RTINGS QM6K + TCL 50·55·65·75·85·98"),
    # --- 추가 누락 모델(2025) ---
    "QM9K":   ([65, 75, 85, 98],                  True,  "us.tcl.com/Tom's Guide QM9K 플래그십 65~98"),
    "QN800F": ([65, 75, 85],                      True,  "samsung Neo QLED 8K QN800F 65/75/85"),
    "S20M2":  ([43, 50, 55, 65, 75],              True,  "RTINGS Sony BRAVIA 2 II(43/50/55/65/75)"),
    "Q7F":    ([43, 50, 55, 65, 75, 85, 98],      True,  "RTINGS Samsung Q7F 2025(43~98)"),
    "LS03F":  ([32, 43, 50, 55, 65, 75, 85],      True,  "samsung The Frame LS03F(32~85)"),
    "UX":     ([100, 116],                        True,  "Hisense UX RGB Mini-LED(100/116)"),
    "QNED85A": ([50, 55, 65, 75, 86, 100],        True,  "RTINGS LG QNED85A 2025(50~100)"),
    "QN80F":  ([55, 65, 75, 85, 100],             True,  "samsung QN80F 2025 Neo QLED 4K(55~100)"),
    "Q8F":    ([43, 50, 55, 65, 75, 85],          True,  "reviews Samsung Q8F 2025(43~85)"),
    "QNED90A": ([55, 65, 75, 86],                 True,  "FlatpanelsHD LG QNED90A(55/65/75/86)"),
    # --- 엔트리·미드 UHD/QLED(2025) ---
    "Q6F":     ([55, 65, 75, 85],                 True,  "reviews Samsung Q6F 엔트리 QLED(55~85)"),
    "U8000F":  ([43, 50, 55, 58, 65, 70, 75, 85], True,  "samsung Crystal UHD U8000F(43~85)"),
    "UA77":    ([50, 55, 65, 75, 86],             True,  "lg.com UA77 UHD(50~86)"),
    "QNED80A": ([50, 55, 65, 75, 86],             False, "lg.com QNED80A(50/75 확인, 세트 추정)"),
    "QD6QF":   ([43, 50, 55, 65, 75, 85, 100],    True,  "Best Buy/Hisense QD6QF Fire TV(43~100)"),
    "S5":      ([43, 50, 55, 58, 65, 75, 85],     True,  "Best Buy/Amazon TCL S5 2025 4K LED(43~85)"),
    "S30II":   ([43, 50, 55, 65, 75, 85, 98],     True,  "Sony BRAVIA 3 II(43~100, 7모델)"),
    # --- 추가 플래그십/누락 모델 ---
    "M5":      ([65, 77, 83, 97],                 True,  "lg.com OLED evo M5 무선(65~97)"),
    "QN95F":   ([55, 65, 75, 85],                 True,  "samsung QN95F 2025 EU 4K 플래그십(55~85)"),
    "LS03FW":  ([65, 75, 85],                     True,  "samsung The Frame Pro LS03FW(65/75/85)"),
    "U9N":     ([75, 85],                         True,  "Hisense U9N 2024 플래그십(75/85)"),
    "QM8L":    ([55, 65, 75, 85, 98],             False, "TCL QM8L 2026 SQD(65 확인, 세트 추정)"),
    "U6N":     ([55, 65, 75, 85],                 True,  "RTINGS Hisense U6N 2024(55~85)"),
    "QN70F":   ([55, 65, 75, 85],                 True,  "RTINGS Samsung QN70F 2025 Edge Mini-LED(55~85)"),
    "XR95II":  ([65, 75, 85, 115],                True,  "Sony BRAVIA 9 II True RGB(65~115)"),
    "XR70II":  ([50, 55, 65, 75, 85, 98],         True,  "Sony BRAVIA 7 II True RGB(50~98)"),
    "QNED92":  ([65, 75, 85, 100, 115],           False, "LG 2026 QNED evo(115/100 확인, 세트 추정)"),
    "R95H":    ([65, 75, 85, 130],                True,  "samsung Micro RGB R95H(65/75/85/130)"),
    "R85H":    ([55, 65, 75, 85, 98],             True,  "samsung Micro RGB R85H(55~98/100)"),
    # --- 2026 중가·엔트리 ---
    "U8000H":  ([43, 50, 55, 58, 65, 70, 75, 85], True,  "samsung Crystal UHD U8000H 2026(43~85)"),
    "LS03H":   ([43, 50, 55, 65, 75, 85, 98],     True,  "samsung The Frame 2026 LS03H(43~98)"),
    "QM7L":    ([55, 65, 75, 85, 98],             True,  "RTINGS TCL QM7L 2026(55~98)"),
    "QM6L":    ([50, 55, 65, 75, 85, 98],         False, "TCL QM6L 2026(FlatpanelsHD 등재, 세트 추정)"),
    "U7SG":    ([55, 65, 75, 85, 100, 116],       False, "hisense-usa U7 2026(U7SG/U7SF, 55~116 세트 추정)"),
    "QNED85B": ([65, 75, 86, 100],                True,  "lg.com 2026 QNED85(65/75/86/100)"),
    # --- 공식 사이트 재확인 추가(2026) ---
    "M70H":    ([43, 50, 55, 65, 75, 85],         True,  "samsung.com Mini LED M70H 2026(43~85)"),
    "M80H":    ([55, 65, 75, 85],                 True,  "samsung.com Mini LED M80H 2026(55~85)"),
    "U6SF":    ([55, 65, 75, 85, 100],            True,  "hisense-usa U6 2026(U6SF Pro, 55~100)"),
    "QNED80B": ([50, 55, 65, 75, 85],             False, "lg.com 2026 QNED80(85 확인, 세트 추정)"),
    # --- 2024 주요 모델 인치(공식/RTINGS 확인) ---
    "QN90D":  ([43, 50, 55, 65, 75, 85, 98],      True,  "samsung QN90D 2024"),
    "QN900D": ([65, 75, 85],                      True,  "samsung QN900D 8K 2024"),
    "QN800D": ([65, 75, 85],                      True,  "samsung QN800D 8K 2024"),
    "QN85D":  ([55, 65, 75, 85],                  True,  "samsung QN85D 2024"),
    "S95D":   ([55, 65, 77],                      True,  "samsung S95D QD-OLED 2024"),
    "S90D":   ([42, 48, 55, 65, 77, 83],          True,  "samsung S90D 2024"),
    "G4":     ([55, 65, 77, 83, 97],              True,  "lg G4 2024"),
    "C4":     ([42, 48, 55, 65, 77, 83],          True,  "lg C4 2024"),
    "B4":     ([48, 55, 65, 77, 83],              True,  "lg B4 2024"),
    "A95L":   ([55, 65, 77],                      True,  "sony A95L QD-OLED"),
    "A80L":   ([55, 65, 77, 83],                  False, "sony A80L(세트 추정)"),
    "X90L":   ([55, 65, 75, 85, 98],              True,  "sony X90L"),
    "XR90":   ([65, 75, 85],                      True,  "sony BRAVIA 9(2024)"),
    "XR80":   ([55, 65, 77],                      True,  "sony BRAVIA 8(2024)"),
    "XR70":   ([55, 65, 75, 85],                  False, "sony BRAVIA 7(세트 추정)"),
    "QM851G": ([65, 75, 85, 98, 115],             True,  "tcl QM8 2024(QM851G)"),
    "C855":   ([65, 75, 85, 98],                  True,  "tcl C855 2024"),
    "C845":   ([55, 65, 75, 85, 98],              False, "tcl C845(세트 추정)"),
    "U8N":    ([55, 65, 75, 85, 100],             True,  "hisense U8N 2024"),
    "U7N":    ([55, 65, 75, 85, 100],             False, "hisense U7N(세트 추정)"),
    "U6N":    ([50, 55, 65, 75, 85],              False, "hisense U6N(세트 추정)"),
    # --- Hisense 2025 ---
    "U8Q":    ([55, 65, 75, 85, 100],             True,  "RTINGS U8QG(55/65/75/85/100)"),
    "U7Q":    ([55, 65, 75, 85, 100],             True,  "RTINGS U75QG 55·65·75·85·100"),
    "U6Q":    ([55, 65, 75, 85, 100],             False, "Hisense 2025(범위 확인, 세트 추정)"),
    # --- Huawei 2025 (중국시장, DB 코드=큐레이션이라 실제 네이밍과 대응 불명확 → 미확정) ---
    "VisionX":  ([65, 75, 85, 98],                False, "Huawei Mini-LED 플래그십 계열 추정(코드 대응 미확정)"),
    "Vision5":  ([55, 65, 75, 85],                False, "Huawei Vision 5 계열 추정"),
    "VisionSE": ([55, 65, 75],                    True,  "Huawei Vision Smart Screen 5 SE(Mini-LED 240Hz, 55/65/75)"),
    # --- Xiaomi 2025 ---
    "S-MiniLED": ([65, 75, 85, 100],              True,  "Xiaomi S Pro Mini LED 2025 65·75·85·100(확인)"),
    "S-OLED":    ([55, 65, 77],                   False, "Xiaomi OLED 글로벌 확인 제한(추정)"),
    "A-Pro":     ([43, 50, 55, 65, 75, 85],       False, "Xiaomi A 계열 추정"),
    # --- LG 2026 (CES 2026) ---
    "G6":     ([55, 65, 77, 83, 97],              True,  "lg.com CES2026 / FlatpanelsHD"),
    "C6":     ([42, 48, 55, 65, 77, 83],          True,  "lg.com CES2026 C6"),
    "B6":     ([48, 55, 65, 77, 83],              True,  "lg.com/Best Buy B6 48·55·65·77·83"),
    # --- 삼성 2026 (코드 정정: G→실제 H, QN90은 2026 단종→QN80H. OLED 라인 S99/S95/S90/S85) ---
    "QN990H": ([85, 98],                          True,  "samsung.com US QN990H — 2026 유일 8K(85·98)"),
    "S99H":   ([55, 65, 77, 83],                  True,  "samsung.com/Gizmochina S99H 2026 프리미엄(QD-OLED 55~77, 83=WOLED)"),
    "S95H":   ([55, 65, 75, 83],                  True,  "samsung.com US S95H 2026 QD-OLED 플래그십"),
    "S90H":   ([42, 48, 55, 65, 77, 83],          True,  "samsung.com US S90H 2026 OLED(42~83)"),
    "S85H":   ([48, 55, 65, 77, 83],              True,  "samsung.com US S85H 2026 WOLED(48~83)"),
    "QN80H":  ([55, 65, 75, 85, 100],             True,  "samsung.com US QN80H 55·65·75·85·100(2026 4K 최상위, QN90 단종)"),
    "QN70H":  ([43, 50, 55, 65, 75, 85],          True,  "samsung.com US QN70H 2026 Neo QLED 4K(43~85)"),
}


def main():
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()
        applied = flagged = missing = 0
        for code, (sizes, confirmed, _src) in SIZES.items():
            cur.execute("select model_id, estimated_fields from model where model_code_base=%s", (code,))
            row = cur.fetchone()
            if not row:
                missing += 1
                print(f"  ⏭ DB에 없음: {code}")
                continue
            mid, ef = row
            ef = list(ef or [])
            if confirmed:
                ef = [f for f in ef if f != SIZE_FLAG]
            else:
                if SIZE_FLAG not in ef:
                    ef.append(SIZE_FLAG)
                flagged += 1
            cur.execute("update model set size_variants_in=%s, estimated_fields=%s where model_id=%s",
                        (sizes, sorted(set(ef)), mid))
            applied += 1
        conn.commit()
    print(f"사이즈 적재 {applied}종 (추정표기 {flagged}종, DB미존재 {missing}종).")


if __name__ == "__main__":
    main()
