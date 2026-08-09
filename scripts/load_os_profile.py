"""
스마트TV OS 플랫폼 프로파일(os_platform) 적재 — OS 자체의 장점·약점·사양. 멱등(PK upsert).

개별 model 스펙과 분리된 "OS 플랫폼" 특성(음성비서·무료채널·클라우드게임·캐스팅·AirPlay·
스마트홈·업데이트 정책·광고 강도 + 장점/약점/추천대상). 브랜드-OS 매핑은 series.os 로 조인.

값 출처(2026-08): 각 벤더 공식 사양 + TechRadar/Tom's Guide OS 비교 리뷰(2025~2026).
실행: ./.venv/bin/python -m scripts.load_os_profile
"""
from __future__ import annotations
import os
import psycopg

DSN = os.environ.get("PG_DSN", "postgresql://localhost/tvspec")

SRC_TR = "https://www.techradar.com/televisions/best-smart-tv-platform-tizen-webos-google-tv-fire-tv-and-roku-compared-tested-and-ranked"

# 컬럼: os, vendor, base_os, ui_current, app_store, app_scale, voice_assistant, fast_service,
#       casting, airplay, cloud_gaming, smart_home, matter, update_policy, ad_level,
#       strengths[], weaknesses[], best_for, source_url
ROWS: list[tuple] = [
    ("Tizen", "Samsung", "Linux(Tizen)", "Tizen 9.0(Quick Menu)",
     "Samsung Apps", "대(주요 스트리밍 총망라)", "Bixby + Alexa",
     "Samsung TV Plus", "Tap View/미러링(Chromecast 미지원)", True,
     "Gaming Hub(Xbox·GeForce Now·Amazon Luna, 콘솔 없이 클라우드)",
     "SmartThings 허브(Zigbee/Thread 내장 모델)", True,
     "OS 7년 보안·기능 업데이트(2024년형~)", "med",
     ["콘솔 없이 클라우드 게임(Gaming Hub)", "SmartThings 스마트홈 허브 내장", "AirPlay 2·모든 주요 앱 지원",
      "장기 업데이트(7년)", "Vision AI 온디바이스 기능"],
     ["Bixby 음성인식 경쟁력 약함", "통합검색 정확도 Google/Roku 대비 미흡", "홈화면 광고 존재"],
     "삼성 갤럭시·SmartThings 생태계, 콘솔 없이 클라우드 게임 원하는 사용자", SRC_TR),

    ("webOS", "LG", "Linux(webOS)", "webOS 25(Re:New)",
     "LG Content Store", "대", "ThinQ + Google Assistant/Alexa(내장 마이크)",
     "LG Channels", "미러링·AirPlay(Chromecast 미지원)", True,
     "Gaming Portal(GeForce Now·Xbox Cloud·Luna)",
     "LG ThinQ + Matter/HomeKit", True,
     "webOS Re:New — 구모델도 5년 UI 업그레이드 제공", "med",
     ["Magic Remote 포인터·직관 UX", "AirPlay 2 + HomeKit 동시지원", "Gaming Portal 클라우드 게임",
      "구모델 5년 업그레이드(Re:New)", "화질 중심 세밀한 설정"],
     ["홈화면 광고 증가 추세", "일부 니치 앱 부족", "저사양 모델 반응속도 편차"],
     "포인터 리모컨 선호, Apple(AirPlay/HomeKit) 사용자, 화질 마니아", SRC_TR),

    ("Google-TV", "Google", "Android(AOSP)", "Google TV(콘텐츠 애그리게이션)",
     "Google Play Store", "최대(1만+ 앱, 최다)", "Google Assistant/Gemini",
     "Google TV Freeplay(라이브 탭)", "Chromecast 내장(캐스팅 최강)", False,
     "GeForce Now 앱(브라우저·앱 기반)",
     "Google Home + Matter", True,
     "Android TV OS 업데이트(브랜드별 상이, 통상 2~3년)", "med",
     ["최다 앱(Play Store 1만+)", "Chromecast 내장 캐스팅", "서비스 교차 개인화 추천(콘텐츠 애그리게이션)",
      "Google Assistant/Gemini AI", "다수 브랜드(Sony·TCL·Hisense·Xiaomi 등) 채택"],
     ["저사양 하드웨어에서 렉·앱 무거움", "AirPlay 미지원(브랜드별)", "업데이트 기간 브랜드 편차", "프라이버시·광고 데이터 수집"],
     "앱 다양성·캐스팅 중시, Google/Android 생태계 사용자", SRC_TR),

    ("Roku", "Roku", "Linux(Roku OS)", "Roku OS 14(타일형 홈)",
     "Roku Channel Store", "대(5,000+ 채널)", "Roku Voice",
     "The Roku Channel(FAST 최강)", "AirPlay 2·미러링(Chromecast 미지원)", True,
     "미지원(클라우드 게임 없음)",
     "Roku Smart Home(제한적, Matter 허브 아님)", False,
     "정기 OTA 업데이트(모델 무관 최신 UI)", "high",
     ["가장 단순·직관적 UI", "특정 스트리밍사에 치우치지 않는 중립 추천", "저가 하드웨어·빠른 반응",
      "The Roku Channel 무료 콘텐츠 최강", "AirPlay 2 + HomeKit 지원"],
     ["클라우드 게임 미지원", "홈화면 광고 많음(ad-heavy)", "UI 디자인 다소 구식", "스마트홈 허브 기능 약함"],
     "복잡함 없이 쉬운 조작·무료 콘텐츠 중시, 예산형 사용자", SRC_TR),

    ("Fire-TV", "Amazon", "Fire OS(Android fork)", "Fire TV(Ambient Experience)",
     "Amazon Appstore", "중(주요 앱 대응, Play 대비 적음)", "Alexa(핸즈프리 최강)",
     "Amazon Freevee + Fire TV 채널", "Miracast(Chromecast·AirPlay 미지원)", False,
     "Amazon Luna(클라우드 게임)",
     "Alexa 스마트홈 + Matter", True,
     "정기 업데이트, Alexa+ 신기능 지속 배포", "high",
     ["Alexa 핸즈프리 음성 최강", "Amazon Luna 클라우드 게임", "Prime Video·Amazon 생태계 밀착",
      "Fire TV Ambient Experience(대기화면)", "Dialogue Boost 대사 강조"],
     ["홈화면 광고·아마존 콘텐츠 강한 푸시(가장 ad-heavy)", "AirPlay·Chromecast 미지원", "Appstore 앱 수 상대적 부족", "프라이버시·데이터 수집"],
     "Alexa·Prime 중심 아마존 생태계, 핸즈프리 음성 중시 사용자", SRC_TR),

    ("VIDAA", "Hisense", "Linux(VIDAA)", "VIDAA U(경량)",
     "VIDAA App Store", "중(주요 앱 대응)", "VIDAA Voice + Alexa",
     "VIDAA Free(무료 채널)", "미러링(Chromecast 미지원)", True,
     "일부 GeForce Now(모델별)",
     "제한적(스마트홈 허브 아님)", False,
     "정기 보안 업데이트", "med",
     ["가볍고 빠른 부팅·반응", "저가 Hisense TV에 최적화", "AirPlay 2 지원(신모델)", "VIDAA Free 무료 채널"],
     ["앱 카탈로그 상대적으로 작음", "일부 앱 Dolby Vision 미지원 사례", "고급 스마트홈 기능 부족"],
     "가성비 Hisense TV, 가벼운 스트리밍 위주 사용자", SRC_TR),

    ("HarmonyOS", "Huawei", "HarmonyOS(분산형)", "HarmonyOS(멀티스크린 협업)",
     "Huawei AppGallery", "중(중국 중심, GMS 미포함)", "Celia(小艺)",
     "Huawei Video 채널", "멀티스크린 협업·미러링", False,
     "Huawei Cloud Gaming(중국)",
     "Huawei 스마트홈(HarmonyOS 생태계)", False,
     "Huawei 정기 업데이트", "low",
     ["Huawei 기기 간 멀티스크린 협업·끊김없는 연동", "스마트 카메라·화상통화", "분산형 OS로 IoT 연동 강점", "홈화면 광고 적음"],
     ["Google 서비스(GMS) 미지원", "중국 외 앱 생태계 제약(AppGallery)", "글로벌 스트리밍 앱 호환성 편차"],
     "Huawei 스마트폰·IoT 생태계, 중국 내 사용자", SRC_TR),

    ("Android-TV", "Google(구세대)", "Android(AOSP)", "Android TV(구 런처)",
     "Google Play Store", "대", "Google Assistant",
     "라이브 채널(브랜드별)", "Chromecast 내장", False,
     "GeForce Now 앱",
     "Google Home + Matter", True,
     "Google TV로 점진 전환(신규는 Google TV)", "low",
     ["Play Store 앱 다양성", "Chromecast 내장", "Google Assistant"],
     ["Google TV 대비 추천·UI 구식", "신모델은 Google TV로 대체 중", "업데이트 종료 모델 존재"],
     "구형 Sony/TCL/Xiaomi 보유자(신규는 Google TV 권장)", SRC_TR),
]


