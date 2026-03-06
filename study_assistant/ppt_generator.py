"""
PPT 자동 생성기 - 수업 주제 → 전문적인 PPT 파일

기능:
1. 주제 입력 → Claude AI가 구조화된 PPT 내용 생성
2. 논문/기사/사례 검색 결과 포함
3. 한국어/中文/English 다국어 지원
4. Google Drive 자동 업로드
5. WhatsApp으로 완성 알림

사용법:
    python study_assistant/ppt_generator.py --topic "회귀분석" --course 196594
    python study_assistant/ppt_generator.py --topic "M&A 절차" --course 196656 --lang zh
    python study_assistant/ppt_generator.py --topic "계약법 기초" --slides 10 --lang ko
"""

import anthropic
import argparse
import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor

PROJECT_ROOT = Path(__file__).parent.parent

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / "config" / ".env")

API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# 과목 매핑
COURSE_MAP = {
    196594: {"ko": "경영통계학", "en": "Business Statistics", "zh": "經營統計學", "prof": "부제만"},
    196600: {"ko": "상법및계약법", "en": "Commercial & Contract Law", "zh": "商法及契約法", "prof": "강편모"},
    196656: {"ko": "M&A전략", "en": "M&A Strategy", "zh": "M&A戰略", "prof": "김철중"},
    196622: {"ko": "국제거시금융론", "en": "International Macrofinance", "zh": "國際宏觀金融論", "prof": "이창민"},
}

# PPT 색상 테마 (한양대 느낌)
THEME = {
    "primary": RGBColor(0, 51, 102),      # 진한 남색
    "secondary": RGBColor(0, 102, 153),    # 파란색
    "accent": RGBColor(204, 0, 0),         # 빨간색 강조
    "bg_dark": RGBColor(0, 51, 102),       # 어두운 배경
    "bg_light": RGBColor(240, 245, 250),   # 밝은 배경
    "text_dark": RGBColor(33, 33, 33),     # 본문 텍스트
    "text_light": RGBColor(255, 255, 255), # 밝은 텍스트
    "text_sub": RGBColor(100, 100, 100),   # 부제 텍스트
}


def generate_ppt_content(topic, course_id=None, lang="ko", num_slides=8):
    """Claude AI로 PPT 내용 생성"""
    client = anthropic.Anthropic(api_key=API_KEY, timeout=120.0)

    course_info = ""
    if course_id and course_id in COURSE_MAP:
        c = COURSE_MAP[course_id]
        course_info = f"\n과목: {c['ko']} ({c['en']}) / 교수: {c['prof']}"

    lang_map = {"ko": "한국어", "en": "English", "zh": "中文繁體"}
    target_lang = lang_map.get(lang, "한국어")

    prompt = f"""MBA 수업 발표용 PPT 내용을 생성해주세요.

주제: {topic}{course_info}
언어: {target_lang}
슬라이드 수: {num_slides}장

반드시 아래 JSON 형식으로 출력하세요:

```json
{{
  "title": "PPT 제목",
  "subtitle": "부제목",
  "slides": [
    {{
      "title": "슬라이드 제목",
      "type": "content",
      "bullets": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3"],
      "notes": "발표자 노트 (설명)"
    }},
    {{
      "title": "사례 연구",
      "type": "case",
      "company": "기업명",
      "bullets": ["사례 포인트 1", "사례 포인트 2"],
      "notes": "발표자 노트"
    }},
    {{
      "title": "참고 자료",
      "type": "references",
      "bullets": ["논문/기사 1 - 저자, 연도", "논문/기사 2 - 저자, 연도"],
      "notes": ""
    }}
  ],
  "key_terms": [
    {{"term": "용어", "ko": "한국어", "en": "English", "zh": "中文"}}
  ]
}}
```

요구사항:
1. MBA 수준의 전문적 내용
2. 실제 기업 사례 1-2개 포함
3. 관련 논문/기사 참고자료 포함
4. 핵심 용어는 한/영/중 3개 언어 병기
5. 각 슬라이드에 발표자 노트 포함
6. 마지막 슬라이드는 참고자료(References)"""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text

    # JSON 추출
    import re
    json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(1))

    # JSON 블록 없으면 전체 파싱 시도
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print("[!] JSON 파싱 실패, 기본 구조로 생성")
        return {
            "title": topic,
            "subtitle": "한양대 MBA",
            "slides": [
                {"title": topic, "type": "content",
                 "bullets": [text[:200]], "notes": ""}
            ],
            "key_terms": []
        }


def set_slide_bg(slide, color):
    """슬라이드 배경색 설정"""
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_text_box(slide, left, top, width, height, text, font_size=18,
                 color=None, bold=False, alignment=PP_ALIGN.LEFT):
    """텍스트 박스 추가"""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.alignment = alignment
    if color:
        p.font.color.rgb = color
    return tf


