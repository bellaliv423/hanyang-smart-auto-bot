# WhatsApp 챗봇 PPT/DOC 연동 가이드
> 작성: 오토 (Claude Code Agent) | 2026-03-06

## 개요

WhatsApp → OpenClaw 챗봇 → PPT/DOC 자동 생성 → 이메일+WhatsApp 발송

## 작동 방식

```
벨라 (WhatsApp)
  "M&A 사례분석 PPT 20장 만들어줘"
    │
    ▼
OpenClaw (스마트 오토)
  IDENTITY.md의 PPT/DOC 명령어 참조
    │
    ▼
ppt_generator.py / doc_generator.py 실행
  Claude API → JSON → python-pptx → .pptx
    │
    ├─→ Gmail (kndli.210@gmail.com) 첨부파일
    ├─→ WhatsApp 텍스트 알림 ("PPT 생성 완료!")
    └─→ Google Drive 업로드 (--upload)
```

## OpenClaw 설정 파일

### IDENTITY.md 위치
```
/home/kndli423/.openclaw/workspaces/hanyang-bot/IDENTITY.md
```

### 핵심 설정 (IDENTITY.md에 추가된 내용)

```markdown
## PPT/DOC 자동 생성 기능

### PPT 생성 명령어
cd "/mnt/d/AI _coding_project_all/hanyang_smart_auto_bot" && \
python3 study_assistant/ppt_generator.py \
  --topic "{주제}" --course {과목ID} --slides {장수} --send

### DOC 문서 생성 명령어
cd "/mnt/d/AI _coding_project_all/hanyang_smart_auto_bot" && \
python3 study_assistant/doc_generator.py \
  --topic "{주제}" --course {과목ID} --type {유형} --send
```

## 벨라가 WhatsApp에서 보내는 메시지 예시

### PPT 요청
| 메시지 | 실행되는 명령 |
|:-------|:-------------|
| "M&A 사례분석 PPT 20장 만들어줘" | `--topic "M&A 사례분석" --course 196656 --slides 20 --send` |
| "경영통계학 회귀분석 PPT" | `--topic "회귀분석" --course 196594 --slides 18 --send` |
| "계약법 기초 PPT 15장" | `--topic "계약법 기초" --course 196600 --slides 15 --send` |
| "국제금융론 환율 PPT" | `--topic "환율 분석" --course 196622 --slides 18 --send` |

### DOC 요청
| 메시지 | 실행되는 명령 |
|:-------|:-------------|
| "M&A 레포트 만들어줘" | `--topic "M&A 분석" --course 196656 --type report --send` |
| "경영통계학 요약 문서" | `--topic "통계학 요약" --course 196594 --type summary --send` |
| "계약법 에세이 써줘" | `--topic "계약법 에세이" --course 196600 --type essay --send` |

## 과목 자동 감지

챗봇이 벨라의 메시지에서 과목 키워드를 감지:
- "통계" "경영통계" → 196594
- "상법" "계약법" → 196600
- "M&A" "인수합병" "인수" → 196656
- "국제금융" "거시금융" "환율" → 196622

## 세션 초기화 (설정 변경 후 필수!)

IDENTITY.md 수정 후 반드시 세션 삭제:
```bash
rm -rf /home/kndli423/.openclaw/agents/main/sessions/
mkdir -p /home/kndli423/.openclaw/agents/main/sessions/
```

## 트러블슈팅

### 챗봇이 PPT 명령을 모름
→ IDENTITY.md에 PPT 섹션 있는지 확인
→ 세션 삭제 후 재시작

### PPT 생성 실패
→ `ANTHROPIC_API_KEY` 확인 (.env)
→ python-pptx 설치 확인: `pip install python-pptx`

### 이메일 미발송
→ `EMAIL_APP_PASSWORD` 확인 (.env)
→ Gmail 2FA + 앱 비밀번호 설정 필요
