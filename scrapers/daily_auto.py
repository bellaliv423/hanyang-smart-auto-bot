"""
Daily Auto: 매일 아침 자동 스크래핑 + Drive 업로드 + WhatsApp 알림

프로세스:
1. LMS 로그인
2. 4과목 스크래핑 (수업계획서, 게시판, 주차학습, 강의자료, 출결)
3. 새 자료/변경사항 감지
4. Google Drive 업로드
5. WhatsApp으로 알림 (챗봇 경유)

사용법:
    python scrapers/daily_auto.py              # 전체 실행
    python scrapers/daily_auto.py --scrape     # 스크래핑만
    python scrapers/daily_auto.py --upload     # 업로드만
    python scrapers/daily_auto.py --notify     # 알림만
    python scrapers/daily_auto.py --dry-run    # 미리보기
"""

import argparse
import io
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
COURSES_DIR = DATA_DIR / "courses"
STUDY_NOTES_DIR = DATA_DIR / "study_notes"

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / "config" / ".env")


def log(msg):
    """타임스탬프 로그"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}")


def load_courses():
    """courses.json 로드"""
    with open(PROJECT_ROOT / "config" / "courses.json", "r", encoding="utf-8") as f:
        return json.load(f)


def get_file_snapshot(directory):
    """디렉토리 내 파일들의 크기+수정시간 스냅샷"""
    snapshot = {}
    if not directory.exists():
        return snapshot
    for fpath in directory.rglob("*"):
        if fpath.is_file():
            key = str(fpath.relative_to(directory))
            snapshot[key] = {
                "size": fpath.stat().st_size,
                "mtime": fpath.stat().st_mtime,
            }
    return snapshot


def detect_changes(before, after):
    """변경된 파일 감지"""
    new_files = []
    updated_files = []

    for key, info in after.items():
        if key not in before:
            new_files.append(key)
        elif before[key]["size"] != info["size"] or before[key]["mtime"] != info["mtime"]:
            updated_files.append(key)

    return new_files, updated_files


def run_scraper():
    """LMS 스크래핑 실행"""
    log("Phase 1: LMS 스크래핑 시작...")

    # 스크래핑 전 스냅샷
    before_snapshot = get_file_snapshot(COURSES_DIR)
    before_notes = get_file_snapshot(STUDY_NOTES_DIR)

    # 스크래핑 실행
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scrapers" / "course_scraper.py")],
        capture_output=True, text=True, timeout=600,
        cwd=str(PROJECT_ROOT),
    )

    if result.returncode != 0:
        log(f"  [!] 스크래핑 오류: {result.stderr[:200]}")
        return [], []

    log("  스크래핑 완료!")

    # 스크래핑 후 스냅샷
    after_snapshot = get_file_snapshot(COURSES_DIR)
    after_notes = get_file_snapshot(STUDY_NOTES_DIR)

    # 변경 감지
    new_files, updated_files = detect_changes(before_snapshot, after_snapshot)
    new_notes, updated_notes = detect_changes(before_notes, after_notes)

    all_new = new_files + [f"study_notes/{n}" for n in new_notes]
    all_updated = updated_files + [f"study_notes/{n}" for n in updated_notes]

    if all_new:
        log(f"  [NEW] 새 파일 {len(all_new)}개: {', '.join(all_new[:5])}")
    if all_updated:
        log(f"  [UPD] 변경 파일 {len(all_updated)}개: {', '.join(all_updated[:5])}")
    if not all_new and not all_updated:
        log("  변경 없음 (새 자료 없음)")

    return all_new, all_updated


def run_upload(dry_run=False):
    """Google Drive 업로드"""
    log("Phase 2: Google Drive 업로드...")

    args = [sys.executable, str(PROJECT_ROOT / "scrapers" / "drive_uploader.py")]
    if dry_run:
        args.append("--dry-run")

    result = subprocess.run(
        args, capture_output=True, text=True, timeout=300,
        cwd=str(PROJECT_ROOT),
    )

    if result.returncode != 0:
        log(f"  [!] 업로드 오류: {result.stderr[:200]}")
        return False

    # 업로드된 파일 수 파싱
    for line in result.stdout.split("\n"):
        if "[DONE]" in line:
            log(f"  {line.strip()}")

    log("  업로드 완료!")
    return True


def send_notification(new_files, updated_files):
    """WhatsApp으로 알림 보내기 (OpenClaw 경유)"""
    if not new_files and not updated_files:
        log("Phase 3: 변경 없음 → 알림 스킵")
        return

    log("Phase 3: WhatsApp 알림 발송...")

    # 알림 메시지 구성
    config = load_courses()
    course_names = {str(c["course_id"]): c["name_ko"] for c in config["courses"]}

    msg_parts = ["📚 [스마트 오토] LMS 자료 업데이트 알림\n"]

    if new_files:
        msg_parts.append(f"🆕 새 자료 {len(new_files)}개:")
        for f in new_files[:10]:
            # 과목 이름 매핑
            parts = f.replace("\\", "/").split("/")
            course_id = parts[0] if parts else ""
            course_name = course_names.get(course_id, course_id)
            file_name = parts[-1] if parts else f
            msg_parts.append(f"  - {course_name}: {file_name}")

    if updated_files:
        msg_parts.append(f"\n📝 변경된 자료 {len(updated_files)}개:")
        for f in updated_files[:10]:
            parts = f.replace("\\", "/").split("/")
            course_id = parts[0] if parts else ""
            course_name = course_names.get(course_id, course_id)
            file_name = parts[-1] if parts else f
            msg_parts.append(f"  - {course_name}: {file_name}")

    msg_parts.append("\n✅ Google Drive에 자동 업로드 완료!")
    msg_parts.append("📂 Drive: https://drive.google.com/drive/folders/1RGGiiz_DKf5ZcUNk7baJis95oAcDJ5Em")

    message = "\n".join(msg_parts)

    # WhatsApp 전송 (OpenClaw CLI)
    target = os.getenv("WHATSAPP_TARGET", "")
    if not target:
        log("  [!] WHATSAPP_TARGET 미설정 → 알림 스킵")
        return

    try:
        result = subprocess.run(
            [
                "wsl", "bash", "-c",
                f'npx openclaw message send --channel whatsapp '
                f'--target "{target}" '
                f'--message "{message}" --json'
            ],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            log("  WhatsApp 알림 발송 완료!")
        else:
            log(f"  [!] WhatsApp 발송 실패: {result.stderr[:100]}")

            # 대안: httpx로 직접 전송
            try:
                import httpx
                gateway_url = os.getenv("WHATSAPP_GATEWAY_URL", "http://localhost:3000")
                resp = httpx.post(
                    f"{gateway_url}/api/sendMessage",
                    json={"chatId": f"{target.replace('+', '')}@c.us", "text": message},
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    log("  WhatsApp 알림 발송 완료! (HTTP API)")
            except Exception as e2:
                log(f"  [!] HTTP API도 실패: {e2}")

    except Exception as e:
        log(f"  [!] 알림 오류: {e}")


def save_daily_log(new_files, updated_files, upload_ok):
    """일일 로그 저장"""
    log_dir = DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"daily_{today}.json"

    log_data = {
        "date": today,
        "timestamp": datetime.now().isoformat(),
        "new_files": new_files,
        "updated_files": updated_files,
        "upload_success": upload_ok,
        "total_changes": len(new_files) + len(updated_files),
    }

    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

    log(f"  일일 로그 저장: {log_file.name}")


def main():
    parser = argparse.ArgumentParser(description="Daily Auto: Scrape + Upload + Notify")
    parser.add_argument("--scrape", action="store_true", help="스크래핑만")
    parser.add_argument("--upload", action="store_true", help="업로드만")
    parser.add_argument("--notify", action="store_true", help="알림만 (테스트)")
    parser.add_argument("--dry-run", action="store_true", help="미리보기")
    args = parser.parse_args()

    print("=" * 50)
    print("  Smart Auto Bot - Daily Auto")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # 특정 단계만 실행
    if args.scrape:
        run_scraper()
        return
    if args.upload:
        run_upload(dry_run=args.dry_run)
        return
    if args.notify:
        send_notification(["test/new_file.png"], [])
        return

    # 전체 파이프라인
    new_files, updated_files = run_scraper()

    upload_ok = False
    if new_files or updated_files:
        upload_ok = run_upload(dry_run=args.dry_run)
        if not args.dry_run:
            send_notification(new_files, updated_files)
    else:
        log("변경 없음 → 업로드/알림 스킵")

    save_daily_log(new_files, updated_files, upload_ok)

    print("\n" + "=" * 50)
    log(f"Daily Auto 완료! (새 {len(new_files)}개 + 변경 {len(updated_files)}개)")
    print("=" * 50)


if __name__ == "__main__":
    main()
