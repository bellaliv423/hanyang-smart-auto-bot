"""
Google Drive 업로드 + 폴더 자동 정리
스크래핑된 자료 및 다운로드 파일을 과목별 폴더로 정리하여 Drive에 업로드

사용법:
    python scrapers/drive_uploader.py                  # 전체 업로드
    python scrapers/drive_uploader.py --course 196594  # 특정 과목만
    python scrapers/drive_uploader.py --dry-run        # 미리보기 (업로드 안 함)
"""

import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / "config" / ".env")

# Google Drive 설정
CREDENTIALS_PATH = Path("D:/OzKiz_Global_Automation/google_credentials.json")
DRIVE_ROOT_FOLDER_ID = "1CKdC7843gCtjk4ZVwwxEImx5QEqgblfZ"  # 벨라 공유 폴더

DATA_DIR = PROJECT_ROOT / "data"


def get_drive_service():
    """Google Drive API 서비스 생성"""
    scopes = ['https://www.googleapis.com/auth/drive']

    # OAuth2 토큰 파일이 있으면 사용 (벨라 개인 계정)
    token_path = PROJECT_ROOT / "config" / "drive_token.json"
    if token_path.exists():
        from google.oauth2.credentials import Credentials as UserCreds
        creds = UserCreds.from_authorized_user_file(str(token_path), scopes)
        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            with open(token_path, 'w') as f:
                f.write(creds.to_json())
        return build('drive', 'v3', credentials=creds)

    # OAuth2 클라이언트 파일이 있으면 브라우저 인증 시작
    client_secret_path = PROJECT_ROOT / "config" / "client_secret.json"
    if client_secret_path.exists():
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), scopes)
        creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as f:
            f.write(creds.to_json())
        return build('drive', 'v3', credentials=creds)

    # 서비스 계정 (폴더 생성만 가능, 파일 업로드 불가)
    creds = Credentials.from_service_account_file(str(CREDENTIALS_PATH), scopes=scopes)
    return build('drive', 'v3', credentials=creds)


def find_or_create_folder(service, folder_name, parent_id):
    """폴더 찾기, 없으면 생성"""
    query = (
        f"name='{folder_name}' and "
        f"'{parent_id}' in parents and "
        f"mimeType='application/vnd.google-apps.folder' and "
        f"trashed=false"
    )
    results = service.files().list(
        q=query, fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    files = results.get("files", [])

    if files:
        return files[0]["id"]

    # 폴더 생성
    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(
        body=metadata, fields="id",
        supportsAllDrives=True,
    ).execute()
    print(f"   [+] 폴더 생성: {folder_name}")
    return folder["id"]


def upload_file(service, local_path, parent_folder_id, file_name=None):
    """파일 업로드 (동일 이름 있으면 업데이트)"""
    local_path = Path(local_path)
    if not local_path.exists():
        return None

    name = file_name or local_path.name

    # 기존 파일 확인
    query = (
        f"name='{name}' and "
        f"'{parent_folder_id}' in parents and "
        f"trashed=false"
    )
    results = service.files().list(
        q=query, fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    existing = results.get("files", [])

    # MIME 타입 결정
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".pdf": "application/pdf",
        ".json": "application/json",
        ".txt": "text/plain",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".ppt": "application/vnd.ms-powerpoint",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".hwp": "application/x-hwp",
        ".zip": "application/zip",
    }
    mime_type = mime_map.get(local_path.suffix.lower(), "application/octet-stream")
    media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=True)

    if existing:
        # 기존 파일 업데이트
        file_id = existing[0]["id"]
        service.files().update(
            fileId=file_id, media_body=media,
            supportsAllDrives=True,
        ).execute()
        return file_id
    else:
        # 새 파일 업로드
        metadata = {"name": name, "parents": [parent_folder_id]}
        result = service.files().create(
            body=metadata, media_body=media, fields="id",
            supportsAllDrives=True,
        ).execute()
        return result["id"]


def setup_drive_folders(service):
    """
    Drive 폴더 구조 생성:
    한양MBA_2026_1학기/
      경영통계학/
        수업계획서/
        게시판/
        주차학습/
        강의자료/
        다운로드/
      상법및계약법/
        ...
    """
    courses_file = PROJECT_ROOT / "config" / "courses.json"
    with open(courses_file, "r", encoding="utf-8") as f:
        config = json.load(f)

    semester = config.get("semester", "2026년 1학기")

    # 최상위: 학기 폴더
    semester_folder_id = find_or_create_folder(service, f"한양MBA_{semester}", DRIVE_ROOT_FOLDER_ID)

    folder_map = {}
    sections = ["수업계획서", "게시판", "주차학습", "강의자료", "다운로드"]

    for course in config["courses"]:
        cid = course["course_id"]
        name = course["name_ko"]

        # 과목 폴더
        course_folder_id = find_or_create_folder(service, name, semester_folder_id)
        folder_map[cid] = {"root": course_folder_id}

        # 섹션별 하위 폴더
        for section in sections:
            section_id = find_or_create_folder(service, section, course_folder_id)
            folder_map[cid][section] = section_id

    return semester_folder_id, folder_map


