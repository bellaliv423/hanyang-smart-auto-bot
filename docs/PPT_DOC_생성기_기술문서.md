# PPT/DOC 자동 생성기 - 완전 기술 문서
> 작성: 오토 (Claude Code Agent) | 2026-03-06 | v2.0

## 1. 개요

MBA 수업용 PPT/DOC 문서를 AI가 자동 생성하는 시스템.
주제 입력 → Claude AI 내용 생성 → python-pptx/python-docx 파일 생성 → 이메일+WhatsApp 발송.

### 핵심 기능
- AI 구조화 콘텐츠: 서론, 본론, 사례, 결론, 참고자료
- 차트/도표 자동 생성: 막대, 파이, 라인 차트 + 테이블
- 3개 언어 핵심 용어: 한국어/English/中文 병기
- 듀얼 발송: 이메일 첨부파일 + WhatsApp 알림
- Google Drive 자동 업로드

## 2. 아키텍처

```
사용자 요청 (CLI / WhatsApp)
    │
    ▼
Claude API (claude-sonnet-4-5-20250929)
    │ max_tokens=16384
    │ 2-pass 생성 (12장 초과 시)
    ▼
JSON 구조화 데이터
    │ slides[], key_terms[], references
    │ chart/table 데이터 포함
    ▼
python-pptx / python-docx
    │ 16:9 슬라이드, 한양대 테마
    │ 차트: CategoryChartData
    │ 테이블: add_table
    ▼
.pptx / .docx 파일
    │
    ├─→ Gmail SMTP (이메일 첨부)
    ├─→ WhatsApp (텍스트 알림)
    └─→ Google Drive (업로드)
```

## 3. 파일 구조

| 파일 | 역할 |
|:-----|:-----|
| `study_assistant/ppt_generator.py` | PPT 자동 생성 (메인) |
| `study_assistant/doc_generator.py` | Word 문서 자동 생성 |
| `study_assistant/email_sender.py` | 이메일 첨부파일 발송 |
| `study_assistant/assistant.py` | AI 학습 보조 (대화형) |

## 4. PPT 생성기 상세 (`ppt_generator.py`)

### 4.1 슬라이드 타입 (6종)

| type | 설명 | 특징 |
|:-----|:-----|:-----|
| `content` | 일반 불릿 슬라이드 | 3-5개 불릿, 자동 간격 |
| `case` | 사례 연구 | 기업명 + 분석 포인트 |
| `chart` | 차트/도표 | bar/pie/line/area 지원 |
| `table` | 비교표/정리표 | 헤더+데이터, 줄무늬 |
| `references` | 참고자료 | 논문/기사 번호 매김 |
| (자동) | 표지/용어/Thank You | build_ppt에서 자동 추가 |

### 4.2 차트 데이터 구조 (JSON)

```json
{
  "title": "글로벌 M&A 시장 규모",
  "type": "chart",
  "chart_type": "bar",
  "categories": ["2022", "2023", "2024", "2025E"],
  "series": [
    {"name": "글로벌 (조달러)", "values": [3.2, 2.8, 3.5, 4.1]},
    {"name": "한국 (조원)", "values": [48, 52, 70, 78]}
  ],
  "bullets": ["핵심 인사이트 1", "인사이트 2"],
  "source": "Refinitiv Deal Intelligence",
  "notes": "발표자 노트 (상세 설명)"
}
```

### 4.3 테이블 데이터 구조

```json
{
  "title": "M&A 유형 비교",
  "type": "table",
  "headers": ["구분", "장점", "단점", "사례"],
  "rows": [
    ["수평적 M&A", "시장점유율 확대", "독점규제", "디즈니-폭스"],
    ["수직적 M&A", "공급망 통합", "유연성 저하", "아마존-홀푸드"]
  ],
  "notes": "발표자 노트"
}
```

### 4.4 디자인 테마

```python
THEME = {
    "primary": RGBColor(0, 51, 102),      # 진한 남색 (한양대)
    "secondary": RGBColor(0, 102, 153),    # 파란색
    "accent": RGBColor(204, 0, 0),         # 빨간색 강조
    "bg_dark": RGBColor(0, 51, 102),       # 표지/Thank You 배경
    "bg_light": RGBColor(240, 245, 250),   # 내용 슬라이드 배경
}
```

### 4.5 겹침 방지 기술 (v2.0 핵심 개선)

**문제**: 개별 텍스트박스로 불릿을 배치하면, 긴 텍스트가 줄바꿈 시 다음 불릿과 겹침

**해결**: 하나의 `TextFrame`에 여러 `Paragraph`로 구성
```python
# AS-IS (겹침 발생)
for bullet in bullets:
    add_text_box(slide, x, y, w, h, bullet)  # 개별 박스
    y += 0.55  # 고정 간격 → 텍스트 길면 겹침!

# TO-BE (겹침 방지)
txBox = slide.shapes.add_textbox(x, y, w, h_large)
tf = txBox.text_frame
tf.word_wrap = True
for bullet in bullets:
    p = tf.add_paragraph()
    p.text = bullet
    p.space_before = Pt(6)  # 자동 간격
```

