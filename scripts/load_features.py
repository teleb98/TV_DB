"""
브랜드 마케팅 feature 적재 — 제품페이지 노출 순서(rank1=최상단) + category 분류. 멱등.

category: picture·performance·gaming·sound·ai·design·**service**·**experience**
  service    = 스마트TV 서비스(무료채널·클라우드게임·앱스토어·음성비서 등, 브랜드 공통)
  experience = 사용 경험(Ambient·Art·Multi View·리모컨·대기감상 등)

- CURATED 6종: 각 브랜드 도메인 제품페이지에서 실제 노출 순서 확인(source=도메인).
- 그 외 전 모델: 브랜드 생태계(service/experience는 브랜드 공통) + 패널 아키타입(picture)으로
  자동 생성(source=brand-generic). flagship/high 는 프리미엄 experience 추가.

실행: ./.venv/bin/python -m scripts.load_features
"""
from __future__ import annotations
import os
import psycopg

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")

# ---------- 브랜드 공통: service ----------
BRAND_SERVICE = {
    "삼성": [("service", "Samsung TV Plus(무료 채널)"), ("service", "Gaming Hub(Xbox·GeForce Now·Luna 클라우드 게임)"),
             ("service", "SmartThings 홈 허브·Matter"), ("service", "Bixby·Alexa 음성 어시스턴트")],
    "LG": [("service", "webOS·LG Channels(무료 채널)"), ("service", "Gaming Portal(GeForce Now·Xbox 클라우드)"),
           ("service", "LG ThinQ·음성 어시스턴트")],
    "Sony": [("service", "Google TV(앱·추천)"), ("service", "Bravia Core 고화질 스트리밍"),
             ("service", "Google Assistant·음성 검색")],
    "TCL": [("service", "Google TV"), ("service", "Google Cast(Chromecast 내장)"), ("service", "Google Assistant")],
    "Hisense": [("service", "Google TV/VIDAA/Fire TV"), ("service", "Google Cast·음성 비서")],
    "Huawei": [("service", "HarmonyOS·AppGallery"), ("service", "AI 음성·스마트홈 연동")],
    "Xiaomi": [("service", "Google TV/PatchWall"), ("service", "Google Cast·음성 어시스턴트")],
    "Philips": [("service", "Google TV(Android)"), ("service", "Google Cast·Assistant")],
    "Thomson": [("service", "Google TV"), ("service", "Google Cast·Assistant")],
    "Roku": [("service", "Roku OS·The Roku Channel(무료 채널)"), ("service", "Roku Voice·스마트홈 연동")],
    "Amazon": [("service", "Fire TV·Alexa+ 음성"), ("service", "Prime Video·무료 채널")],
    "Toshiba": [("service", "Fire TV·Alexa 음성"), ("service", "Prime Video·앱스토어")],
    "Panasonic": [("service", "Fire TV·Alexa 음성"), ("service", "My Home Screen 연동")],
    "Sharp": [("service", "Google TV(Android)"), ("service", "Google Cast·Assistant")],
    "Vizio": [("service", "SmartCast·WatchFree+(무료 채널)"), ("service", "Siri·Google Assistant·Alexa 음성")],
}
# ---------- 브랜드 공통: experience(넓게 적용) ----------
BRAND_EXPERIENCE = {
    "삼성": [("experience", "Ambient Mode(배경 화면)"), ("experience", "Multi View(멀티뷰)"),
             ("experience", "Q-Symphony 사운드")],
    "LG": [("experience", "Always Ready(대기 감상)"), ("experience", "Multi View"),
           ("experience", "Magic Remote(포인터·음성)")],
    "Sony": [("experience", "Perfect for PlayStation 5"), ("experience", "Eco 대시보드")],
    "TCL": [("experience", "Game Master"), ("experience", "제로 베젤 디자인")],
    "Hisense": [("experience", "Game Mode Pro"), ("experience", "Filmmaker Mode")],
    "Huawei": [("experience", "스마트 카메라·화상통화"), ("experience", "멀티스크린 협업")],
    "Xiaomi": [("experience", "Xiaomi 생태계 연동"), ("experience", "Game Boost")],
    "Philips": [("experience", "Ambilight(3면 배경조명)"), ("experience", "P5 AI 화질엔진")],
    "Thomson": [("experience", "내장 서브우퍼"), ("experience", "슬림 디자인")],
    "Roku": [("experience", "Roku Smart Picture"), ("experience", "간편 홈스크린·Backlit 음성 리모컨")],
    "Amazon": [("experience", "Fire TV Ambient Experience"), ("experience", "핸즈프리 Alexa·Dialogue Boost")],
    "Toshiba": [("experience", "REGZA Engine ZR·AI 4K 업스케일"), ("experience", "Game Mode")],
    "Panasonic": [("experience", "ThermalFlow 냉각 시스템"), ("experience", "Filmmaker Mode·시네마 색보정")],
    "Sharp": [("experience", "Xtreme Brightness·Deep Chroma QD"), ("experience", "85W 스피커 시스템")],
    "Vizio": [("experience", "SmartCast Home(간편 홈스크린)"), ("experience", "게임 메뉴·저지연 모드")],
}
# ---------- 프리미엄 experience(flagship/high 만) ----------
BRAND_EXP_PREMIUM = {
    "삼성": [("experience", "SolarCell 리모컨(태양광 충전)"), ("experience", "Slim/One Connect")],
    "LG": [("experience", "AI 컨시어지·AI 챗봇")],
    "Sony": [("experience", "Bravia Cam(제스처·화상통화·자동 최적화)")],
    "TCL": [("experience", "FlexConnect(가변 무선 사운드)")],
    "Hisense": [("experience", "IMAX Enhanced·와이드 시야각")],
    "Huawei": [], "Xiaomi": [],
    "Philips": [("experience", "4면 Ambilight·Bowers & Wilkins 사운드")],
    "Thomson": [],
    "Roku": [("experience", "Smart Picture Max·Backlit Voice Remote Pro")],
    "Amazon": [], "Toshiba": [],
    "Panasonic": [("experience", "Primary RGB Tandem 패널·ThermalFlow(Z95B)")],
    "Sharp": [("experience", "2000+ 로컬디밍 존·Harman/Kardon 사운드")],
    "Vizio": [("experience", "FreeSync Premium Pro·4x HDMI 2.1")],
}
# ---------- 브랜드 sound ----------
BRAND_SOUND = {
    "삼성": ("sound", "Object Tracking Sound·Dolby Atmos"), "LG": ("sound", "AI Sound Pro·Dolby Atmos"),
    "Sony": ("sound", "Acoustic Multi Audio·Dolby Atmos"), "TCL": ("sound", "ONKYO·Dolby Atmos"),
    "Hisense": ("sound", "Dolby Atmos"), "Huawei": ("sound", "하이파이 스피커·Dolby Atmos"),
    "Xiaomi": ("sound", "Dolby Atmos"),
    "Philips": ("sound", "Bowers & Wilkins·Dolby Atmos"), "Thomson": ("sound", "Dolby Atmos"),
    "Roku": ("sound", "측면발사 Dolby Atmos·내장 서브우퍼"), "Amazon": ("sound", "Dolby Audio"),
    "Toshiba": ("sound", "Dolby Audio·DTS"),
    "Panasonic": ("sound", "전면 스피커·30W 서브우퍼·Dolby Atmos"),
    "Sharp": ("sound", "85W Harman/Kardon·Dolby Atmos"),
    "Vizio": ("sound", "Dolby Audio"),
}
# ---------- picture: (brand, archetype) ----------
PICTURE = {
    ("삼성", "oled"): [("picture", "OLED HDR Pro·자발광"), ("picture", "OLED Glare Free")],
    ("삼성", "miniled"): [("picture", "Quantum Mini LED·Neo Quantum HDR+"), ("picture", "Quantum Matrix·Glare Free")],
    ("삼성", "qled"): [("picture", "Quantum Dot Color(QLED)")],
    ("삼성", "led"): [("picture", "Crystal Processor 4K·PurColor")],
    ("LG", "oled"): [("picture", "Perfect Black(OLED evo)·자발광"), ("picture", "Brightness Booster")],
    ("LG", "miniled"): [("picture", "Precision Dimming·Dynamic QNED Color")],
    ("LG", "led"): [("picture", "4K UHD·HDR10 Pro")],
    ("Sony", "oled"): [("picture", "XR Triluminos·Perfect Black")],
    ("Sony", "miniled"): [("picture", "XR Backlight Master Drive")],
    ("Sony", "led"): [("picture", "4K Processor·Triluminos Pro")],
    ("TCL", "miniled"): [("picture", "QD-Mini LED·Precise Dimming")],
    ("TCL", "led"): [("picture", "HDR·Dolby Vision")],
    ("Hisense", "miniled"): [("picture", "ULED MiniLED·Full Array Local Dimming"), ("picture", "QLED Color")],
    ("Hisense", "qled"): [("picture", "QLED Quantum Dot Color")],
    ("Hisense", "led"): [("picture", "4K HDR")],
    ("Huawei", "miniled"): [("picture", "Super Mini LED·Honghu 화질")],
    ("Huawei", "led"): [("picture", "4K 화질 엔진")],
    ("Xiaomi", "oled"): [("picture", "OLED 자발광")],
    ("Xiaomi", "miniled"): [("picture", "QD-Mini LED")],
    ("Xiaomi", "led"): [("picture", "4K HDR")],
    ("Philips", "oled"): [("picture", "Primary RGB Tandem OLED / OLED EX"), ("picture", "P5 AI 화질")],
    ("Thomson", "miniled"): [("picture", "Mini LED·Dolby Vision")],
    ("Thomson", "qled"): [("picture", "QLED Quantum Dot")],
    ("Roku", "miniled"): [("picture", "Mini-LED QLED·Full Array Local Dimming"), ("picture", "Roku Smart Picture")],
    ("Roku", "qled"): [("picture", "QLED·4K HDR")],
    ("Amazon", "qled"): [("picture", "QLED·Full Array Local Dimming"), ("picture", "Dolby Vision IQ·HDR10+ Adaptive")],
    ("Amazon", "led"): [("picture", "4K UHD·HDR10")],
    ("Toshiba", "led"): [("picture", "REGZA Engine ZR·4K HDR·Dolby Vision")],
    ("Panasonic", "oled"): [("picture", "HCX Pro AI MK II·4K Remaster Engine"), ("picture", "Master OLED Pro(OLED EX)")],
    ("Sharp", "miniled"): [("picture", "Xtreme Mini LED·Deep Chroma Quantum Dot")],
    ("Vizio", "qled"): [("picture", "Quantum Color·4K HDR")],
}

