"""
브랜드 마케팅 feature(스펙 외) 적재 — 제품페이지 노출 '순서'(rank1=최상단=가장 중요)대로. 멱등.

각 feature 는 category 로 분류:
  picture(화질)·performance(성능)·gaming·sound(음향)·ai·design ·
  **service(스마트TV 서비스: 무료채널·클라우드게임·앱스토어·음성비서 등)** ·
  **experience(사용 경험: Ambient·Art·Multi View·리모컨·대기감상 등)**

출처: 각 브랜드 도메인 제품페이지(2026-07). Sony는 sony.com 크롤차단 → Sony 마케팅 표기.
실행: ./.venv/bin/python -m scripts.load_features
"""
from __future__ import annotations
import os
import psycopg

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")

# code: (source, [(category, feature) 순서대로 — 앞이 상단/가장 중요])
FEATURES: dict[str, tuple[str, list[tuple[str, str]]]] = {
    "QN90F": ("samsung.com", [
        ("ai", "Samsung Vision AI"),
        ("picture", "Glare Free 반사방지"),
        ("picture", "Quantum Mini LED Pro(Quantum Matrix Plus)"),
        ("ai", "NQ4 AI Gen3 프로세서·4K AI Upscaling Pro"),
        ("gaming", "Motion Xcelerator 165Hz·Gaming Hub"),
        ("picture", "Neo Quantum HDR+"),
        ("sound", "Object Tracking Sound+·Q-Symphony·Dolby Atmos"),
        ("service", "Gaming Hub(Xbox·GeForce Now·Luna 클라우드 게임)"),
        ("service", "Samsung TV Plus(무료 채널)"),
        ("service", "SmartThings 홈 허브·Matter"),
        ("service", "Bixby·Alexa 음성 어시스턴트"),
        ("experience", "Ambient Mode(배경 화면)"),
        ("experience", "Multi View(멀티뷰)"),
        ("experience", "Slim One Connect(원커넥트 박스)"),
        ("experience", "SolarCell 리모컨(태양광 충전)")]),
    "S95F": ("samsung.com", [
        ("ai", "Samsung Vision AI"),
        ("picture", "역대 최고 밝기 OLED·OLED HDR Pro"),
        ("picture", "OLED Glare Free"),
        ("ai", "NQ4 AI Gen3 프로세서"),
        ("gaming", "Motion Xcelerator 165Hz·Gaming Hub"),
        ("design", "Infinity One Design·One Connect"),
        ("service", "Gaming Hub(Xbox·GeForce Now·Luna 클라우드 게임)"),
        ("service", "Samsung TV Plus(무료 채널)"),
        ("service", "SmartThings 홈 허브·Matter"),
        ("service", "Bixby·Alexa·Click to Search·Live Translate"),
        ("experience", "Ambient Mode"),
        ("experience", "Multi View"),
        ("experience", "Q-Symphony·Dolby Atmos"),
        ("experience", "SolarCell 리모컨")]),
    "G5": ("lg.com", [
        ("picture", "Brightness Booster Ultimate(최대 +45%)"),
        ("ai", "α11 AI 프로세서 Gen2"),
        ("picture", "Perfect Black(OLED evo)"),
        ("gaming", "4K 165Hz VRR(G-Sync·FreeSync Premium)"),
        ("design", "One Wall Design"),
        ("sound", "Dolby Vision·Dolby Atmos·WOW Orchestra"),
        ("service", "webOS 25(AI 홈·350+ LG Channels 무료)"),
        ("service", "Gaming Portal(GeForce Now·Xbox 클라우드 게임)"),
        ("service", "LG ThinQ·홈 IoT·음성 어시스턴트"),
        ("experience", "Always Ready(대기 감상)"),
        ("experience", "Multi View(멀티뷰)"),
        ("experience", "Magic Remote(포인터·음성)"),
        ("experience", "AI 컨시어지·AI 챗봇")]),
    "QM8K": ("tcl.com", [
        ("picture", "5000nit·Precise Dimming(5000+ 존, 30M:1)"),
        ("picture", "Halo Control(Micro-OD)"),
        ("sound", "Audio by Bang & Olufsen"),
        ("gaming", "4K 144Hz·288 VRR·Game Master"),
        ("ai", "AiPQ Pro 프로세서"),
        ("service", "Google TV(앱·추천)"),
        ("service", "Google Cast·Chromecast 내장"),
        ("service", "Google Assistant 음성"),
        ("experience", "FlexConnect(가변 무선 사운드)"),
        ("experience", "ONKYO 사운드 시스템"),
        ("experience", "제로 베젤 디자인")]),
    "U8Q": ("hisense-usa.com", [
        ("picture", "MiniLED Pro·5000nit 피크"),
        ("picture", "QLED Color·Full Array Local Dimming"),
        ("picture", "Anti-Glare Low Reflection Pro"),
        ("gaming", "165Hz 네이티브·Game Mode Pro·288 VRR"),
        ("sound", "Dolby Atmos 82W 4.1.2ch"),
        ("service", "Google TV(US)·VIDAA(지역별)"),
        ("service", "Google Assistant·Alexa 음성"),
        ("service", "Google Cast 내장"),
        ("experience", "Hi-View Engine 화질 경험"),
        ("experience", "IMAX Enhanced·Filmmaker Mode"),
        ("experience", "와이드 시야각 패널")]),
    "XR80II": ("sony-marketing", [
        ("ai", "XR 프로세서(AI)"),
        ("picture", "QD-OLED 최대 밝기·색재현"),
        ("gaming", "Perfect for PlayStation 5(Auto HDR·Auto Genre)"),
        ("sound", "Acoustic Surface Audio+"),
        ("service", "Google TV(앱·추천)"),
        ("service", "Bravia Core(고화질 스트리밍·영화 크레딧)"),
        ("service", "Netflix·Prime Video Calibrated 모드"),
        ("experience", "Bravia Cam(제스처·화상통화·자동 최적화)"),
        ("experience", "Studio Calibrated 모드"),
        ("experience", "Eco 대시보드")]),
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
            cur.execute("delete from model_feature where model_id=%s", (mid,))
            for i, (cat, feat) in enumerate(feats, start=1):
                cur.execute("""insert into model_feature(model_id, rank, feature, category, source)
                               values (%s,%s,%s,%s,%s)""", (mid, i, feat, cat, source))
                rows += 1
        conn.commit()
    print(f"model_feature {rows}건 적재(모델 {len(FEATURES)}종, category 포함).")


if __name__ == "__main__":
    main()
