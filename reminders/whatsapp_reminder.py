"""
Phase 4: WhatsApp 수업 리마인더
수업 전 30분, 당일 아침 요약, 주간 일정 알림

사용법:
    python reminders/whatsapp_reminder.py              # 데몬 모드 (상시 실행)
    python reminders/whatsapp_reminder.py --now         # 즉시 오늘 알림 발송
    python reminders/whatsapp_reminder.py --weekly      # 주간 일정 발송
    python reminders/whatsapp_reminder.py --test        # 테스트 메시지 발송
"""

import argparse
import io
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import schedule
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / "config" / ".env")

WHATSAPP_URL = os.getenv("WHATSAPP_GATEWAY_URL", "http://localhost:3000")
WHATSAPP_TARGET = os.getenv("WHATSAPP_TARGET", "")
REMINDER_MINUTES = int(os.getenv("REMINDER_BEFORE_CLASS_MINUTES", "30"))

# 요일 매핑
DAY_MAP = {
    "월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6
}


def load_courses():
    with open(PROJECT_ROOT / "config" / "courses.json", "r", encoding="utf-8") as f:
        return json.load(f)


def send_whatsapp(message):
    """WhatsApp 메시지 발송 (OpenClaw gateway)"""
    try:
        # OpenClaw npx 명령어 방식
        import subprocess
        result = subprocess.run(
            [
                "npx", "openclaw", "message", "send",
                "--channel", "whatsapp",
                "--target", WHATSAPP_TARGET,
                "--message", message,
                "--json"
            ],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT)
        )
        if result.returncode == 0:
            print(f"   [OK] WhatsApp 발송 완료")
            return True
        else:
            print(f"   [!] OpenClaw 실패: {result.stderr[:100]}")
    except Exception as e:
        print(f"   [!] OpenClaw 사용 불가: {e}")

    # 대안: HTTP API 직접 호출
    try:
        resp = httpx.post(
            f"{WHATSAPP_URL}/api/sendText",
            json={"chatId": f"{WHATSAPP_TARGET.replace('+','')}@c.us", "text": message},
            timeout=10
        )
        if resp.status_code == 200:
            print(f"   [OK] WhatsApp HTTP API 발송 완료")
            return True
    except Exception as e:
        print(f"   [!] HTTP API 실패: {e}")

    print(f"   [FALLBACK] 콘솔 출력:\n{message}")
    return False


def get_today_classes():
    """오늘 수업 목록 반환"""
    config = load_courses()
    today_weekday = datetime.now().weekday()  # 0=월, 5=토
    today_classes = []

    for course in config["courses"]:
        day_str = course["schedule"].get("day", "")
        if day_str and DAY_MAP.get(day_str) == today_weekday:
            today_classes.append(course)

    # 시간순 정렬
    today_classes.sort(key=lambda c: c["schedule"].get("time", ""))
    return today_classes


def morning_summary():
    """아침 일일 수업 요약 (08:00 발송)"""
    classes = get_today_classes()
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d (%a)")

    if not classes:
        msg = f"[한양 스마트 오토] {date_str}\n\n오늘은 수업이 없어요! 쉬는 날~"
    else:
        msg = f"[한양 스마트 오토] {date_str}\n\n오늘 수업 {len(classes)}개:\n"
        for i, c in enumerate(classes, 1):
            s = c["schedule"]
            msg += f"\n{i}. {c['name_ko']}"
            msg += f"\n   {s['time']} | {s['room']}"
            msg += f"\n   LMS: {c['lms_url']}"

        msg += f"\n\n수업 {REMINDER_MINUTES}분 전에 다시 알려드릴게요!"

    print(f"\n[아침 요약] {date_str} - {len(classes)}과목")
    send_whatsapp(msg)


def class_reminder(course):
    """수업 시작 전 리마인더"""
    s = course["schedule"]
    name = course["name_ko"]
    name_en = course.get("name_en", "")

    # 학습 노트가 있으면 핵심 내용 포함
    notes_dir = PROJECT_ROOT / "data" / "study_notes"
    cid = course["course_id"]
    tip = ""

    # 최신 예습 자료 확인
    preview_files = sorted(notes_dir.glob(f"{cid}_preview_*.md"), reverse=True)
    if preview_files:
        with open(preview_files[0], "r", encoding="utf-8") as f:
            content = f.read()
            # 핵심 개념 부분만 추출 (처음 300자)
            if "핵심 개념" in content:
                start = content.index("핵심 개념")
                tip = "\n\n[예습 포인트]\n" + content[start:start+300].strip()

    msg = f"[수업 알림] {name}\n"
    msg += f"({name_en})\n\n"
    msg += f"시간: {s['time']}\n"
    msg += f"장소: {s['room']}\n"
    msg += f"LMS: {course['lms_url']}\n"
    msg += f"\n{REMINDER_MINUTES}분 후 수업 시작!"
    if tip:
        msg += tip

    print(f"\n[수업 알림] {name} - {s['time']}")
    send_whatsapp(msg)


