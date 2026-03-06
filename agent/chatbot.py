"""
한양 스마트 오토 학업 챗봇
터미널 또는 WhatsApp에서 대화형 학업 비서 역할

사용법:
    python agent/chatbot.py                  # 터미널 대화 모드
    python agent/chatbot.py --whatsapp       # WhatsApp 연동 모드 (OpenClaw)
"""

import anthropic
import argparse
import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / "config" / ".env")

API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


def load_system_prompt():
    """IDENTITY.md + 과목 정보로 시스템 프롬프트 구성"""
    identity_path = PROJECT_ROOT / "agent" / "IDENTITY.md"
    courses_path = PROJECT_ROOT / "config" / "courses.json"

    system = ""
    if identity_path.exists():
        with open(identity_path, "r", encoding="utf-8") as f:
            system = f.read()

    if courses_path.exists():
        with open(courses_path, "r", encoding="utf-8") as f:
            courses = json.load(f)
        courses_str = json.dumps(courses, ensure_ascii=False, indent=2)
        # surrogate 문자 제거
        courses_str = courses_str.encode("utf-8", errors="replace").decode("utf-8")
        system += f"\n\n## Course Data (JSON)\n```json\n{courses_str}\n```"

    # 오늘 날짜 + 요일
    now = datetime.now()
    day_names = ["월", "화", "수", "목", "금", "토", "일"]
    system += f"\n\n## Current Time\n- 날짜: {now.strftime('%Y-%m-%d')} ({day_names[now.weekday()]}요일)"
    system += f"\n- 시간: {now.strftime('%H:%M')}"

    # 학습 노트 요약
    notes_dir = PROJECT_ROOT / "data" / "study_notes"
    if notes_dir.exists():
        notes = list(notes_dir.glob("*.md"))
        if notes:
            system += f"\n\n## Available Study Notes ({len(notes)} files)\n"
            for n in sorted(notes):
                system += f"- {n.name}\n"

    # 전체 시스템 프롬프트 인코딩 정리
    return system.encode("utf-8", errors="replace").decode("utf-8")


def chat_terminal():
    """터미널 대화 모드"""
    client = anthropic.Anthropic(api_key=API_KEY, timeout=120.0)
    system = load_system_prompt()
    messages = []

    print("=" * 50)
    print("  Hanyang Smart Auto Study Bot")
    print("  한양 스마트 오토 학업봇")
    print("=" * 50)
    print("안녕하세요! 스마트 오토예요.")
    print("수업, 학습, 일정 관련 무엇이든 물어보세요!")
    print("(종료: quit / 예습: 예습해줘 / 복습: 복습해줘)")
    print("-" * 50)

    while True:
        try:
            user_input = input("\n[Bella] ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n안녕! 다음에 또 봐요~")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "종료", "q"):
            print("\n안녕! 공부 파이팅~")
            break

        messages.append({"role": "user", "content": user_input})

        try:
            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                system=system,
                messages=messages,
            )
            reply = response.content[0].text
            messages.append({"role": "assistant", "content": reply})

            print(f"\n[스마트오토] {reply}")

        except Exception as e:
            print(f"\n[Error] API 오류: {e}")
            messages.pop()  # 실패한 메시지 제거


def main():
    if not API_KEY:
        print("[!] .env에 ANTHROPIC_API_KEY 설정 필요!")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Hanyang Smart Auto Chatbot")
    parser.add_argument("--whatsapp", action="store_true", help="WhatsApp integration mode")
    args = parser.parse_args()

    if args.whatsapp:
        print("[WhatsApp 모드는 OpenClaw 에이전트와 연동하세요]")
        print("  npx openclaw agent start --identity agent/IDENTITY.md")
        return

    chat_terminal()


if __name__ == "__main__":
    main()
