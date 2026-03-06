"""
HY-ON LMS 과목별 스크래핑 (Phase 2)
각 과목의 수업계획서, 게시판, 주차학습, 강의자료실 자동 수집

사용법:
    python scrapers/course_scraper.py                  # 전체 과목 스크래핑
    python scrapers/course_scraper.py --course 196594  # 특정 과목만
    python scrapers/course_scraper.py --headless       # 백그라운드 모드
"""

import asyncio
import argparse
import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import async_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / "config" / ".env")

USER_ID = os.getenv("HANYANG_USER_ID", "")
PASSWORD = os.getenv("HANYANG_PASSWORD", "")

DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

PORTAL_LOGIN_URL = "https://portal.hanyang.ac.kr/sso/lgin.do"
LMS_BASE = "https://learning.hanyang.ac.kr"


def load_courses():
    courses_file = PROJECT_ROOT / "config" / "courses.json"
    with open(courses_file, "r", encoding="utf-8") as f:
        return json.load(f)


async def full_login(page):
    """포털 SSO + LMS 로그인 (Phase 1에서 검증된 플로우)"""
    # Step 1: 포털 로그인
    print("[LOGIN] 포털 SSO 로그인...")
    await page.goto(PORTAL_LOGIN_URL, wait_until="networkidle", timeout=30000)

    await page.locator('input#userId').fill(USER_ID)
    await page.locator('input#password').fill(PASSWORD)

    # 로그인 버튼 (fieldset a)
    try:
        btn = page.locator('fieldset a').first
        if await btn.is_visible(timeout=2000):
            await btn.click()
        else:
            await page.locator('input#password').press("Enter")
    except Exception:
        await page.locator('input#password').press("Enter")

    await page.wait_for_load_state("networkidle", timeout=15000)

    # "다음에 변경" 팝업
    try:
        cancel_btn = page.locator('#btn_cancel')
        if await cancel_btn.is_visible(timeout=3000):
            await cancel_btn.click()
            await page.wait_for_load_state("networkidle", timeout=10000)
            print("   비밀번호 변경 팝업 처리 완료")
    except Exception:
        pass

    print(f"   포털 로그인 완료: {page.url[:60]}")

    # Step 2: LMS 로그인
    print("[LOGIN] LMS 로그인...")
    await page.goto(LMS_BASE, wait_until="networkidle", timeout=30000)

    if "api.hanyang.ac.kr" in page.url or "oauth/login" in page.url:
        await page.locator('input#uid').fill(USER_ID)
        await page.locator('input#upw').fill(PASSWORD)
        await page.locator('button#login_btn').click()
        await page.wait_for_load_state("networkidle", timeout=15000)

    # LMS 리다이렉트 대기
    await asyncio.sleep(2)

    if "learning.hanyang.ac.kr" in page.url:
        print(f"   LMS 로그인 완료: {page.url[:60]}")
        return True
    else:
        print(f"   [!] LMS 접속 실패: {page.url[:60]}")
        return False


async def scrape_syllabus(page, course_id, course_name):
    """수업 계획서 스크래핑"""
    url = f"{LMS_BASE}/courses/{course_id}/assignments/syllabus"
    print(f"   [수업계획서] {url}")
    await page.goto(url, wait_until="networkidle", timeout=30000)
    await asyncio.sleep(2)

    # 스크린샷
    ss_dir = DATA_DIR / "courses" / str(course_id)
    ss_dir.mkdir(parents=True, exist_ok=True)
    await page.screenshot(path=str(ss_dir / "syllabus.png"), full_page=True)

    # 수업계획서 내용 추출 (iframe 안에 있을 수 있음)
    content = ""
    try:
        # 메인 콘텐츠 영역
        content_area = page.locator('#course_syllabus, .syllabus_content, #content, .ic-Layout-contentMain')
        if await content_area.count() > 0:
            content = await content_area.first.inner_text()
    except Exception:
        pass

    # iframe 내부 콘텐츠도 시도
    if not content:
        for frame in page.frames:
            try:
                frame_content = await frame.locator('body').inner_text()
                if len(frame_content) > 100:
                    content = frame_content
                    break
            except Exception:
                continue

    return {
        "type": "syllabus",
        "url": url,
        "content": content[:5000] if content else "",
        "screenshot": str(ss_dir / "syllabus.png"),
    }


async def scrape_board(page, course_id, course_name):
    """게시판 스크래핑"""
    url = f"{LMS_BASE}/courses/{course_id}/external_tools/132"
    print(f"   [게시판] {url}")
    await page.goto(url, wait_until="networkidle", timeout=30000)
    await asyncio.sleep(3)

    ss_dir = DATA_DIR / "courses" / str(course_id)
    ss_dir.mkdir(parents=True, exist_ok=True)
    await page.screenshot(path=str(ss_dir / "board.png"), full_page=True)

    # iframe 내부 게시글 목록 추출
    posts = []
    for frame in page.frames:
        try:
            # 게시판 글 목록 찾기
            rows = frame.locator('tr, .post-item, .board-item, a[href*="board"]')
            count = await rows.count()
            if count > 1:
                for i in range(min(count, 20)):
                    text = (await rows.nth(i).inner_text()).strip().replace('\n', ' ')[:200]
                    if text and len(text) > 5:
                        posts.append(text)
                break
        except Exception:
            continue

    return {
        "type": "board",
        "url": url,
        "posts": posts[:20],
        "screenshot": str(ss_dir / "board.png"),
    }


