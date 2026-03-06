# OpenClaw 챗봇 설정 & 멀티 에이전트 가이드

> 작성일: 2026-03-06 | 이 문서는 WhatsApp 학업 챗봇 설정 + 오류 해결 과정을 기록합니다.

## 1. OpenClaw 기본 구조

OpenClaw은 여러 에이전트를 동시에 운영할 수 있는 AI 에이전트 프레임워크입니다.

```
~/.openclaw/
├── agents/
│   ├── main/                    # 기본 에이전트 (isDefault=true)
│   │   ├── agent/
│   │   │   ├── USER.md          # 사용자 정보
│   │   │   ├── auth-profiles.json
│   │   │   └── models.json
│   │   └── sessions/            # 대화 세션 파일들
│   └── hanyang-bot/             # 학업봇 에이전트
│       ├── agent/
│       │   ├── IDENTITY.md      # 에이전트 정체성 + 수업 정보
│       │   └── auth-profiles.json
│       └── sessions/            # 대화 세션 파일들
├── workspaces/
│   └── hanyang-bot/             # 에이전트 작업 공간
│       ├── IDENTITY.md          # ★ 에이전트 정체성 (workspace 우선!)
│       ├── USER.md              # ★ 사용자 정보 (workspace 우선!)
│       ├── BOOTSTRAP.md         # 부트스트랩 데이터
│       ├── SOUL.md              # 에이전트 성격/행동 규칙
│       ├── AGENTS.md            # 멀티 에이전트 설정
│       ├── TOOLS.md             # 사용 가능 도구
│       └── HEARTBEAT.md         # 상태 체크
└── workspace/                   # main 에이전트 기본 작업 공간
```

## 2. 핵심 발견: 파일 우선순위

### 문제: 에이전트가 수업 정보를 모름
- `agents/hanyang-bot/agent/IDENTITY.md` 에 수업 시간표를 넣었음
- `workspaces/hanyang-bot/BOOTSTRAP.md` 에도 수업 시간표를 넣었음
- **그런데도** 챗봇이 "수업 정보가 없다"고 응답!

### 원인: workspace 파일이 agent 파일보다 우선!

```
우선순위 (높은 순서):
1. workspaces/hanyang-bot/IDENTITY.md  ← ★ 여기가 최우선!
2. workspaces/hanyang-bot/USER.md      ← ★ 사용자 정보
3. workspaces/hanyang-bot/BOOTSTRAP.md
4. agents/hanyang-bot/agent/IDENTITY.md ← 이건 2순위
```

workspace의 `IDENTITY.md`와 `USER.md`가 비어있으면,
agent 폴더의 IDENTITY.md에 아무리 정보를 넣어도 소용없음!

### 해결: workspace 파일에 수업 정보 직접 입력

**workspace/IDENTITY.md** 에 수업 시간표 + 교수 정보 + 교수 평가 넣기
**workspace/USER.md** 에 벨라 정보 + 수업 일정 넣기

## 3. 세션 초기화 (중요!)

에이전트 설정을 바꾸면 반드시 세션 초기화 필요:

```bash
# WSL에서 실행
rm -rf ~/.openclaw/agents/hanyang-bot/sessions/
mkdir -p ~/.openclaw/agents/hanyang-bot/sessions/
```

### 왜 세션 초기화가 필요한가?
- OpenClaw은 대화 히스토리를 `sessions/*.jsonl` 파일에 저장
- 이전 세션에서 "수업 정보 없다"고 답한 기록이 남아있으면,
  새 시스템 프롬프트를 받아도 이전 맥락을 따라 같은 답변을 함
- Anthropic 프롬프트 캐시(`cacheRead`)도 이전 시스템 프롬프트를 기억
- 세션 파일 삭제 → 완전히 새로운 대화 시작 → 새 IDENTITY.md 반영

### 주의: sessions.json 도 삭제해야 함!
```bash
# sessions.json에 세션 매핑 정보가 있어서
# .jsonl만 삭제하면 같은 세션 ID를 재사용할 수 있음
rm -rf ~/.openclaw/agents/hanyang-bot/sessions/  # 폴더 통째로!
mkdir -p ~/.openclaw/agents/hanyang-bot/sessions/
```

## 4. 멀티 에이전트 라우팅 (WhatsApp 바인딩)

### 현재 에이전트 목록
```bash
npx openclaw agents list --json
```

| Agent | 역할 | 바인딩 | Default |
|:------|:------|:-------|:--------|
| main | OzKiz 고객봇 | 없음 | Yes (기본) |
| hanyang-bot | 학업봇 | whatsapp | No |
| ozkiz-ops | 주문처리 | 없음 | No |
| buyer-hunter | 바이어 발굴 | 없음 | No |
| bella-secretary | 비서 | 없음 | No |

### 바인딩 확인/설정
```bash
# 현재 바인딩 확인
npx openclaw agents bindings --json

# WhatsApp을 hanyang-bot에 바인딩
npx openclaw agents bind --agent hanyang-bot --bind whatsapp

# 바인딩 제거
npx openclaw agents unbind --agent hanyang-bot --bind whatsapp
```