def create_title_slide(prs, data, course_id=None):
    """표지 슬라이드"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank
    set_slide_bg(slide, THEME["bg_dark"])

    # 제목
    add_text_box(slide, Inches(1), Inches(1.5), Inches(8), Inches(1.5),
                 data["title"], font_size=36, color=THEME["text_light"],
                 bold=True, alignment=PP_ALIGN.CENTER)

    # 부제
    add_text_box(slide, Inches(1), Inches(3.2), Inches(8), Inches(0.8),
                 data.get("subtitle", ""), font_size=20,
                 color=RGBColor(180, 200, 220), alignment=PP_ALIGN.CENTER)

    # 과목 + 날짜
    if course_id and course_id in COURSE_MAP:
        c = COURSE_MAP[course_id]
        info = f"{c['ko']} | {c['prof']} 교수"
    else:
        info = "한양대학교 MBA 경영전문대학원"

    add_text_box(slide, Inches(1), Inches(4.5), Inches(8), Inches(0.5),
                 info, font_size=14, color=RGBColor(150, 170, 190),
                 alignment=PP_ALIGN.CENTER)

    add_text_box(slide, Inches(1), Inches(5.0), Inches(8), Inches(0.5),
                 datetime.now().strftime("%Y년 %m월 %d일"), font_size=12,
                 color=RGBColor(130, 150, 170), alignment=PP_ALIGN.CENTER)


def create_content_slide(prs, slide_data, slide_num):
    """내용 슬라이드"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank
    set_slide_bg(slide, THEME["bg_light"])

    # 상단 색상 바
    shape = slide.shapes.add_shape(
        1, Inches(0), Inches(0), Inches(10), Inches(0.08)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = THEME["primary"]
    shape.line.fill.background()

    # 슬라이드 번호
    add_text_box(slide, Inches(0.5), Inches(0.2), Inches(0.5), Inches(0.4),
                 f"{slide_num:02d}", font_size=11, color=THEME["text_sub"])

    # 제목
    add_text_box(slide, Inches(0.5), Inches(0.5), Inches(9), Inches(0.7),
                 slide_data["title"], font_size=28, color=THEME["primary"],
                 bold=True)

    # 구분선
    shape = slide.shapes.add_shape(
        1, Inches(0.5), Inches(1.2), Inches(2), Inches(0.03)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = THEME["accent"]
    shape.line.fill.background()

    # 불릿 포인트
    bullets = slide_data.get("bullets", [])
    y_pos = 1.5
    for bullet in bullets:
        tf = add_text_box(slide, Inches(0.8), Inches(y_pos), Inches(8.4), Inches(0.6),
                     f"    {bullet}", font_size=16, color=THEME["text_dark"])
        # 불릿 마커
        add_text_box(slide, Inches(0.5), Inches(y_pos), Inches(0.3), Inches(0.4),
                     "●", font_size=10, color=THEME["secondary"])
        y_pos += 0.55

    # 발표자 노트
    notes = slide_data.get("notes", "")
    if notes:
        notes_slide = slide.notes_slide
        notes_slide.notes_text_frame.text = notes


def create_case_slide(prs, slide_data, slide_num):
    """사례 연구 슬라이드"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, RGBColor(255, 255, 255))

    # 상단 바
    shape = slide.shapes.add_shape(
        1, Inches(0), Inches(0), Inches(10), Inches(0.08)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = THEME["accent"]
    shape.line.fill.background()

    # 제목
    add_text_box(slide, Inches(0.5), Inches(0.3), Inches(1.5), Inches(0.5),
                 "CASE STUDY", font_size=11, color=THEME["accent"], bold=True)

    add_text_box(slide, Inches(0.5), Inches(0.7), Inches(9), Inches(0.7),
                 slide_data["title"], font_size=26, color=THEME["primary"],
                 bold=True)

    company = slide_data.get("company", "")
    if company:
        add_text_box(slide, Inches(0.5), Inches(1.4), Inches(9), Inches(0.4),
                     company, font_size=16, color=THEME["secondary"], bold=True)

    # 불릿
    bullets = slide_data.get("bullets", [])
    y_pos = 2.0
    for bullet in bullets:
        add_text_box(slide, Inches(0.8), Inches(y_pos), Inches(8.4), Inches(0.6),
                     f"▸ {bullet}", font_size=15, color=THEME["text_dark"])
        y_pos += 0.5

    notes = slide_data.get("notes", "")
    if notes:
        slide.notes_slide.notes_text_frame.text = notes


def create_terms_slide(prs, key_terms):
    """핵심 용어 슬라이드 (3개 언어)"""
    if not key_terms:
        return

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, THEME["bg_light"])

    # 상단 바
    shape = slide.shapes.add_shape(
        1, Inches(0), Inches(0), Inches(10), Inches(0.08)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = THEME["primary"]
    shape.line.fill.background()

    add_text_box(slide, Inches(0.5), Inches(0.5), Inches(9), Inches(0.7),
                 "Key Terms / 핵심 용어 / 關鍵術語", font_size=24,
                 color=THEME["primary"], bold=True)

    # 테이블 형식으로 용어 표시
    y_pos = 1.5
    # 헤더
    add_text_box(slide, Inches(0.5), Inches(1.2), Inches(3), Inches(0.4),
                 "한국어", font_size=13, color=THEME["secondary"], bold=True)
    add_text_box(slide, Inches(3.5), Inches(1.2), Inches(3), Inches(0.4),
                 "English", font_size=13, color=THEME["secondary"], bold=True)
    add_text_box(slide, Inches(6.5), Inches(1.2), Inches(3), Inches(0.4),
                 "中文", font_size=13, color=THEME["secondary"], bold=True)

    for term in key_terms[:8]:
        add_text_box(slide, Inches(0.5), Inches(y_pos), Inches(3), Inches(0.4),
                     term.get("ko", ""), font_size=14, color=THEME["text_dark"])
        add_text_box(slide, Inches(3.5), Inches(y_pos), Inches(3), Inches(0.4),
                     term.get("en", ""), font_size=14, color=THEME["text_dark"])
        add_text_box(slide, Inches(6.5), Inches(y_pos), Inches(3), Inches(0.4),
                     term.get("zh", ""), font_size=14, color=THEME["text_dark"])
        y_pos += 0.45


def create_references_slide(prs, slide_data):
    """참고자료 슬라이드"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, RGBColor(255, 255, 255))

    shape = slide.shapes.add_shape(
        1, Inches(0), Inches(0), Inches(10), Inches(0.08)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = THEME["primary"]
    shape.line.fill.background()

    add_text_box(slide, Inches(0.5), Inches(0.5), Inches(9), Inches(0.7),
                 "References / 참고 자료", font_size=24,
                 color=THEME["primary"], bold=True)

    bullets = slide_data.get("bullets", [])
    y_pos = 1.5
    for i, ref in enumerate(bullets, 1):
        add_text_box(slide, Inches(0.5), Inches(y_pos), Inches(9), Inches(0.5),
                     f"[{i}] {ref}", font_size=12, color=THEME["text_sub"])
        y_pos += 0.4


def create_end_slide(prs):
    """마지막 슬라이드"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, THEME["bg_dark"])

    add_text_box(slide, Inches(1), Inches(2.5), Inches(8), Inches(1),
                 "Thank You", font_size=40, color=THEME["text_light"],
                 bold=True, alignment=PP_ALIGN.CENTER)

    add_text_box(slide, Inches(1), Inches(3.8), Inches(8), Inches(0.5),
                 "한양대학교 MBA 경영전문대학원", font_size=14,
                 color=RGBColor(150, 170, 190), alignment=PP_ALIGN.CENTER)

    add_text_box(slide, Inches(1), Inches(4.5), Inches(8), Inches(0.4),
                 "Generated by Smart Auto Study Bot", font_size=10,
                 color=RGBColor(100, 120, 140), alignment=PP_ALIGN.CENTER)


def build_ppt(data, course_id=None, output_path=None):
    """PPT 파일 생성"""
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(5.625)  # 16:9

    # 1. 표지
    create_title_slide(prs, data, course_id)

    # 2. 내용 슬라이드
    slide_num = 1
    for slide_data in data.get("slides", []):
        slide_type = slide_data.get("type", "content")

        if slide_type == "case":
            create_case_slide(prs, slide_data, slide_num)
        elif slide_type == "references":
            create_references_slide(prs, slide_data)
        else:
            create_content_slide(prs, slide_data, slide_num)
        slide_num += 1

    # 3. 핵심 용어 (3개 언어)
    create_terms_slide(prs, data.get("key_terms", []))

    # 4. 마지막 슬라이드
    create_end_slide(prs)

    # 저장
    if not output_path:
        safe_title = data["title"].replace(" ", "_").replace("/", "-")[:30]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_path = PROJECT_ROOT / "data" / "study_notes" / f"PPT_{safe_title}_{timestamp}.pptx"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Smart Auto PPT Generator")
    parser.add_argument("--topic", required=True, help="PPT 주제")
    parser.add_argument("--course", type=int, help="Course ID")
    parser.add_argument("--lang", default="ko", choices=["ko", "en", "zh"], help="언어")
    parser.add_argument("--slides", type=int, default=8, help="슬라이드 수")
    parser.add_argument("--output", help="출력 파일 경로")
    parser.add_argument("--upload", action="store_true", help="Drive 업로드")
    parser.add_argument("--email", action="store_true", help="이메일로 발송")
    parser.add_argument("--whatsapp", action="store_true", help="WhatsApp 알림")
    parser.add_argument("--send", action="store_true", help="이메일 + WhatsApp 모두 발송")
    args = parser.parse_args()

    if not API_KEY:
        print("[!] ANTHROPIC_API_KEY 필요!")
        sys.exit(1)

    print(f"{'='*50}")
    print(f"  Smart Auto PPT Generator")
    print(f"  주제: {args.topic}")
    if args.course and args.course in COURSE_MAP:
        print(f"  과목: {COURSE_MAP[args.course]['ko']}")
    print(f"  언어: {args.lang} | 슬라이드: {args.slides}장")
    print(f"{'='*50}")

    # 1. AI 내용 생성
    print("\n[1/3] AI 내용 생성 중...")
    data = generate_ppt_content(args.topic, args.course, args.lang, args.slides)
    print(f"  제목: {data.get('title', args.topic)}")
    print(f"  슬라이드: {len(data.get('slides', []))}장")

    # 2. PPT 파일 생성
    print("\n[2/3] PPT 파일 생성 중...")
    output_path = build_ppt(data, args.course, args.output)
    print(f"  저장: {output_path}")
    print(f"  크기: {output_path.stat().st_size / 1024:.1f} KB")

    # 3. Drive 업로드 (선택)
    if args.upload:
        print("\n[3/3] Google Drive 업로드 중...")
        try:
            sys.path.insert(0, str(PROJECT_ROOT / "scrapers"))
            from drive_uploader import get_drive_service, find_or_create_folder, upload_file

            service = get_drive_service()
            DRIVE_ROOT = "1RGGiiz_DKf5ZcUNk7baJis95oAcDJ5Em"

            with open(PROJECT_ROOT / "config" / "courses.json", "r", encoding="utf-8") as f:
                config = json.load(f)

            semester_folder = find_or_create_folder(service, f"한양MBA_{config['semester']}", DRIVE_ROOT)

            if args.course:
                course_name = COURSE_MAP.get(args.course, {}).get("ko", "기타")
                course_folder = find_or_create_folder(service, course_name, semester_folder)
                notes_folder = find_or_create_folder(service, "학습노트", course_folder)
                file_id = upload_file(service, output_path, notes_folder)
            else:
                file_id = upload_file(service, output_path, semester_folder)

            drive_url = f"https://drive.google.com/file/d/{file_id}/view"
            print(f"  Drive URL: {drive_url}")
        except Exception as e:
            print(f"  [!] 업로드 실패: {e}")

    # 4. 이메일 발송
    if args.email or args.send:
        print("\n[EMAIL] 이메일 발송 중...")
        try:
            from email_sender import send_email_with_attachment
            course_name = COURSE_MAP.get(args.course, {}).get("ko", "") if args.course else ""
            subject = f"[Smart Auto] {course_name} - {data.get('title', args.topic)}"
            send_email_with_attachment(output_path, subject=subject)
        except Exception as e:
            print(f"  [!] 이메일 실패: {e}")

    # 5. WhatsApp 알림
    if args.whatsapp or args.send:
        print("\n[WHATSAPP] WhatsApp 알림 발송 중...")
        try:
            import subprocess
            target = os.getenv("WHATSAPP_TARGET", "")
            course_name = COURSE_MAP.get(args.course, {}).get("ko", "") if args.course else ""
            msg = (
                f"PPT 생성 완료!\n"
                f"제목: {data.get('title', args.topic)}\n"
                f"과목: {course_name}\n"
                f"슬라이드: {len(data.get('slides', []))}장\n"
                f"파일: {output_path.name}\n"
                f"이메일로도 보냈어요!"
            )
            subprocess.run(
                ["wsl", "bash", "-c",
                 f'npx openclaw message send --channel whatsapp '
                 f'--target "{target}" --message "{msg}" --json'],
                capture_output=True, timeout=30,
            )
            print("  WhatsApp 알림 발송 완료!")
        except Exception as e:
            print(f"  [!] WhatsApp 실패: {e}")

    print(f"\n{'='*50}")
    print(f"[DONE] PPT 생성 완료!")
    print(f"  파일: {output_path.name}")

    # JSON 결과 출력 (에이전트 파싱용)
    result = {
        "status": "success",
        "file": str(output_path),
        "file_name": output_path.name,
        "title": data.get("title", args.topic),
        "slides": len(data.get("slides", [])),
        "terms": len(data.get("key_terms", [])),
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
