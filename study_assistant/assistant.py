"""
스마트 오토 학습 보조 (Phase 3)
Claude API로 수업 스크린샷 분석 + Scholar 논문 검색 + 예습/복습 자료 생성

사용법:
    python study_assistant/assistant.py                        # 전체 과목 분석
    python study_assistant/assistant.py --course 196594        # 특정 과목만
    python study_assistant/assistant.py --mode preview         # 예습 자료 생성
    python study_assistant/assistant.py --mode review          # 복습 자료 생성
    python study_assistant/assistant.py --mode syllabus        # 수업계획서 분석
    python study_assistant/assistant.py --mode explain         # 어려운 내용 해설
    python study_assistant/assistant.py --query "회귀분석"     # 특정 주제 검색/해설
"""

import anthropic
import argparse
import base64
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
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "data" / "study_notes"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_courses():
    with open(PROJECT_ROOT / "config" / "courses.json", "r", encoding="utf-8") as f:
        return json.load(f)


def image_to_base64(image_path):
    """이미지를 base64로 변환"""
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def get_client():
    return anthropic.Anthropic(api_key=API_KEY, timeout=120.0)


def analyze_syllabus(client, course):
    """수업계획서 스크린샷 분석 -> 구조화된 과목 요약"""
    cid = course["course_id"]
    name = course["name_ko"]
    screenshot = DATA_DIR / "courses" / str(cid) / "syllabus.png"

    if not screenshot.exists():
        return None

    print(f"\n[수업계획서 분석] {name}")

    content = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": image_to_base64(screenshot),
            },
        },
        {
            "type": "text",
            "text": f"""이 수업계획서 스크린샷을 분석해서 다음 정보를 구조화해주세요:

과목명: {name} ({course.get('name_en', '')})

분석해야 할 항목:
1. 교수님 이름 및 연락처
2. 수업 목표/개요
3. 주차별 강의 계획 (1~16주)
4. 성적 평가 방법 (출석, 과제, 시험 비율)
5. 교재 및 참고도서
6. 과제/프로젝트 설명
7. 주의사항/특이사항

출력 형식: 한국어로 깔끔하게 정리. 주차별 계획은 표 형식으로.
추가로 中文 간단 요약과 English 간단 요약도 마지막에 포함해주세요.""",
        },
    ]

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        messages=[{"role": "user", "content": content}],
    )

    result = response.content[0].text

    # 저장
    output_file = OUTPUT_DIR / f"{cid}_syllabus_analysis.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# {name} - 수업계획서 분석\n")
        f.write(f"분석일: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(result)

    print(f"   저장: {output_file}")
    return result


def analyze_weekly(client, course):
    """주차학습 스크린샷 분석 -> 현재 주차 학습 내용 파악"""
    cid = course["course_id"]
    name = course["name_ko"]
    screenshot = DATA_DIR / "courses" / str(cid) / "weekly.png"

    if not screenshot.exists():
        return None

    print(f"\n[주차학습 분석] {name}")

    content = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": image_to_base64(screenshot),
            },
        },
        {
            "type": "text",
            "text": f"""이 주차학습 페이지 스크린샷을 분석해주세요.

과목명: {name}

분석 항목:
1. 현재 진행 중인 주차 및 학습 내용
2. 각 주차별 학습 주제 목록
3. 업로드된 강의 자료 (PDF, 동영상 등) 있으면 제목 기록
4. 과제/퀴즈 마감일 있으면 기록
5. 다음 주 예습해야 할 내용 추천

한국어로 정리해주세요.""",
        },
    ]

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=3000,
        messages=[{"role": "user", "content": content}],
    )

    result = response.content[0].text

    output_file = OUTPUT_DIR / f"{cid}_weekly_analysis.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# {name} - 주차학습 분석\n")
        f.write(f"분석일: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(result)

    print(f"   저장: {output_file}")
    return result


def generate_preview(client, course, week_topic=""):
    """예습 자료 생성 - 다음 수업 준비용"""
    cid = course["course_id"]
    name = course["name_ko"]
    name_en = course.get("name_en", "")

    print(f"\n[예습 자료 생성] {name}")

    # 수업계획서 분석 결과가 있으면 활용
    syllabus_file = OUTPUT_DIR / f"{cid}_syllabus_analysis.md"
    syllabus_context = ""
    if syllabus_file.exists():
        with open(syllabus_file, "r", encoding="utf-8") as f:
            syllabus_context = f.read()[:3000]

    prompt = f"""MBA 과목 예습 자료를 만들어주세요.

과목: {name} ({name_en})
{f'주제: {week_topic}' if week_topic else ''}

{f'수업계획서 정보:\n{syllabus_context}' if syllabus_context else ''}

다음 내용을 포함해주세요:
1. **핵심 개념 정리** - 이번 주 배울 주요 개념 3~5개, 각각 간단 설명
2. **사전 지식** - 이해를 위해 미리 알아야 할 배경 지식
3. **핵심 용어 사전** - 영어/한국어/中文 3개 언어로 주요 용어 정리 (표 형식)
4. **예상 질문** - 수업에서 나올 수 있는 토론 질문 3개
5. **추천 읽기 자료** - 관련 기사, 논문, 책 추천

출력: 한국어 메인 + 핵심 용어는 3개 언어"""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    result = response.content[0].text

    timestamp = datetime.now().strftime('%Y%m%d')
    output_file = OUTPUT_DIR / f"{cid}_preview_{timestamp}.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# {name} - 예습 자료\n")
        f.write(f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(result)

    print(f"   저장: {output_file}")
    return result


def generate_review(client, course, week_topic=""):
    """복습 자료 생성 - 수업 후 정리용"""
    cid = course["course_id"]
    name = course["name_ko"]
    name_en = course.get("name_en", "")

    print(f"\n[복습 자료 생성] {name}")

    prompt = f"""MBA 과목 복습 자료를 만들어주세요.

과목: {name} ({name_en})
{f'주제: {week_topic}' if week_topic else ''}

다음 내용을 포함해주세요:
1. **핵심 요약** - 이번 주 배운 내용 5줄 요약
2. **핵심 공식/프레임워크** - 꼭 기억해야 할 공식이나 분석 틀
3. **실전 적용 사례** - 실제 비즈니스에서 어떻게 활용되는지 예시 2~3개
4. **자주 출제되는 포인트** - 시험에 나올 가능성 높은 내용
5. **복습 체크리스트** - 이해도 자가 점검 질문 5개 (O/X 또는 단답)
6. **다음 주 연결** - 다음 주차 내용과의 연결고리

출력: 한국어 메인. 핵심 용어는 (영어/中文) 병기."""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    result = response.content[0].text

    timestamp = datetime.now().strftime('%Y%m%d')
    output_file = OUTPUT_DIR / f"{cid}_review_{timestamp}.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# {name} - 복습 자료\n")
        f.write(f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(result)

    print(f"   저장: {output_file}")
    return result


def explain_topic(client, course, query):
    """특정 주제에 대한 상세 해설"""
    name = course["name_ko"]
    name_en = course.get("name_en", "")
    cid = course["course_id"]

    print(f"\n[주제 해설] {name}: {query}")

    prompt = f"""MBA 학생을 위해 다음 주제를 상세히 해설해주세요.

과목: {name} ({name_en})
질문/주제: {query}

해설 요청:
1. **개념 설명** - 쉽게, 비유를 활용해서
2. **수학/공식** - 관련 공식이 있으면 단계별 설명
3. **실전 예시** - 실제 비즈니스 케이스
4. **관련 논문/이론** - 원저자와 핵심 기여
5. **시험 팁** - 이 주제가 시험에 나온다면 어떤 형태로?

대상: MBA 학생 (비전공자도 이해할 수 있게)
언어: 한국어 메인, 핵심 용어는 영어/中文 병기"""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    result = response.content[0].text

    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    safe_query = "".join(c for c in query[:20] if c.isalnum() or c in "가-힣 ")
    output_file = OUTPUT_DIR / f"{cid}_explain_{safe_query}_{timestamp}.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# {name} - 주제 해설: {query}\n")
        f.write(f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(result)

    print(f"   저장: {output_file}")
    return result


def main():
    if not API_KEY:
        print("[!] .env에 ANTHROPIC_API_KEY 설정 필요!")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Smart Auto Study Assistant")
    parser.add_argument("--course", type=str, help="Specific course ID")
    parser.add_argument("--mode", type=str, default="syllabus",
                        choices=["syllabus", "weekly", "preview", "review", "explain", "all"],
                        help="Analysis mode")
    parser.add_argument("--query", type=str, help="Topic to explain (for explain mode)")
    parser.add_argument("--topic", type=str, default="", help="Week topic for preview/review")
    args = parser.parse_args()

    config = load_courses()
    courses = config["courses"]

    if args.course:
        courses = [c for c in courses if str(c["course_id"]) == str(args.course)]
        if not courses:
            print(f"[!] Course ID {args.course} not found")
            sys.exit(1)

    client = get_client()

    print("=" * 50)
    print(f"Smart Auto Study Assistant - Mode: {args.mode}")
    print(f"Courses: {len(courses)}")
    print("=" * 50)

    for course in courses:
        name = course["name_ko"]

        if args.mode == "syllabus" or args.mode == "all":
            analyze_syllabus(client, course)

        if args.mode == "weekly" or args.mode == "all":
            analyze_weekly(client, course)

        if args.mode == "preview" or args.mode == "all":
            generate_preview(client, course, args.topic)

        if args.mode == "review" or args.mode == "all":
            generate_review(client, course, args.topic)

        if args.mode == "explain":
            if not args.query:
                print(f"[!] --query 필요! 예: --query '회귀분석'")
                sys.exit(1)
            explain_topic(client, course, args.query)

    # Drive 업로드 (study_notes 폴더)
    print(f"\n{'='*50}")
    print("[DONE] 학습 자료 생성 완료!")
    print(f"   저장 위치: {OUTPUT_DIR}")
    print(f"   Drive 업로드: python scrapers/drive_uploader.py 실행")


if __name__ == "__main__":
    main()