### 문제: main이 default라서 WhatsApp 메시지를 가로챔
- hanyang-bot에 WhatsApp 바인딩이 있어도
- main이 `isDefault: true`라서 먼저 메시지를 받을 수 있음
- 해결: main의 USER.md에도 수업 정보 추가 (백업)

### 특정 에이전트 직접 호출 (CLI)
```bash
# hanyang-bot으로 직접 WhatsApp 메시지 보내기
npx openclaw agent \
  --agent hanyang-bot \
  --channel whatsapp \
  --to "+821097805690" \
  --message "토요일 수업 알려줘" \
  --deliver
```

## 5. 에이전트 설정 파일 내용

### workspace/IDENTITY.md (핵심!)
```markdown
# IDENTITY.md - 스마트 오토 (Smart Auto)

- **Name:** 스마트 오토 (Smart Auto)
- **Creature:** AI 학업 비서봇
- **Emoji:** 📚
- **Languages:** 한국어 (기본), 中文繁體, English
- **Owner:** Bella (벨라) - 한양대 MBA 경영전문대학원

## 2026년 1학기 수업 일정 (항상 기억!)

### 화요일 (1과목)
- 19:00-22:00 M&A전략:계획수립과실행 | 김철중 교수 | 경영관 201

### 토요일 (3과목)
- 09:00-12:00 상법및계약법 | 강편모 교수 | 경영관 203
- 13:00-16:00 경영통계학 | 부제만 교수 | 경영관 103
- 16:00-19:00 국제거시금융론 | 이창민 교수 | 경영관 203

### 교수 평가
- 부제만: 편하고 재밌음, 기말만, 과제없음, 추천 상
- 강편모: 14문제중 5-6개 출제, 과제없음, B+ 쉬움
- 김철중: 현업 Case study, 레포트2+발표2
- 이창민: 시험없음 과제대체, 정리레포트
```

### workspace/USER.md
```markdown
# USER.md

- **Name:** Bella (벨라, 황영아)
- **What to call them:** 벨라
- **Timezone:** Asia/Seoul
- **Languages:** 한국어, 中文繁體, English
- **School:** 한양대학교 MBA 경영전문대학원
- **Origin:** 대만 출신, 한국 10년+

## 수업 일정
(IDENTITY.md와 동일한 시간표)
```

### workspace/BOOTSTRAP.md
- IDENTITY.md와 동일한 수업 정보 (백업)
- 과목별 상세 정보 (Course ID, LMS URL, 성적 비율 등)

## 6. 오류 해결 타임라인

| 시간 | 시도 | 결과 | 원인 |
|:-----|:-----|:-----|:-----|
| 18:47 | agent/IDENTITY.md 수업 정보 추가 | 실패 | workspace가 우선 |
| 18:50 | BOOTSTRAP.md 수업 정보 추가 | 실패 | workspace IDENTITY가 우선 |
| 19:16 | BOOTSTRAP.md 상세 업데이트 + 세션 삭제 | 실패 | workspace가 우선 |
| 19:30 | main USER.md에 수업 정보 추가 | 부분 성공 | main은 OzKiz용 |
| 19:57 | hanyang-bot 세션 삭제 | 실패 | sessions.json 남아있음 |
| 20:03 | 세션 폴더 통째로 삭제 + 재생성 | 실패 | workspace 파일이 비어있음 |
| 20:04 | **workspace/IDENTITY.md + USER.md 업데이트** | **성공!** | **핵심 해결** |

### 핵심 교훈
1. **workspace 파일이 agent 파일보다 우선** → workspace부터 수정!
2. **세션 폴더 통째로 삭제** → `.jsonl` + `sessions.json` 모두 삭제!
3. **Anthropic 프롬프트 캐시** → 세션 삭제해도 캐시가 5분 정도 유지될 수 있음
4. **멀티 에이전트 환경** → default 에이전트도 수업 정보 백업 필요

## 7. 새 학기 설정 체크리스트

새 학기가 되면 이 순서대로 업데이트:

1. `config/courses.json` 수정 (새 과목 정보)
2. WSL에서 workspace 파일 업데이트:
   - `~/.openclaw/workspaces/hanyang-bot/IDENTITY.md`
   - `~/.openclaw/workspaces/hanyang-bot/USER.md`
   - `~/.openclaw/workspaces/hanyang-bot/BOOTSTRAP.md`
3. agent 파일도 업데이트:
   - `~/.openclaw/agents/hanyang-bot/agent/IDENTITY.md`
4. main agent에도 백업:
   - `~/.openclaw/agents/main/agent/USER.md`
5. 세션 초기화:
   ```bash
   rm -rf ~/.openclaw/agents/hanyang-bot/sessions/
   mkdir -p ~/.openclaw/agents/hanyang-bot/sessions/
   rm -f ~/.openclaw/agents/main/sessions/*.jsonl
   ```
6. 테스트:
   ```bash
   npx openclaw agent --agent hanyang-bot --channel whatsapp \
     --to "+82번호" --message "토요일 수업 알려줘" --deliver
   ```