# ---------- CURATED(공식 페이지 순서 확인 6종) ----------
CURATED: dict[str, tuple[str, list[tuple[str, str]]]] = {
    "QN90F": ("samsung.com", [
        ("ai", "Samsung Vision AI"), ("picture", "Glare Free 반사방지"),
        ("picture", "Quantum Mini LED Pro(Quantum Matrix Plus)"), ("ai", "NQ4 AI Gen3 프로세서·4K AI Upscaling Pro"),
        ("gaming", "Motion Xcelerator 165Hz·Gaming Hub"), ("picture", "Neo Quantum HDR+"),
        ("sound", "Object Tracking Sound+·Q-Symphony·Dolby Atmos"),
        ("service", "Gaming Hub(Xbox·GeForce Now·Luna 클라우드 게임)"), ("service", "Samsung TV Plus(무료 채널)"),
        ("service", "SmartThings 홈 허브·Matter"), ("service", "Bixby·Alexa 음성 어시스턴트"),
        ("experience", "Ambient Mode(배경 화면)"), ("experience", "Multi View(멀티뷰)"),
        ("experience", "Slim One Connect(원커넥트 박스)"), ("experience", "SolarCell 리모컨(태양광 충전)")]),
    "S95F": ("samsung.com", [
        ("ai", "Samsung Vision AI"), ("picture", "역대 최고 밝기 OLED·OLED HDR Pro"), ("picture", "OLED Glare Free"),
        ("ai", "NQ4 AI Gen3 프로세서"), ("gaming", "Motion Xcelerator 165Hz·Gaming Hub"),
        ("design", "Infinity One Design·One Connect"),
        ("service", "Gaming Hub(Xbox·GeForce Now·Luna 클라우드 게임)"), ("service", "Samsung TV Plus(무료 채널)"),
        ("service", "SmartThings 홈 허브·Matter"), ("service", "Bixby·Alexa·Click to Search·Live Translate"),
        ("experience", "Ambient Mode"), ("experience", "Multi View"), ("experience", "Q-Symphony·Dolby Atmos"),
        ("experience", "SolarCell 리모컨")]),
    "G5": ("lg.com", [
        ("picture", "Brightness Booster Ultimate(최대 +45%)"), ("ai", "α11 AI 프로세서 Gen2"),
        ("picture", "Perfect Black(OLED evo)"), ("gaming", "4K 165Hz VRR(G-Sync·FreeSync Premium)"),
        ("design", "One Wall Design"), ("sound", "Dolby Vision·Dolby Atmos·WOW Orchestra"),
        ("service", "webOS 25(AI 홈·350+ LG Channels 무료)"), ("service", "Gaming Portal(GeForce Now·Xbox 클라우드 게임)"),
        ("service", "LG ThinQ·홈 IoT·음성 어시스턴트"), ("experience", "Always Ready(대기 감상)"),
        ("experience", "Multi View(멀티뷰)"), ("experience", "Magic Remote(포인터·음성)"),
        ("experience", "AI 컨시어지·AI 챗봇")]),
    "QM8K": ("tcl.com", [
        ("picture", "5000nit·Precise Dimming(5000+ 존, 30M:1)"), ("picture", "Halo Control(Micro-OD)"),
        ("sound", "Audio by Bang & Olufsen"), ("gaming", "4K 144Hz·288 VRR·Game Master"), ("ai", "AiPQ Pro 프로세서"),
        ("service", "Google TV(앱·추천)"), ("service", "Google Cast·Chromecast 내장"), ("service", "Google Assistant 음성"),
        ("experience", "FlexConnect(가변 무선 사운드)"), ("experience", "ONKYO 사운드 시스템"),
        ("experience", "제로 베젤 디자인")]),
    "U8Q": ("hisense-usa.com", [
        ("picture", "MiniLED Pro·5000nit 피크"), ("picture", "QLED Color·Full Array Local Dimming"),
        ("picture", "Anti-Glare Low Reflection Pro"), ("gaming", "165Hz 네이티브·Game Mode Pro·288 VRR"),
        ("sound", "Dolby Atmos 82W 4.1.2ch"), ("service", "Google TV(US)·VIDAA(지역별)"),
        ("service", "Google Assistant·Alexa 음성"), ("service", "Google Cast 내장"),
        ("experience", "Hi-View Engine 화질 경험"), ("experience", "IMAX Enhanced·Filmmaker Mode"),
        ("experience", "와이드 시야각 패널")]),
    "XR80II": ("sony-marketing", [
        ("ai", "XR 프로세서(AI)"), ("picture", "QD-OLED 최대 밝기·색재현"),
        ("gaming", "Perfect for PlayStation 5(Auto HDR·Auto Genre)"), ("sound", "Acoustic Surface Audio+"),
        ("service", "Google TV(앱·추천)"), ("service", "Bravia Core(고화질 스트리밍·영화 크레딧)"),
        ("service", "Netflix·Prime Video Calibrated 모드"),
        ("experience", "Bravia Cam(제스처·화상통화·자동 최적화)"), ("experience", "Studio Calibrated 모드"),
        ("experience", "Eco 대시보드")]),
}