def weekly_schedule():
    """주간 시간표 요약 (일요일 저녁 또는 수동 실행)"""
    config = load_courses()
    now = datetime.now()

    # 이번 주 시작일 (월요일)
    monday = now - timedelta(days=now.weekday())

    msg = f"[한양 MBA 주간 시간표]\n"
    msg += f"{monday.strftime('%m/%d')} ~ {(monday + timedelta(days=6)).strftime('%m/%d')}\n"
    msg += "=" * 30

    # 요일별 정리
    day_order = ["월", "화", "수", "목", "금", "토", "일"]
    for day in day_order:
        day_courses = [c for c in config["courses"] if c["schedule"].get("day") == day]
        if day_courses:
            day_idx = DAY_MAP[day]
            date = monday + timedelta(days=day_idx)
            msg += f"\n\n{day}요일 ({date.strftime('%m/%d')}):"
            for c in sorted(day_courses, key=lambda x: x["schedule"].get("time", "")):
                s = c["schedule"]
                msg += f"\n  {s['time']} {c['name_ko']} ({s['room']})"

    msg += "\n\n" + "=" * 30
    msg += "\nGood luck this week, Bella!"

    print(f"\n[주간 시간표] 발송")
    send_whatsapp(msg)


def setup_schedule():
    """스케줄 설정 - 아침 요약 + 수업 전 리마인더"""
    config = load_courses()

    # 1. 매일 08:00 아침 요약
    schedule.every().day.at("08:00").do(morning_summary)
    print("[스케줄] 매일 08:00 아침 수업 요약")

    # 2. 일요일 20:00 주간 시간표
    schedule.every().sunday.at("20:00").do(weekly_schedule)
    print("[스케줄] 매주 일요일 20:00 주간 시간표")

    # 3. 수업별 리마인더 (수업 시작 30분 전)
    for course in config["courses"]:
        day = course["schedule"].get("day", "")
        time_str = course["schedule"].get("time", "")
        if not day or not time_str:
            continue

        # 시작 시간에서 30분 빼기
        start_time = time_str.split("-")[0]
        hour, minute = map(int, start_time.split(":"))
        reminder_dt = datetime(2026, 1, 1, hour, minute) - timedelta(minutes=REMINDER_MINUTES)
        reminder_time = reminder_dt.strftime("%H:%M")

        day_map_schedule = {
            "월": schedule.every().monday,
            "화": schedule.every().tuesday,
            "수": schedule.every().wednesday,
            "목": schedule.every().thursday,
            "금": schedule.every().friday,
            "토": schedule.every().saturday,
            "일": schedule.every().sunday,
        }

        if day in day_map_schedule:
            day_map_schedule[day].at(reminder_time).do(class_reminder, course)
            print(f"[스케줄] {day}요일 {reminder_time} - {course['name_ko']} 리마인더")


def main():
    parser = argparse.ArgumentParser(description="Hanyang WhatsApp Class Reminder")
    parser.add_argument("--now", action="store_true", help="Send today's summary now")
    parser.add_argument("--weekly", action="store_true", help="Send weekly schedule now")
    parser.add_argument("--test", action="store_true", help="Send test message")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon (default)")
    args = parser.parse_args()

    print("=" * 50)
    print("Hanyang Smart Auto - WhatsApp Reminder (Phase 4)")
    print("=" * 50)

    if args.test:
        send_whatsapp("[테스트] 한양 스마트 오토 학업봇 WhatsApp 연동 테스트!")
        return

    if args.now:
        morning_summary()
        return

    if args.weekly:
        weekly_schedule()
        return

    # 데몬 모드
    setup_schedule()
    print(f"\n[RUNNING] 리마인더 데몬 시작! (Ctrl+C로 종료)")
    print(f"   WhatsApp: {WHATSAPP_TARGET}")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