def main():
    with psycopg.connect(DSN) as conn:
        cur = conn.cursor()
        for r in ROWS:
            cur.execute("""
                insert into os_platform
                    (os, vendor, base_os, ui_current, app_store, app_scale, voice_assistant,
                     fast_service, casting, airplay, cloud_gaming, smart_home, matter,
                     update_policy, ad_level, strengths, weaknesses, best_for, source_url)
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                on conflict (os) do update set
                    vendor=excluded.vendor, base_os=excluded.base_os, ui_current=excluded.ui_current,
                    app_store=excluded.app_store, app_scale=excluded.app_scale,
                    voice_assistant=excluded.voice_assistant, fast_service=excluded.fast_service,
                    casting=excluded.casting, airplay=excluded.airplay, cloud_gaming=excluded.cloud_gaming,
                    smart_home=excluded.smart_home, matter=excluded.matter,
                    update_policy=excluded.update_policy, ad_level=excluded.ad_level,
                    strengths=excluded.strengths, weaknesses=excluded.weaknesses,
                    best_for=excluded.best_for, source_url=excluded.source_url, updated_at=now()
            """, r)
        conn.commit()
        # DB 내 해당 OS 모델 보유 여부 대조
        cur.execute("""
            select p.os, p.ad_level, p.airplay,
                   coalesce(count(distinct m.model_id),0) db_models
            from os_platform p
            left join series s on s.os::text = p.os
            left join model m on m.series_id = s.series_id
            group by p.os, p.ad_level, p.airplay order by db_models desc
        """)
        rows = cur.fetchall()
    print(f"os_platform {len(ROWS)}개 OS 적재.")
    for osn, ad, ap, n in rows:
        print(f"  {osn:11} 모델 {n:3}종  광고 {ad:4}  AirPlay {'O' if ap else 'X'}")


if __name__ == "__main__":
    main()
