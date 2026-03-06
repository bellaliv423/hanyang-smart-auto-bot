"""
HY-ON LMS 로그인 자동화 (Playwright)
Phase 1: 한양대 포털 SSO -> HY-ON LMS 접속 -> 과목 대시보드 확인

사용법:
    python scrapers/hyon_login.py              # 브라우저 보이는 모드
    python scrapers/hyon_login.py --headless   # 백그라운드 모드
    python scrapers/hyon_login.py --record     # 녹화 모드 (디버깅)
"""

import asyncio
import argparse
import io
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# Windows cp949 인코딩 문제 해결
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 프로젝트 루트 기준 .env 로드
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / "config" / ".env")

# 설정
PORTAL_LOGIN_URL = "https://portal.hanyang.ac.kr/sso/lgin.do"
LMS_URL = "https://learning.hanyang.ac.kr"
USER_ID = os.getenv("HANYANG_USER_ID", "")
PASSWORD = os.getenv("HANYANG_PASSWORD", "")

# data 폴더 생성
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 과목 설정 로드
COURSES_FILE = PROJECT_ROOT / "config" / "courses.json"


def load_courses():
    """courses.json에서 과목 정보 로드"""
    if COURSES_FILE.exists():
        with open(COURSES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"courses": []}


async def login_portal(page):
    """한양대 포털 SSO 로그인"""
    print("[1/4] 한양대 포털 로그인 페이지 접속...")
    await page.goto(PORTAL_LOGIN_URL, wait_until="networkidle", timeout=30000)

    print(f"[2/4] 로그인 중... (ID: {USER_ID})")

    # 디버깅에서 확인된 정확한 셀렉터
    id_input = page.locator('input#userId')
    pw_input = page.locator('input#password')

    try:
        await id_input.wait_for(state="visible", timeout=5000)
        await pw_input.wait_for(state="visible", timeout=5000)
    except Exception:
        screenshot_path = DATA_DIR / "login_debug.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"   [!] 로그인 폼을 찾을 수 없음! 스크린샷: {screenshot_path}")
        return False

    print("   ID/PW 입력 필드 발견 (userId, password)")
    await id_input.fill(USER_ID)
    await pw_input.fill(PASSWORD)

    # 로그인 버튼 - 녹화에서 확인: fieldset a (aria/로그인[role="link"])
    login_clicked = False
    btn_selectors = [
        'fieldset a',
        'a:has-text("로그인")',
        'text=로그인',
        'button:has-text("로그인")',
    ]

    for sel in btn_selectors:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=1000):
                await btn.click()
                print(f"   로그인 버튼 클릭: {sel}")
                login_clicked = True
                break
        except Exception:
            continue

    if not login_clicked:
        print("   로그인 버튼 못 찾음 -> Enter 키로 폼 제출")
        await pw_input.press("Enter")

    # 로그인 결과 대기
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)

        # "다음에 변경" 비밀번호 변경 팝업 처리
        try:
            cancel_btn = page.locator('#btn_cancel')
            if await cancel_btn.is_visible(timeout=3000):
                await cancel_btn.click()
                print("   비밀번호 변경 팝업 -> '다음에 변경' 클릭")
                await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass  # 팝업 없으면 무시

        # 로그인 성공 확인
        current_url = page.url
        if "lgin.do" in current_url:
            # 아직 로그인 페이지에 있으면 실패 가능성
            screenshot_path = DATA_DIR / "login_result.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"   [?] 아직 로그인 페이지 - 2차 인증이 필요할 수 있음")
            print(f"   스크린샷: {screenshot_path}")

            # 에러 메시지 확인
            error_text = await page.locator('.error, .alert, [class*="err"], [class*="warn"]').first.inner_text() if await page.locator('.error, .alert, [class*="err"], [class*="warn"]').count() > 0 else ""
            if error_text:
                print(f"   에러 메시지: {error_text.strip()[:100]}")

            return False
        else:
            print(f"[3/4] 포털 로그인 성공! -> {current_url[:60]}")
            return True

    except Exception as e:
        print(f"   [!] 로그인 후 로딩 대기 실패: {e}")
        screenshot_path = DATA_DIR / "login_error.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        return False


async def login_lms(page):
    """LMS(api.hanyang.ac.kr) 별도 로그인 처리"""
    current_url = page.url

    # LMS 자체 로그인 페이지인지 확인
    if "api.hanyang.ac.kr" not in current_url and "oauth/login" not in current_url:
        return True  # 이미 로그인됨

    print("   LMS 별도 로그인 필요 (api.hanyang.ac.kr)")

    # LMS 로그인 폼 - 디버깅에서 확인된 정확한 셀렉터
    # ID: input#uid, PW: input#upw, 버튼: button#login_btn
    id_input = page.locator('input#uid')
    pw_input = page.locator('input#upw')

    try:
        await id_input.wait_for(state="visible", timeout=5000)
        await pw_input.wait_for(state="visible", timeout=5000)
    except Exception:
        print("   [!] LMS 로그인 폼을 찾을 수 없음")
        return False

    await id_input.fill(USER_ID)
    await pw_input.fill(PASSWORD)

    # 로그인 버튼 클릭
    login_btn = page.locator('button#login_btn')
    try:
        await login_btn.click()
        print("   LMS 로그인 버튼 클릭 (button#login_btn)")
    except Exception:
        await pw_input.press("Enter")
        print("   LMS Enter 키로 로그인")

    await page.wait_for_load_state("networkidle", timeout=15000)
    print(f"   LMS 로그인 후 URL: {page.url[:80]}")
    return True