def upload_course_data(service, folder_map, course_id, dry_run=False):
    """한 과목의 스크래핑 데이터 업로드"""
    cid = course_id
    course_dir = DATA_DIR / "courses" / str(cid)

    if not course_dir.exists():
        print(f"   [!] 데이터 없음: {course_dir}")
        return 0

    uploaded = 0
    section_file_map = {
        "수업계획서": ["syllabus.png"],
        "게시판": ["board.png"],
        "주차학습": ["weekly.png"],
        "강의자료": ["materials.png"],
    }

    for section, files in section_file_map.items():
        folder_id = folder_map[cid].get(section)
        if not folder_id:
            continue

        for fname in files:
            fpath = course_dir / fname
            if fpath.exists():
                if dry_run:
                    print(f"   [DRY] {section}/{fname}")
                else:
                    upload_file(service, fpath, folder_id)
                    print(f"   [OK] {section}/{fname}")
                uploaded += 1

    # scrape_result.json -> 과목 루트
    result_file = course_dir / "scrape_result.json"
    if result_file.exists():
        if dry_run:
            print(f"   [DRY] scrape_result.json")
        else:
            upload_file(service, result_file, folder_map[cid]["root"])
            print(f"   [OK] scrape_result.json")
        uploaded += 1

    # 다운로드 폴더의 파일들
    download_dir = course_dir / "downloads"
    if download_dir.exists():
        dl_folder_id = folder_map[cid].get("다운로드")
        if dl_folder_id:
            for fpath in download_dir.iterdir():
                if fpath.is_file():
                    if dry_run:
                        print(f"   [DRY] 다운로드/{fpath.name}")
                    else:
                        upload_file(service, fpath, dl_folder_id)
                        print(f"   [OK] 다운로드/{fpath.name}")
                    uploaded += 1

    # 학습 노트 (study_notes)
    study_notes_dir = DATA_DIR / "study_notes"
    if study_notes_dir.exists():
        # "학습노트" 하위 폴더 생성
        notes_folder_id = folder_map[cid].get("학습노트")
        if not notes_folder_id:
            notes_folder_id = find_or_create_folder(service, "학습노트", folder_map[cid]["root"])
            folder_map[cid]["학습노트"] = notes_folder_id

        for fpath in study_notes_dir.glob(f"{cid}_*.md"):
            if dry_run:
                print(f"   [DRY] 학습노트/{fpath.name}")
            else:
                upload_file(service, fpath, notes_folder_id)
                print(f"   [OK] 학습노트/{fpath.name}")
            uploaded += 1

    return uploaded


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Upload course data to Google Drive")
    parser.add_argument("--course", type=str, help="Specific course ID")
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    args = parser.parse_args()

    print("=" * 50)
    print("Smart Auto Bot - Google Drive Upload")
    print("=" * 50)

    if not CREDENTIALS_PATH.exists():
        print(f"[!] 서비스 계정 파일 없음: {CREDENTIALS_PATH}")
        sys.exit(1)

    service = get_drive_service()
    print("[1/3] Google Drive 연결 완료")

    # 폴더 구조 생성
    semester_id, folder_map = setup_drive_folders(service)
    print(f"[2/3] Drive 폴더 구조 준비 완료 (학기 폴더: {semester_id})")

    # 과목 설정 로드
    with open(PROJECT_ROOT / "config" / "courses.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    courses = config["courses"]
    if args.course:
        courses = [c for c in courses if str(c["course_id"]) == str(args.course)]

    # 업로드
    print(f"[3/3] 업로드 시작 ({len(courses)}과목){'  [DRY RUN]' if args.dry_run else ''}")
    total = 0
    for course in courses:
        cid = course["course_id"]
        print(f"\n--- {course['name_ko']} (ID: {cid}) ---")
        count = upload_course_data(service, folder_map, cid, dry_run=args.dry_run)
        total += count

    # 요약 JSON도 업로드
    summary_file = DATA_DIR / "scrape_summary.json"
    if summary_file.exists() and not args.dry_run:
        upload_file(service, summary_file, semester_id)
        total += 1

    print(f"\n{'='*50}")
    action = "미리보기" if args.dry_run else "업로드"
    print(f"[DONE] {action} 완료! 총 {total}개 파일")
    print(f"   Drive 폴더: https://drive.google.com/drive/folders/{semester_id}")


if __name__ == "__main__":
    main()
