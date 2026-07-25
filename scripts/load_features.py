"""
브랜드 마케팅 feature(스펙 외) 적재 — 각 브랜드 공식 제품페이지 노출 '순서'대로. 멱등.

rank=1 이 제품페이지 최상단(브랜드가 가장 앞세우는 기능)=가장 중요. WebSearch(2026-07)로
각 브랜드 도메인(samsung.com·lg.com·tcl.com·hisense-usa.com) 제품페이지 하이라이트 순서 확인.
※ Sony는 sony.com 크롤 차단 → Sony 마케팅 표기 순서(source=sony-marketing).

실행: ./.venv/bin/python -m scripts.load_features
"""
from __future__ import annotations
import os
import psycopg

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")

# code: (source, [feature 순서대로 — 앞이 상단/가장 중요])
FEATURES: dict[str, tuple[str, list[str]]] = {
    "QN90F": ("samsung.com", [
        "Samsung Vision AI", "Glare Free 반사방지", "Quantum Mini LED Pro(Quantum Matrix Plus)",
        "NQ4 AI Gen3 프로세서·4K AI Upscaling Pro", "Motion Xcelerator 165Hz",
        "Neo Quantum HDR+", "Object Tracking Sound+·Gaming Hub"]),
    "S95F":  ("samsung.com", [
        "Samsung Vision AI", "역대 최고 밝기 OLED·OLED HDR Pro", "OLED Glare Free",
        "NQ4 AI Gen3 프로세서", "Motion Xcelerator 165Hz",
        "Click to Search·Live Translate", "Infinity One Design·One Connect"]),
    "G5":    ("lg.com", [
        "Brightness Booster Ultimate(최대 +45%)", "α11 AI 프로세서 Gen2", "Perfect Black(OLED evo)",
        "4K 165Hz VRR(G-Sync·FreeSync Premium)", "webOS 25(350+ 채널·클라우드 게이밍)",
        "One Wall Design", "Dolby Vision·Dolby Atmos"]),
    "QM8K":  ("tcl.com", [
        "5000nit·Precise Dimming(5000+ 존, 30M:1)", "Halo Control(Micro-OD)",
        "Audio by Bang & Olufsen", "4K 144Hz·288 VRR 게이밍", "AiPQ Pro 프로세서",
        "QD-Mini LED·QLED Color", "Google TV"]),
    "U8Q":   ("hisense-usa.com", [
        "MiniLED Pro·5000nit 피크", "QLED Color(10억+ 색)", "Full Array Local Dimming(무헤일로)",
        "165Hz 네이티브", "Anti-Glare Low Reflection Pro", "Dolby Atmos 82W 4.1.2ch", "Google TV"]),
    "XR80II": ("sony-marketing", [
        "XR 프로세서", "QD-OLED 최대 밝기·색재현", "Perfect for PlayStation 5(Auto HDR Tone Mapping)",
        "Acoustic Surface Audio+", "Studio Calibrated 모드(Netflix·Prime)", "Google TV·BRAVIA"]),
}


def main():
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()
        rows = 0
        for code, (source, feats) in FEATURES.items():
            cur.execute("select model_id from model where model_code_base=%s", (code,))
            r = cur.fetchone()
            if not r:
                print(f"  ⏭ DB에 없음: {code}")
                continue
            mid = r[0]
            cur.execute("delete from model_feature where model_id=%s", (mid,))  # 재적재 시 순서 재정렬
            for i, feat in enumerate(feats, start=1):
                cur.execute("""insert into model_feature(model_id, rank, feature, source)
                               values (%s,%s,%s,%s)""", (mid, i, feat, source))
                rows += 1
        conn.commit()
    print(f"model_feature {rows}건 적재(모델 {len(FEATURES)}종, 우선순위 순).")


if __name__ == "__main__":
    main()