**적용 위치**: content, case, chart, references 모든 슬라이드

### 4.6 2-Pass 생성 (대용량 PPT)

12장 초과 시 자동으로 2번 API 호출:
- Part 1: 서론~본론 (절반)
- Part 2: 사례분석~결론~참고자료 (나머지)
- 중복 방지: Part 2에 Part 1의 제목 목록 전달

```python
if num_slides > 12:
    part1 = _call_claude_for_slides(..., "Part 1: 서론~본론")
    part2 = _call_claude_for_slides(..., "Part 2: 사례분석~결론",
        existing_titles=[s["title"] for s in part1["slides"]])
    part1["slides"].extend(part2["slides"])
```

### 4.7 JSON 복구 (잘린 응답 처리)

Claude API 응답이 잘릴 경우 자동 복구:
1. ````json ... ``` ` 블록 추출
2. `{` 시작점 찾기
3. `json.loads()` 시도
4. 실패 시 `repair_truncated_json()` → 열린 brackets/braces 자동 닫기
5. 최후 수단: 줄 단위 역순 파싱

## 5. DOC 생성기 상세 (`doc_generator.py`)

### 5.1 문서 유형 (5종)

| type | 설명 |
|:-----|:-----|
| `report` | 학술 보고서/레포트 |
| `summary` | 수업 내용 요약 |
| `case` | 기업 사례 분석 |
| `review` | 논문/자료 리뷰 |
| `essay` | 에세이/소논문 |

### 5.2 문서 구조
- 제목 + 부제 + 과목/교수/날짜
- Abstract 요약
- 본문 섹션 (Heading 1/2)
- 핵심 용어 테이블 (한/영/중)
- References
- 푸터

## 6. 이메일 발송 (`email_sender.py`)

- SMTP: Gmail (smtp.gmail.com:587, STARTTLS)
- 인증: Gmail 앱 비밀번호 (2FA 필요)
- 첨부: MIMEApplication으로 .pptx/.docx 첨부
- 수신: kndli.210@gmail.com (기본값)

## 7. 사용법

### CLI 명령어

```bash
# PPT 생성 (기본 18장)
python study_assistant/ppt_generator.py --topic "M&A 사례분석" --course 196656 --send

# PPT 20장 + Drive 업로드
python study_assistant/ppt_generator.py --topic "회귀분석" --course 196594 --slides 20 --send --upload

# DOC 레포트
python study_assistant/doc_generator.py --topic "계약법 요약" --course 196600 --type report --send

# DOC 사례분석 (중국어)
python study_assistant/doc_generator.py --topic "M&A案例分析" --course 196656 --type case --lang zh --send
```

### WhatsApp에서 요청 (OpenClaw 연동)

챗봇에게 자연어로 요청:
- "M&A 사례 분석 PPT 20장 만들어줘"
- "경영통계학 회귀분석 PPT 만들어줘"
- "계약법 요약 레포트 만들어줘"
- "국제금융론 에세이 써줘"

### 과목 ID 매핑

| ID | 과목 | 교수 |
|:---|:-----|:-----|
| 196594 | 경영통계학 | 부제만 |
| 196600 | 상법및계약법 | 강편모 |
| 196656 | M&A전략 | 김철중 |
| 196622 | 국제거시금융론 | 이창민 |

## 8. 의존성

```
python-pptx>=0.6.0    # PPT 생성
python-docx>=1.0.0    # DOC 생성
anthropic>=0.18.0     # Claude API
python-dotenv         # 환경변수
```

## 9. 트러블슈팅

### JSON 파싱 실패
- 원인: max_tokens 부족으로 응답 잘림
- 해결: max_tokens=16384, 2-pass 생성, JSON 자동 복구

### 텍스트 겹침 (v1 → v2)
- 원인: 개별 텍스트박스의 고정 간격
- 해결: 하나의 TextFrame + 여러 Paragraph

### sys.stdout 인코딩 충돌
- 원인: email_sender와 ppt_generator 둘 다 stdout 래핑
- 해결: `try/except` 가드 + encoding 체크

### 이메일 발송 실패
- Gmail 앱 비밀번호 확인: Google 계정 → 보안 → 2FA → 앱 비밀번호
- `.env`의 `EMAIL_APP_PASSWORD` 확인

## 10. 버전 히스토리

| 버전 | 날짜 | 변경 |
|:-----|:-----|:-----|
| v1.0 | 2026-03-06 | 기본 PPT/DOC 생성, 이메일 발송 |
| v1.1 | 2026-03-06 | 차트/테이블 슬라이드 추가 |
| v2.0 | 2026-03-06 | 겹침 방지 (TextFrame), 2-pass 생성, JSON 복구, WhatsApp 연동 |
