# CLAUDE.md - Hanyang Smart Auto Bot

## Project Overview
한양대 MBA 학생을 위한 AI 학업 비서봇.
LMS 자동 스크래핑 + AI 분석 + WhatsApp 리마인드 + 대화형 챗봇.

## Target Users (3 groups)
1. **야간 MBA 직장인** - 시간 없어서 LMS 확인 못하는 분
2. **외국인 MBA 학생** - 한국어 수업 자료가 어려운 분
3. **예습/복습 자동화** - AI 학습 도우미가 필요한 분

## Architecture
```
hanyang_smart_auto_bot/
├── config/              # 과목 설정, 인증 정보(.env)
├── scrapers/            # HY-ON LMS 스크래퍼 (Playwright)
│   ├── hyon_login.py    # 포털 SSO + LMS 2단계 로그인
│   ├── course_scraper.py # 과목별 콘텐츠 수집
│   └── drive_uploader.py # Google Drive 업로드
├── study_assistant/     # 학습 보조 (Claude API)
│   └── assistant.py     # AI 분석 (syllabus/preview/review/explain)
├── reminders/           # 알림 시스템
│   └── whatsapp_reminder.py # WhatsApp 리마인더
├── agent/               # 챗봇
│   ├── IDENTITY.md      # 챗봇 페르소나
│   └── chatbot.py       # 터미널 대화형 챗봇
└── data/                # 수집 데이터 + AI 학습 자료
```

## Key Technical Notes

### HY-ON LMS Login (2-step!)
1. Portal SSO: `portal.hanyang.ac.kr` → `input#userId` + `input#password`
2. LMS Login: `api.hanyang.ac.kr` → `input#uid` + `input#upw` + `button#login_btn`
3. Password popup: `#btn_cancel` ("다음에 변경") auto-dismiss

### Claude API
- Model: `claude-sonnet-4-5-20250929` (NOT 20250514!)
- timeout=120.0 required (default will timeout)

### Google Drive
- Must use OAuth2 (service accounts can't upload - storage quota limit)
- OAuth2: client_secret.json → drive_token.json flow

### Windows Encoding
- cp949 fix: `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')`

## URLs
- Portal: https://portal.hanyang.ac.kr
- LMS (HY-ON): https://learning.hanyang.ac.kr
- Credentials: stored in config/.env (never commit!)

## Setup
See [docs/SETUP.md](docs/SETUP.md) for detailed installation guide.
