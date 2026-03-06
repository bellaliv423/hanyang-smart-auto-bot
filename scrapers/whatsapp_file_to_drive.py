"""
WhatsApp 파일 수신 → Google Drive 자동 업로드

벨라가 WhatsApp에서 파일(PDF, PPT, DOC, 이미지 등)을 보내면
자동으로 Google Drive 해당 과목 폴더에 업로드

사용법:
    # OpenClaw 에이전트에서 호출 (bash 도구)
    python3 /mnt/d/AI\\ _coding_project_all/hanyang_smart_auto_bot/scrapers/whatsapp_file_to_drive.py \\
        --file /path/to/downloaded/file.pdf \\
        --course 196594 \\
        --section 강의자료

    # 과목 자동 감지 (파일명에 과목명 포함 시)
    python3 .../whatsapp_file_to_drive.py --file file.pdf --auto
"""

import argparse
import io
import json
import os
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Windows/WSL 경로 호환
if os.path.exists("/mnt/d"):
    PROJECT_ROOT = Path("/mnt/d/AI _coding_project_all/hanyang_smart_auto_bot")
else:
    PROJECT_ROOT = Path(__file__).parent.parent

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / "config" / ".env")


def detect_course(filename):
    """파일명에서 과목 자동 감지"""
    course_keywords = {
        196594: ["경영통계", "통계", "statistics", "부제만"],
        196600: ["상법", "계약법", "commercial", "contract", "강편모"],
        196656: ["M&A", "mna", "김철중", "merger"],
        196622: ["국제거시", "금융론", "macrofinance", "이창민"],
    }

    filename_lower = filename.lower()
    for course_id, keywords in course_keywords.items():
        for kw in keywords:
            if kw.lower() in filename_lower:
                return course_id
    return None


def upload_to_drive(file_path, course_id, section="강의자료"):
    """Google Drive에 파일 업로드"""
    # drive_uploader의 함수 재사용
    sys.path.insert(0, str(PROJECT_ROOT / "scrapers"))
    from drive_uploader import get_drive_service, find_or_create_folder

    service = get_drive_service()

    # courses.json에서 과목명 찾기
    with open(PROJECT_ROOT / "config" / "courses.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    course_name = None
    for c in config["courses"]:
        if c["course_id"] == course_id:
            course_name = c["name_ko"]
            break

    if not course_name:
        print(f"[!] 과목 ID {course_id}를 찾을 수 없습니다")
        return None

    # Drive 폴더 경로: 한양MBA_2026년 1학기/{과목명}/{섹션}
    DRIVE_ROOT = "1RGGiiz_DKf5ZcUNk7baJis95oAcDJ5Em"
    semester = config.get("semester", "2026년 1학기")

    semester_folder = find_or_create_folder(service, f"한양MBA_{semester}", DRIVE_ROOT)
    course_folder = find_or_create_folder(service, course_name, semester_folder)
    section_folder = find_or_create_folder(service, section, course_folder)

    # 업로드
    from drive_uploader import upload_file
    file_id = upload_file(service, file_path, section_folder)

    if file_id:
        drive_url = f"https://drive.google.com/file/d/{file_id}/view"
        print(f"[OK] 업로드 완료!")
        print(f"  과목: {course_name}")
        print(f"  섹션: {section}")
        print(f"  파일: {Path(file_path).name}")
        print(f"  URL: {drive_url}")
        return drive_url

    return None


def save_to_local(file_path, course_id, section="강의자료"):
    """로컬 폴더에도 저장"""
    local_dir = PROJECT_ROOT / "data" / "courses" / str(course_id) / "downloads"
    local_dir.mkdir(parents=True, exist_ok=True)

    src = Path(file_path)
    dst = local_dir / src.name

    import shutil
    shutil.copy2(str(src), str(dst))
    print(f"[OK] 로컬 저장: {dst}")
    return str(dst)


def main():
    parser = argparse.ArgumentParser(description="WhatsApp File → Drive Upload")
    parser.add_argument("--file", required=True, help="업로드할 파일 경로")
    parser.add_argument("--course", type=int, help="Course ID (예: 196594)")
    parser.add_argument("--section", default="강의자료", help="Drive 섹션 (기본: 강의자료)")
    parser.add_argument("--auto", action="store_true", help="파일명에서 과목 자동 감지")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"[!] 파일 없음: {file_path}")
        sys.exit(1)

    # 과목 ID 결정
    course_id = args.course
    if args.auto or not course_id:
        detected = detect_course(file_path.name)
        if detected:
            course_id = detected
            print(f"[AUTO] 과목 감지: {course_id}")
        elif not course_id:
            print("[!] 과목을 감지할 수 없습니다. --course로 지정해주세요")
            print("  가능한 ID: 196594(경영통계학), 196600(상법), 196656(M&A), 196622(국제거시금융론)")
            sys.exit(1)

    # 로컬 저장
    save_to_local(file_path, course_id, args.section)

    # Drive 업로드
    drive_url = upload_to_drive(file_path, course_id, args.section)

    if drive_url:
        # JSON 결과 출력 (OpenClaw 에이전트가 파싱 가능)
        result = {
            "status": "success",
            "course_id": course_id,
            "section": args.section,
            "file_name": file_path.name,
            "drive_url": drive_url,
        }
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