def archetype(panel: str) -> str:
    if panel in ("OLED", "WOLED", "QD-OLED"):
        return "oled"
    if panel in ("Neo-QLED", "Mini-LED", "Micro-LED"):
        return "miniled"
    if panel == "QLED":
        return "qled"
    return "led"


def generate(brand, panel, tier, processor, refresh):
    feats: list[tuple[str, str]] = []
    feats += PICTURE.get((brand, archetype(panel)), [("picture", "4K HDR")])
    if processor:
        feats.append(("ai", f"{processor} 프로세서"))
    if refresh and refresh >= 120:
        feats.append(("gaming", f"{refresh}Hz·VRR·ALLM 게이밍"))
    feats.append(BRAND_SOUND.get(brand, ("sound", "Dolby Atmos")))
    feats += BRAND_SERVICE.get(brand, [])
    feats += BRAND_EXPERIENCE.get(brand, [])
    if tier in ("flagship", "high"):
        feats += BRAND_EXP_PREMIUM.get(brand, [])
    return feats


def main():
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()
        cur.execute("""select m.model_id, m.model_code_base, b.name brand, s.panel_tech, s.tier,
                              m.processor, m.refresh_rate_native
                       from model m join series s on m.series_id=s.series_id
                       join brand b on s.brand_id=b.brand_id""")
        models = cur.fetchall()
        curated_n = gen_n = rows = 0
        for mid, code, brand, panel, tier, proc, refresh in models:
            if code in CURATED:
                source, feats = CURATED[code]
                curated_n += 1
            else:
                source, feats = "brand-generic", generate(brand, panel, tier, proc, refresh)
                gen_n += 1
            ins = conn.cursor()
            ins.execute("delete from model_feature where model_id=%s", (mid,))
            for i, (cat, feat) in enumerate(feats, start=1):
                ins.execute("""insert into model_feature(model_id, rank, feature, category, source)
                               values (%s,%s,%s,%s,%s)""", (mid, i, feat, cat, source))
                rows += 1
        conn.commit()
    print(f"model_feature {rows}건 적재 — CURATED {curated_n}종(공식순서) + 생성 {gen_n}종(brand-generic).")


if __name__ == "__main__":
    main()
