# Hanyang Smart Auto Study Bot

**한양대 MBA 학생을 위한 AI 학업 비서봇**

> LMS 자동 스크래핑 + AI 분석 + WhatsApp 리마인드 + 대화형 챗봇
>
> [한국어](#한국어) | [English](#english) | [中文](#中文)

---

## 한국어

### 이런 분들을 위해 만들었어요

- **야간 MBA 직장인** — 시간 없어서 LMS 확인 못하는 분
- **외국인 MBA 학생** — 한국어 수업 자료가 어려운 분
- **예습/복습 자동화** — AI가 핵심 정리해주면 좋겠는 분

### 주요 기능

| 기능 | 설명 |
|:-----|:-----|
| **LMS 자동 스크래핑** | HY-ON(Canvas LMS) 자동 로그인 → 수업계획서, 주차학습, 강의자료, 게시판 수집 |
| **AI 학습 보조** | Claude API로 수업 내용 분석, 예습/복습 자료 자동 생성 (한/中/EN) |
| **WhatsApp 알림** | 매일 아침 수업 요약, 수업 30분 전 리마인드, 주간 시간표 |
| **대화형 챗봇** | "예습해줘", "회귀분석 설명해줘" 등 자연어로 학업 질문 |
| **Google Drive 동기화** | 스크래핑 자료 + AI 학습노트 자동 업로드 |
| **다국어 지원** | 핵심 용어 한국어/中文/English 병기 |

### 시스템 구조

```
hanyang_smart_auto_bot/
├── config/
│   ├── .env.example        # 환경변수 템플릿 (이것을 .env로 복사)
│   └── courses.json        # 과목 설정 + 시간표
├── scrapers/
│   ├── hyon_login.py       # Phase 1: HY-ON LMS 로그인 자동화
│   ├── course_scraper.py   # Phase 2: 과목별 스크래핑
│   └── drive_uploader.py   # Google Drive 업로드
├── study_assistant/
│   └── assistant.py        # Phase 3: AI 학습 보조 (Claude API)
├── reminders/
│   └── whatsapp_reminder.py # Phase 4: WhatsApp 리마인더
├── agent/
│   ├── IDENTITY.md         # 챗봇 페르소나 설정
│   └── chatbot.py          # 대화형 학업 챗봇
├── data/
│   ├── courses/{id}/       # 과목별 스크래핑 데이터
│   ├── study_notes/        # AI 생성 학습 자료
│   └── mba_full_catalog.json  # 143개 전체 과목 목록
└── docs/
    └── SETUP.md            # 상세 설치 가이드
```

### 빠른 시작 (5분)

```bash
# 1. 클론
git clone https://github.com/bellaliv423/hanyang-smart-auto-bot.git
cd hanyang-smart-auto-bot

# 2. Python 환경 설정
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. 패키지 설치
pip install -r requirements.txt
playwright install chromium

# 4. 환경 변수 설정
cp config/.env.example config/.env
# config/.env 파일을 열어서 본인 계정 정보 입력

# 5. 과목 설정
# config/courses.json 에서 본인 수강 과목으로 수정

# 6. 실행!
python scrapers/hyon_login.py          # LMS 로그인 테스트
python scrapers/course_scraper.py      # 과목 스크래핑
python study_assistant/assistant.py --mode syllabus  # AI 분석
python agent/chatbot.py                # 챗봇 시작
```

> 상세 설치 가이드는 [docs/SETUP.md](docs/SETUP.md) 참고

### 기술 스택

- **Python 3.12** + Playwright (브라우저 자동화)
- **Anthropic Claude API** (AI 분석, 모델: `claude-sonnet-4-5-20250929`)
- **Google Drive API** (OAuth2 파일 동기화)
- **OpenClaw** (WhatsApp/챗봇 연동)
- **Windows Task Scheduler** (자동 실행)

### 도움이 필요하거나 피드백이 있다면

- **버그 신고**: [Issues](../../issues) 에서 "Bug Report" 선택
- **기능 요청**: [Issues](../../issues) 에서 "Feature Request" 선택
- **질문/도움**: [Discussions](../../discussions) 에서 자유롭게!
- **직접 연락**: WhatsApp으로 벨라에게 문의

> 이 프로젝트는 비개발자(벨라)가 Claude Code만으로 만든 프로젝트예요.
> 코딩을 몰라도 AI와 함께라면 이런 자동화가 가능합니다!

---

## English

### Who Is This For?

- **Working MBA students** — too busy to check LMS regularly
- **International students** — need help understanding Korean course materials
- **Anyone** who wants AI-powered study automation

### Key Features

| Feature | Description |
|:--------|:-----------|
| **LMS Auto-Scraping** | Auto-login to HY-ON (Canvas LMS) → collect syllabi, weekly content, materials |
| **AI Study Assistant** | Claude API analyzes course content, generates preview/review notes (KO/ZH/EN) |
| **WhatsApp Reminders** | Daily morning summary, 30-min pre-class reminder, weekly schedule |
| **Interactive Chatbot** | Ask study questions in natural language |
| **Google Drive Sync** | Auto-upload scraped materials + AI study notes |
| **Multilingual** | Key terms in Korean / Chinese / English |

### Quick Start

See [docs/SETUP.md](docs/SETUP.md) for detailed setup instructions.

```bash
git clone https://github.com/bellaliv423/hanyang-smart-auto-bot.git
cd hanyang-smart-auto-bot
pip install -r requirements.txt
playwright install chromium
cp config/.env.example config/.env
# Edit config/.env with your credentials
python agent/chatbot.py
```

### Feedback & Support

- **Bug Report**: Open an [Issue](../../issues)
- **Feature Request**: Open an [Issue](../../issues)
- **Questions**: Use [Discussions](../../discussions)

---

## 中文

### 適用對象

- **在職MBA學生** — 沒時間每天看LMS的上班族
- **外國留學生** — 韓語課程資料理解困難的同學
- **想要AI自動化學習** — 讓AI幫你整理預習/複習重點

### 主要功能

| 功能 | 說明 |
|:-----|:-----|
| **LMS自動爬取** | 自動登入HY-ON → 收集課程大綱、週次學習、講義資料 |
| **AI學習助手** | Claude API分析課程內容，自動生成預習/複習筆記（韓/中/英） |
| **WhatsApp提醒** | 每日早晨摘要、上課前30分鐘提醒、每週課表 |
| **互動聊天機器人** | 用自然語言問學習問題 |
| **Google Drive同步** | 自動上傳爬取資料 + AI學習筆記 |
| **多語言支援** | 關鍵術語韓語/中文/英文對照 |

### 回饋與支援

- **錯誤回報**: 開一個 [Issue](../../issues)
- **功能建議**: 開一個 [Issue](../../issues)
- **問題討論**: 使用 [Discussions](../../discussions)

---

## License

MIT License - 자유롭게 사용하세요!

## Credits

Built with Claude Code by Bella (벨라) - 비개발자의 AI 자동화 도전기

> "코딩을 몰라도 AI와 함께라면 가능합니다" / "不會寫程式也能用AI做自動化"
