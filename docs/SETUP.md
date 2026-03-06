# Hanyang Smart Auto Bot - Setup Guide / 설치 가이드

> 이 가이드를 따라하면 누구나 설치할 수 있어요!
> Follow this guide step by step - no coding experience needed!

---

## 목차 / Table of Contents

1. [필수 준비물](#1-필수-준비물--prerequisites)
2. [Python 설치](#2-python-설치)
3. [프로젝트 다운로드](#3-프로젝트-다운로드)
4. [패키지 설치](#4-패키지-설치)
5. [환경 변수 설정](#5-환경-변수-설정--credentials)
6. [과목 설정](#6-과목-설정--course-configuration)
7. [Google Drive 연동 (선택)](#7-google-drive-연동-선택)
8. [OpenClaw + WhatsApp 챗봇 (선택)](#8-openclaw--whatsapp-챗봇-선택)
9. [실행 방법](#9-실행-방법--how-to-run)
10. [자동 실행 설정 (Windows)](#10-자동-실행-설정-windows-task-scheduler)
11. [문제 해결](#11-문제-해결--troubleshooting)

---

## 1. 필수 준비물 / Prerequisites

| 항목 | 설명 | 필수? |
|:-----|:-----|:------|
| **Windows 10/11** | Mac/Linux도 가능하나, 이 가이드는 Windows 기준 | O |
| **Python 3.10+** | 3.12 권장 | O |
| **한양대 포털 계정** | portal.hanyang.ac.kr 로그인 가능한 학번/비번 | O |
| **Claude API Key** | https://console.anthropic.com/ 에서 발급 | O |
| **Google Cloud 프로젝트** | Drive 업로드용 (선택) | X |
| **WhatsApp** | 알림 수신용 (선택) | X |

### 비용 안내
- **Claude API**: 월 $5~10 정도 (사용량에 따라 다름)
- **Google Drive API**: 무료
- **나머지**: 모두 무료

---

## 2. Python 설치

### Windows
1. https://www.python.org/downloads/ 에서 Python 3.12 다운로드
2. 설치 시 **"Add Python to PATH"** 반드시 체크!
3. 확인:
   ```bash
   python --version
   # Python 3.12.x
   ```

### Mac
```bash
brew install python@3.12
```

---

## 3. 프로젝트 다운로드

```bash
# Git이 설치되어 있다면
git clone https://github.com/bellaliv423/hanyang-smart-auto-bot.git
cd hanyang-smart-auto-bot

# Git이 없다면 GitHub에서 ZIP 다운로드 후 압축 해제
```

---

## 4. 패키지 설치

```bash
# 가상환경 생성 (권장)
python -m venv venv

# 가상환경 활성화
# Windows (CMD):
venv\Scripts\activate
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Mac/Linux:
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt

# Playwright 브라우저 설치 (LMS 자동화에 필요)
playwright install chromium
```

### requirements.txt 내용
```
playwright>=1.40.0      # 브라우저 자동화 (LMS 로그인/스크래핑)
python-dotenv>=1.0.0    # .env 파일 로드
anthropic>=0.40.0       # Claude AI API
httpx>=0.27.0           # HTTP 클라이언트
schedule>=1.2.0         # 알림 스케줄러
google-auth>=2.0.0      # Google Drive 인증 (선택)
google-auth-oauthlib>=1.0.0
google-api-python-client>=2.0.0
openpyxl>=3.1.0         # Excel 파일 읽기 (선택)
```

---

## 5. 환경 변수 설정 / Credentials

```bash
# 템플릿 복사
cp config/.env.example config/.env
```

`config/.env` 파일을 열어서 수정:

```env
# 한양 포털 로그인 정보
HANYANG_USER_ID=본인_학번
HANYANG_PASSWORD=본인_비밀번호

# Claude API 키
# https://console.anthropic.com/ 에서 발급
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# WhatsApp 알림 (선택사항, 없으면 빈칸 유지)
WHATSAPP_GATEWAY_URL=http://localhost:3000
WHATSAPP_TARGET=+82본인번호
```

### Claude API 키 발급 방법
1. https://console.anthropic.com/ 접속
2. 회원가입/로그인
3. "API Keys" 메뉴 → "Create Key"
4. 생성된 키를 `.env`에 붙여넣기
5. 결제 수단 등록 (월 $5~10 예상)

> **주의**: `.env` 파일은 절대 GitHub에 올리지 마세요! (`.gitignore`에 이미 포함됨)

---

## 6. 과목 설정 / Course Configuration

`config/courses.json`을 본인 수강 과목으로 수정:

```json
{
  "semester": "2026년 1학기",
  "lms_base_url": "https://learning.hanyang.ac.kr",
  "portal_url": "https://portal.hanyang.ac.kr/port.do",
  "menu_tools": {
    "syllabus": "/assignments/syllabus",
    "board": "/external_tools/132",
    "weekly": "/external_tools/140",
    "materials": "/external_tools/3",
    "attendance": "/external_tools/138"
  },
  "courses": [
    {
      "code": "수업코드",
      "name_ko": "과목명 (한국어)",
      "name_en": "Course Name (English)",
      "name_zh": "課程名 (中文)",
      "professor": "교수명",
      "course_id": 000000,
      "lms_url": "https://learning.hanyang.ac.kr/courses/000000",
      "schedule": {
        "day": "토",
        "day_en": "Saturday",
        "time": "13:00-16:00",
        "room": "경영관 103"
      }
    }
  ]
}
```

### Course ID 찾는 방법
1. HY-ON (learning.hanyang.ac.kr) 로그인
2. 본인 과목 클릭
3. URL에서 숫자 확인: `learning.hanyang.ac.kr/courses/`**196594** ← 이 숫자가 Course ID

---

## 7. Google Drive 연동 (선택)

Google Drive에 학습 자료를 자동 업로드하려면:

### 7-1. Google Cloud 프로젝트 설정

1. https://console.cloud.google.com/ 접속
2. "프로젝트 만들기" → 이름 입력 (예: `hanyang-mba`)
3. "API 및 서비스" → "라이브러리" → "Google Drive API" 검색 → "사용 설정"

### 7-2. OAuth2 클라이언트 만들기

1. "API 및 서비스" → "사용자 인증 정보"
2. "OAuth 동의 화면" → "외부" → 앱 이름 입력 → 본인 이메일 추가 (테스트 사용자)
3. "사용자 인증 정보 만들기" → "OAuth 클라이언트 ID"
   - 유형: **데스크톱 앱**
   - 이름: 아무거나
4. JSON 다운로드 → `config/client_secret.json`으로 저장

### 7-3. 최초 인증

```bash
python scrapers/drive_uploader.py
# 브라우저가 열리면 Google 계정 로그인 → 권한 허용
# config/drive_token.json 자동 생성됨
```

> **주의**: `client_secret.json`과 `drive_token.json`은 절대 GitHub에 올리지 마세요!

---

## 8. OpenClaw + WhatsApp 챗봇 (선택)

WhatsApp으로 챗봇과 대화하려면:

### 8-1. WSL 설치 (Windows)

```powershell
# PowerShell (관리자)
wsl --install
```

### 8-2. OpenClaw 설치 (WSL 내)

```bash
# WSL 터미널에서
npm install -g openclaw

# WhatsApp gateway 시작
npx openclaw gateway start --channel whatsapp

# QR 코드 스캔 → WhatsApp 연결
```

### 8-3. 에이전트 시작

```bash
# agent/IDENTITY.md를 OpenClaw 에이전트 디렉토리에 복사
mkdir -p ~/.openclaw/agents/hanyang-bot/agent/
cp agent/IDENTITY.md ~/.openclaw/agents/hanyang-bot/agent/

# 에이전트 시작
npx openclaw agent start --identity agent/IDENTITY.md
```

### 8-4. 대화 테스트

WhatsApp에서 본인 번호로 메시지 보내기:
- "오늘 수업 있어?"
- "경영통계학 예습해줘"
- "이번주 시간표 알려줘"

---

## 9. 실행 방법 / How to Run

### Phase 1: LMS 로그인 테스트
```bash
python scrapers/hyon_login.py
# 브라우저가 열리며 자동 로그인 → 대시보드 확인
```

### Phase 2: 과목 스크래핑
```bash
python scrapers/course_scraper.py
# 4과목 수업계획서/게시판/주차학습/강의자료 수집
# 결과: data/courses/{course_id}/ 폴더에 저장
```

### Phase 3: AI 학습 보조
```bash
# 수업계획서 분석 (3개 언어)
python study_assistant/assistant.py --mode syllabus

# 특정 과목 예습
python study_assistant/assistant.py --course 196594 --mode preview

# 복습 자료 생성
python study_assistant/assistant.py --course 196594 --mode review

# 특정 주제 설명
python study_assistant/assistant.py --course 196594 --mode explain --query "회귀분석"
```

### Phase 4: WhatsApp 알림
```bash
# 테스트 메시지
python reminders/whatsapp_reminder.py --test

# 오늘 수업 요약
python reminders/whatsapp_reminder.py --now

# 주간 시간표
python reminders/whatsapp_reminder.py --weekly

# 데몬 모드 (상시 실행)
python reminders/whatsapp_reminder.py
```

### 대화형 챗봇
```bash
python agent/chatbot.py
# [Bella] 경영통계학 예습해줘
# [스마트오토] 이번 주 경영통계학 예습 포인트입니다...
```

### Google Drive 업로드
```bash
python scrapers/drive_uploader.py
```

---

## 10. 자동 실행 설정 (Windows Task Scheduler)

매일 자동으로 스크래핑 + 알림을 실행하려면:

### 배치 파일 만들기

`run_daily.bat` 파일 생성:
```bat
@echo off
cd /d "D:\hanyang-smart-auto-bot"
call venv\Scripts\activate
python scrapers/course_scraper.py
python study_assistant/assistant.py --mode preview
python reminders/whatsapp_reminder.py --now
```

### Task Scheduler 등록
1. Windows 검색 → "작업 스케줄러"
2. "기본 작업 만들기" → 이름: `Hanyang_Study_Bot`
3. 트리거: 매일 08:00
4. 동작: `run_daily.bat` 경로 선택
5. 완료!

---

## 11. 문제 해결 / Troubleshooting

### "LMS 로그인 실패"
- `.env`의 학번/비밀번호 확인
- 한양 포털에서 직접 로그인 되는지 확인
- 비밀번호에 특수문자(`@`, `#` 등)가 있으면 따옴표로 감싸기

### "Claude API 오류"
- API 키 확인: `sk-ant-api03-`로 시작해야 함
- 잔액 확인: https://console.anthropic.com/settings/billing
- 모델명: `claude-sonnet-4-5-20250929` (오타 주의!)

### "한글 깨짐 (Windows)"
- Python 파일 첫 줄에 추가:
  ```python
  import sys, io
  sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
  ```

### "Google Drive 업로드 실패"
- `client_secret.json` 파일 확인
- OAuth 동의 화면에서 본인 이메일이 테스트 사용자에 추가되었는지 확인
- `drive_token.json` 삭제 후 재인증

### "WhatsApp 메시지 안 옴"
- WSL에서 OpenClaw gateway 실행 중인지 확인
- WhatsApp QR 코드 재스캔
- `WHATSAPP_TARGET` 번호 형식 확인 (`+82` 포함)

### "Playwright 브라우저 안 열림"
```bash
playwright install chromium
# 또는 시스템 의존성 설치
playwright install-deps
```

---

## 피드백 & 기여

### 피드백 방법
1. **GitHub Issues**: 버그 신고, 기능 요청
2. **GitHub Discussions**: 질문, 아이디어 공유
3. **WhatsApp**: 벨라에게 직접 연락

### 기여하기
1. Fork → Branch → 수정 → Pull Request
2. 또는 Issue에 아이디어 남기기

> 이 프로젝트는 **비개발자**가 **Claude Code**만으로 만들었습니다.
> 코딩을 몰라도 충분히 기여할 수 있어요!

---

*Made with Claude Code by Bella (벨라) - Hanyang MBA*