async def navigate_to_lms(page, context):
    """포털에서 HY-ON LMS로 이동"""
    print("[4/4] HY-ON LMS 접속 중...")

    # 직접 LMS URL로 이동
    await page.goto(LMS_URL, wait_until="networkidle", timeout=30000)
    current_url = page.url
    print(f"   LMS URL: {current_url[:80]}")

    # LMS 자체 로그인이 필요한 경우
    if "login" in current_url.lower() or "oauth" in current_url.lower():
        lms_login_ok = await login_lms(page)
        if not lms_login_ok:
            screenshot_path = DATA_DIR / "lms_login_fail.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"   [!] LMS 로그인 실패 - 스크린샷: {screenshot_path}")
            return False

        # 로그인 후 리다이렉트 대기
        await asyncio.sleep(2)
        current_url = page.url
        print(f"   LMS 로그인 후: {current_url[:80]}")

        # 아직 learning.hanyang.ac.kr이 아니면 직접 이동
        if "learning.hanyang.ac.kr" not in current_url:
            await page.goto(LMS_URL, wait_until="networkidle", timeout=30000)

    # 대시보드 로딩 대기
    await asyncio.sleep(3)
    screenshot_path = DATA_DIR / "lms_dashboard.png"
    await page.screenshot(path=str(screenshot_path), full_page=True)
    print(f"   LMS 스크린샷: {screenshot_path}")

    # 대시보드 확인 - 여러 셀렉터 시도
    dashboard_selectors = [
        '.ic-DashboardCard',
        '[class*="DashboardCard"]',
        'text=대시보드',
        'text=Dashboard',
        'a[href*="/courses/"]',
    ]

    for sel in dashboard_selectors:
        try:
            count = await page.locator(sel).count()
            if count > 0:
                print(f"   [OK] LMS 대시보드 접속 성공! ({sel}, {count}개)")
                return True
        except Exception:
            continue

    print(f"   [?] LMS 상태 불확실 - 스크린샷 확인: {screenshot_path}")
    return True  # 스크린샷으로 수동 확인 가능


async def scrape_dashboard(page):
    """대시보드에서 과목 목록 수집"""
    print("\n=== 대시보드 과목 목록 ===")

    # Canvas LMS 과목 링크 찾기
    card_selectors = [
        '.ic-DashboardCard',
        '[class*="DashboardCard"]',
        '.course-list-item',
        'a[href*="/courses/"]',
    ]

    courses_found = []

    for sel in card_selectors:
        try:
            cards = page.locator(sel)
            count = await cards.count()
            if count > 0:
                print(f"   과목 카드 {count}개 발견 (셀렉터: {sel})")
                for i in range(count):
                    card = cards.nth(i)
                    text = (await card.inner_text()).strip().replace('\n', ' ')[:80]
                    href = await card.get_attribute("href") or ""
                    courses_found.append({"text": text, "href": href})
                    print(f"   [{i+1}] {text}")
                break
        except Exception:
            continue

    if not courses_found:
        print("   과목 카드를 자동으로 찾지 못함")
        print("   data/lms_dashboard.png 스크린샷을 확인하세요")

    # 결과 저장
    result_path = DATA_DIR / "courses_found.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(courses_found, f, ensure_ascii=False, indent=2)
    print(f"   결과 저장: {result_path}")

    return courses_found


async def main(headless=False, record=False):
    """메인 실행"""
    if not USER_ID or not PASSWORD:
        print("[!] .env 파일에 HANYANG_USER_ID와 HANYANG_PASSWORD를 설정하세요!")
        print(f"   경로: {PROJECT_ROOT / 'config' / '.env'}")
        sys.exit(1)

    print("=" * 50)
    print("Smart Auto Hanyang Bot - Phase 1: HY-ON Login")
    print("=" * 50)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            slow_mo=500 if not headless else 0,
        )

        context_opts = {
            "viewport": {"width": 1280, "height": 900},
            "locale": "ko-KR",
        }
        if record:
            record_dir = DATA_DIR / "recordings"
            record_dir.mkdir(parents=True, exist_ok=True)
            context_opts["record_video_dir"] = str(record_dir)

        context = await browser.new_context(**context_opts)
        page = await context.new_page()

        try:
            # Step 1-3: 포털 로그인
            login_ok = await login_portal(page)
            if not login_ok:
                print("\n[FAIL] 포털 로그인 실패!")
                print("  -> data/ 폴더의 스크린샷을 확인하세요")
                return

            # Step 4: LMS 이동
            lms_ok = await navigate_to_lms(page, context)
            if lms_ok:
                courses = await scrape_dashboard(page)
                print(f"\n[DONE] Phase 1 완료! {len(courses)}개 과목 발견")
            else:
                print("\n[WARN] LMS 접속 확인 필요 - data/ 스크린샷 확인")

        except Exception as e:
            print(f"\n[ERROR] 오류 발생: {e}")
            screenshot_path = DATA_DIR / "error.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"   에러 스크린샷: {screenshot_path}")
        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HY-ON LMS Login Automation")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--record", action="store_true", help="Record video for debugging")
    args = parser.parse_args()

    asyncio.run(main(headless=args.headless, record=args.record))
