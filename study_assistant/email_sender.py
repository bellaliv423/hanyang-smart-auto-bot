"""
이메일 첨부파일 발송 - PPT/DOC 생성 후 자동 이메일 전송

사용법:
    python study_assistant/email_sender.py --file "path/to/file.pptx" --to "kndli.210@gmail.com"
    python study_assistant/email_sender.py --file "path/to/file.docx" --subject "경영통계학 레포트"
"""

import argparse
import io
import os
import smtplib
import sys
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

try:
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass

PROJECT_ROOT = Path(__file__).parent.parent

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / "config" / ".env")

# 이메일 설정
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.getenv("EMAIL_SENDER", "kndli.210@gmail.com")
SENDER_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "")
DEFAULT_TO = os.getenv("EMAIL_DEFAULT_TO", "kndli.210@gmail.com")


def send_email_with_attachment(file_path, to_email=None, subject=None, body=None):
    """이메일 첨부파일 발송"""
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"[!] 파일 없음: {file_path}")
        return False

    to_email = to_email or DEFAULT_TO

    if not subject:
        subject = f"[Smart Auto] {file_path.stem}"

    if not body:
        ext = file_path.suffix.lower()
        type_name = "PPT" if ext == ".pptx" else "Word 문서" if ext == ".docx" else "파일"
        body = f"""안녕하세요 벨라!

Smart Auto Study Bot이 생성한 {type_name}를 보내드려요.

파일명: {file_path.name}
크기: {file_path.stat().st_size / 1024:.1f} KB

Google Drive에도 자동 업로드되었어요!
Drive: https://drive.google.com/drive/folders/1RGGiiz_DKf5ZcUNk7baJis95oAcDJ5Em

---
Hanyang Smart Auto Study Bot
"""

    # 이메일 구성
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain", "utf-8"))

    # 첨부파일
    with open(file_path, "rb") as f:
        attachment = MIMEApplication(f.read())
        attachment.add_header(
            "Content-Disposition", "attachment",
            filename=file_path.name,
        )
        msg.attach(attachment)

    # 발송
    if not SENDER_PASSWORD:
        print("[!] EMAIL_APP_PASSWORD가 .env에 설정되지 않았습니다")
        print("    Gmail 앱 비밀번호 설정 방법:")
        print("    1. Google 계정 → 보안 → 2단계 인증 활성화")
        print("    2. 앱 비밀번호 생성 → 16자리 복사")
        print("    3. .env에 EMAIL_APP_PASSWORD=xxxx 추가")
        return False

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        print(f"[OK] 이메일 발송 완료!")
        print(f"  To: {to_email}")
        print(f"  Subject: {subject}")
        print(f"  Attachment: {file_path.name}")
        return True

    except Exception as e:
        print(f"[!] 이메일 발송 실패: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Email with Attachment")
    parser.add_argument("--file", required=True, help="첨부할 파일 경로")
    parser.add_argument("--to", default=DEFAULT_TO, help="수신자 이메일")
    parser.add_argument("--subject", help="이메일 제목")
    parser.add_argument("--body", help="이메일 본문")
    args = parser.parse_args()

    send_email_with_attachment(args.file, args.to, args.subject, args.body)


if __name__ == "__main__":
    main()