async def scrape_weekly(page, course_id, course_name):
    """주차학습 스크래핑"""
    url = f"{LMS_BASE}/courses/{course_id}/external_tools/140"
    print(f"   [주차학습] {url}")
    await page.goto(url, wait_until="networkidle", timeout=30000)
    await asyncio.sleep(3)

    ss_dir = DATA_DIR / "courses" / str(course_id)
    ss_dir.mkdir(parents=True, exist_ok=True)
    await page.screenshot(path=str(ss_dir / "weekly.png"), full_page=True)

    # iframe 내 주차별 학습 콘텐츠
    weeks = []
    for frame in page.frames:
        try:
            items = frame.locator('a, .week-item, .module-item, div[class*="week"], div[class*="Week"]')
            count = await items.count()
            if count > 0:
                for i in range(min(count, 30)):
                    text = (await items.nth(i).inner_text()).strip().replace('\n', ' ')[:200]
                    href = await items.nth(i).get_attribute("href") or ""
                    if text and len(text) > 3:
                        weeks.append({"text": text, "href": href})
                if weeks:
                    break
        except Exception:
            continue

    return {
        "type": "weekly",
        "url": url,
        "weeks": weeks[:30],
        "screenshot": str(ss_dir / "weekly.png"),
    }


async def scrape_materials(page, course_id, course_name):
    """강의자료실 스크래핑"""
    url = f"{LMS_BASE}/courses/{course_id}/external_tools/3"
    print(f"   [강의자료실] {url}")
    await page.goto(url, wait_until="networkidle", timeout=30000)
    await asyncio.sleep(3)

    ss_dir = DATA_DIR / "courses" / str(course_id)
    ss_dir.mkdir(parents=True, exist_ok=True)
    await page.screenshot(path=str(ss_dir / "materials.png"), full_page=True)

    # 강의자료 목록 추출
    materials = []
    for frame in page.frames:
        try:
            items = frame.locator('a, .file-item, tr')
            count = await items.count()
            if count > 0:
                for i in range(min(count, 30)):
                    text = (await items.nth(i).inner_text()).strip().replace('\n', ' ')[:200]
                    href = await items.nth(i).get_attribute("href") or ""
                    if text and len(text) > 3:
                        materials.append({"text": text, "href": href})
                if materials:
                    break
        except Exception:
            continue

    return {
        "type": "materials",
        "url": url,
        "materials": materials[:30],
        "screenshot": str(ss_dir / "materials.png"),
    }


async def scrape_course(page, course):
    """한 과목의 모든 섹션 스크래핑"""
    cid = course["course_id"]
    name = course["name_ko"]
    print(f"\n{'='*50}")
    print(f"[{course['code']}] {name} (ID: {cid})")
    print(f"{'='*50}")

    results = {
        "course_id": cid,
        "code": course["code"],
        "name_ko": name,
        "scraped_at": datetime.now().isoformat(),
    }

    results["syllabus"] = await scrape_syllabus(page, cid, name)
    results["board"] = await scrape_board(page, cid, name)
    results["weekly"] = await scrape_weekly(page, cid, name)
    results["materials"] = await scrape_materials(page, cid, name)

    # 결과 저장
    output_dir = DATA_DIR / "courses" / str(cid)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "scrape_result.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"   결과 저장: {output_file}")

    return results


async def main(headless=False, target_course=None):
    if not USER_ID or not PASSWORD:
        print("[!] .env에 HANYANG_USER_ID, HANYANG_PASSWORD 설정 필요!")
        sys.exit(1)

    config = load_courses()
    courses = config["courses"]

    if target_course:
        courses = [c for c in courses if str(c["course_id"]) == str(target_course)]
        if not courses:
            print(f"[!] Course ID {target_course} 없음")
            sys.exit(1)

    print("=" * 50)
    print(f"Smart Auto Bot - Phase 2: Course Scraping ({len(courses)} courses)")
    print("=" * 50)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            slow_mo=300 if not headless else 0,
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="ko-KR",
        )
        page = await context.new_page()

        try:
            login_ok = await full_login(page)
            if not login_ok:
                print("[FAIL] 로그인 실패!")
                return

            all_results = []
            for course in courses:
                result = await scrape_course(page, course)
                all_results.append(result)

            # 전체 결과 요약 저장
            summary_file = DATA_DIR / "scrape_summary.json"
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump({
                    "scraped_at": datetime.now().isoformat(),
                    "courses_count": len(all_results),
                    "courses": [
                        {
                            "code": r["code"],
                            "name": r["name_ko"],
                            "board_posts": len(r["board"]["posts"]),
                            "weekly_items": len(r["weekly"]["weeks"]),
                            "material_items": len(r["materials"]["materials"]),
                        }
                        for r in all_results
                    ]
                }, f, ensure_ascii=False, indent=2)

            print(f"\n{'='*50}")
            print(f"[DONE] 전체 스크래핑 완료! {len(all_results)}과목")
            print(f"   요약: {summary_file}")
            for r in all_results:
                print(f"   - {r['name_ko']}: 게시판 {len(r['board']['posts'])}건, "
                      f"주차학습 {len(r['weekly']['weeks'])}건, "
                      f"강의자료 {len(r['materials']['materials'])}건")

        except Exception as e:
            print(f"\n[ERROR] {e}")
            await page.screenshot(path=str(DATA_DIR / "scrape_error.png"), full_page=True)
        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HY-ON Course Scraper")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--course", type=str, help="Specific course ID to scrape")
    args = parser.parse_args()

    asyncio.run(main(headless=args.headless, target_course=args.course))
